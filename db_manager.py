import sqlite3
import re
import json

DB_PATH = "games.db"

def get_all_genres():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT genre FROM games")
    all_genres = cursor.fetchall()
    conn.close()
    
    unique_genres = set()
    for (genre_str,) in all_genres:
        if genre_str:
            for g in genre_str.split(','):
                if g.strip():
                    unique_genres.add(g.strip())
    return sorted(list(unique_genres))

def parse_requirements(platforms_json):
    min_ram = 0
    min_disk = 0
    try:
        platforms = json.loads(platforms_json)
        for p in platforms:
            req_en = p[1]
            if req_en and isinstance(req_en, dict):
                min_req = req_en.get('minimum', '')
                rec_req = req_en.get('recommended', '')
                text = str(min_req) + " " + str(rec_req)
                
                # RAM
                ram_match = re.search(r'(\d+)\s*(GB|MB)\s*RAM', text, re.IGNORECASE)
                if ram_match:
                    val = int(ram_match.group(1))
                    if ram_match.group(2).upper() == 'MB':
                        val = val / 1024
                    if val > min_ram:
                        min_ram = val
                        
                # Disk Space
                disk_match = re.search(r'(\d+)\s*(GB|MB)\s*(available space|storage|hard drive space|space)', text, re.IGNORECASE)
                if disk_match:
                    val = int(disk_match.group(1))
                    if disk_match.group(2).upper() == 'MB':
                        val = val / 1024
                    if val > min_disk:
                        min_disk = val
    except Exception:
        pass
    return min_ram, min_disk

def get_all_games(sort_by=None, search_text=None, selected_genres=None, playtime_filter=None, esrb_filter=None, hardware_specs=None):
    """
    Fetch games from the database with filtering and sorting.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT name, genre, playtime, date_of_publishing, rating, platforms, id FROM games WHERE 1=1"
    params = []
    
    if search_text:
        query += " AND name LIKE ?"
        params.append(f"%{search_text}%")
        
    if selected_genres:
        genre_conditions = []
        for g in selected_genres:
            genre_conditions.append("genre LIKE ?")
            params.append(f"%{g}%")
        query += " AND (" + " OR ".join(genre_conditions) + ")"
        
    if playtime_filter and playtime_filter != "Any":
        if playtime_filter == "Under 10 hours":
            query += " AND playtime > 0 AND playtime < 10"
        elif playtime_filter == "10-50 hours":
            query += " AND playtime >= 10 AND playtime <= 50"
        elif playtime_filter == "Over 50 hours":
            query += " AND playtime > 50"
            
    if esrb_filter and esrb_filter != "All":
        query += " AND esrb_rating = ?"
        params.append(esrb_filter)
    
    if sort_by == 'name':
        query += " ORDER BY name ASC"
    elif sort_by == 'playtime':
        query += " ORDER BY playtime DESC"
    elif sort_by == 'date_of_publishing':
        query += " ORDER BY date_of_publishing DESC"
    elif sort_by == 'rating':
        query += " ORDER BY rating DESC"
    else:
        # Default sort
        query += " ORDER BY rating DESC"
        
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    filtered_results = []
    for row in results:
        name, genre, playtime, date_of_publishing, rating, platforms_json, game_id = row
        
        hardware_score = 0
        if hardware_specs:
            pc_ram = hardware_specs.get('ram_gb', 0)
            pc_disk = hardware_specs.get('disk_gb', 0)
            
            min_ram, min_disk = parse_requirements(platforms_json)
            
            # Якщо мінімальні вимоги перевищують існуючі - фільтруємо гру
            if min_ram > pc_ram:
                continue
            if min_disk > pc_disk:
                continue
            
            # Чим менша різниця, тим ближче гра до лімітів ПК
            hardware_score = (pc_ram - min_ram) + ((pc_disk - min_disk) * 0.1)
                
        filtered_results.append((name, genre, playtime, date_of_publishing, rating, game_id, hardware_score))
        
    if sort_by == 'hardware' and hardware_specs:
        filtered_results.sort(key=lambda x: x[6])
        
    # Return without the hardware_score
    return [x[:6] for x in filtered_results]

def get_game_details(game_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, platforms, rating, date_of_publishing, genre FROM games WHERE id = ?", (game_id,))
    res = cursor.fetchone()
    conn.close()
    return res
