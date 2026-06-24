import sqlite3
import json
import os
import uuid
import chromadb
from datetime import datetime
from ollama import Client

DB_PATH = "games.db"
CHROMA_PATH = "chroma_db"
HISTORY_FILE = "chat_history.json"

chroma_client = None
collection = None

def get_chroma_collection():
    global chroma_client, collection
    if not chroma_client:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name="games_v2")
        
        # Check if empty
        if collection.count() == 0:
            import db_manager
            print("Populating ChromaDB with games and their requirements...")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, genre, platforms FROM games")
            rows = cursor.fetchall()
            
            ids = []
            documents = []
            metadatas = []
            
            for row in rows:
                game_id, name, desc, genre, platforms_json = row
                min_ram, min_disk = db_manager.parse_requirements(platforms_json)
                req_str = f"RAM: {min_ram}GB, Disk Space: {min_disk}GB"
                
                ids.append(str(game_id))
                doc = f"Game: {name}\nGenre: {genre}\nSystem Requirements: {req_str}\nDescription: {desc}"
                documents.append(doc)
                metadatas.append({"name": name, "genre": genre})
                
            if ids:
                batch_size = 100
                for i in range(0, len(ids), batch_size):
                    collection.add(
                        documents=documents[i:i+batch_size],
                        metadatas=metadatas[i:i+batch_size],
                        ids=ids[i:i+batch_size]
                    )
            conn.close()
            print("ChromaDB populated.")
            
    return collection

def search_games(query_text, n_results=3):
    col = get_chroma_collection()
    if col.count() == 0:
        return []
    
    results = col.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    docs = results.get("documents", [[]])[0]
    return docs

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {}
                return data
        except Exception:
            return {}
    return {}

def save_history(history_dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_dict, f, ensure_ascii=False, indent=2)

def generate_chat_title(session_id, first_message):
    client = Client(host='http://localhost:11434')
    prompt = f"Generate a very short 3-5 word title summarizing this query: '{first_message}'. ONLY output the title, no quotes or extra text."
    try:
        response = client.chat(model='llama3.2', messages=[{"role": "user", "content": prompt}])
        title = response['message']['content'].strip(' "\'')
    except Exception:
        title = "New Chat"
        
    history = load_history()
    if session_id not in history:
        history[session_id] = {"title": title, "messages": [], "created_at": datetime.now().isoformat()}
    else:
        history[session_id]["title"] = title
    save_history(history)
    
    return title

def generate_response(session_id, user_message, hardware_specs, chunk_callback=None):
    if not hardware_specs:
        import hardware_scanner
        hardware_specs = hardware_scanner.get_hardware_specs()

    context_docs = search_games(user_message, n_results=3)
    context_text = "\n\n---\n\n".join(context_docs)
    
    hw_text = f"OS: {hardware_specs.get('os')}\nCPU: {hardware_specs.get('cpu')}\nGPU: {hardware_specs.get('gpu')}\nRAM: {hardware_specs.get('ram_gb')}GB\nDisk Space: {hardware_specs.get('disk_gb')}GB"
        
    system_prompt = f"""You are an expert Game Recommender AI assistant.
Your goal is to help the user find the best games based on their preferences and their hardware specifications.

User's PC Hardware Specifications:
{hw_text}

Relevant games for this query:
{context_text}

CRITICAL INSTRUCTIONS:
1. Answer shortly and concisely. Do NOT write long paragraphs.
2. NEVER mention whether a game is in our database or not. ONLY write about the games explicitly provided in the 'Relevant games for this query' section. Do not reference the database directly.
3. DO NOT MAKE UP OR HALLUCINATE ANY GAME TITLES. If the provided games do not match the user's request, simply apologize and say you couldn't find a good match right now.
4. Always compare the game's System Requirements against the User's PC Hardware Specifications! If a game requires more RAM or Disk Space than the user has, warn them explicitly!
5. Be conversational and friendly.
6. Reply ONLY in English.
"""
    
    history_dict = load_history()
    if session_id not in history_dict:
        history_dict[session_id] = {
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
        
    session_messages = history_dict[session_id]["messages"]
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append past history (limit to last 6 messages for faster processing)
    for msg in session_messages[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": user_message})
    
    client = Client(host='http://localhost:11434')
    try:
        response = client.chat(model='llama3.2', messages=messages, stream=True)
        reply = ""
        for chunk in response:
            chunk_content = chunk['message']['content']
            reply += chunk_content
            if chunk_callback:
                chunk_callback(reply)
                
        # Save to history
        session_messages.append({"role": "user", "content": user_message})
        session_messages.append({"role": "assistant", "content": reply})
        save_history(history_dict)
        
        return reply
    except Exception as e:
        error_msg = f"Error connecting to Ollama: {e}\nPlease make sure Ollama is running and the 'llama3.2' model is loaded."
        if chunk_callback:
            chunk_callback(error_msg)
        return error_msg
