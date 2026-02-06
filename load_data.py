import json
import requests
import sqlite3
import re

URL = 'https://api.rawg.io/api/games/'
API = '755e964103a14e4f94dad0a1a06e9947'

def clean_unwanted(text):
    if not text:
        return text
    # 1. Replace html notaion with white spaces 
    text = re.sub('<[^<]+?>', '', text)
    # 2. Replace tabs (\t), returns (\r), and newlines (\n) with a single space
    text = re.sub(r'[\t\r\n]+', ' ', text)
    # 3. Collapse multiple spaces into one "  " -> " "
    text = re.sub(r'\s+', ' ', text)
    return text.strip() 

def clean_platforms(game):
    cleaned_platforms_list = []
    for p in game.get('platforms', []):
        p_name = p['platform']['name']
        
        # We clean the internal requirement strings one by one
        req_en = p.get('requirements_en')
        if isinstance(req_en, dict):
            # Clean both 'minimum' and 'recommended' inside the dict
            req_en = {k: clean_unwanted(v) for k, v in req_en.items()}
        elif isinstance(req_en, str):
            req_en = clean_unwanted(req_en)

        req_ru = p.get('requirements_ru')
        if isinstance(req_ru, dict):
            req_ru = {k: clean_unwanted(v) for k, v in req_ru.items()}
        elif isinstance(req_ru, str):
            req_ru = clean_unwanted(req_ru)

        cleaned_platforms_list.append((p_name, req_en, req_ru))

    return json.dumps(cleaned_platforms_list)

def start(data):
    games = data['results']

    COLUMNS = [
        'id', 'name', 'genre', 'description', 'date_of_publishing', 
        'tags', 'tba', 'rating', 'ratings', 'ratings_count', 
        'review_text_count', 'added_by_status', 'metacritic', 
        'playtime', 'updated', 'dominant_color', 'platforms', 
        'stores', 'esrb_rating'
    ]

    all_game_tuples = []

    for game in games:
        detail_url = f"{URL}{game['id']}"
        res = requests.get(detail_url, params={'key': API})
        
        if res.status_code == 200:
            description = res.json().get('description', 'No description available')
            description = clean_unwanted(description)
        else:
            description = "null"

        game_map = {
            'id': game['id'],
            'name': game['name'],
            'genre': ",".join([g['name'] for g in game.get('genres', [])]),
            'description': description,
            'date_of_publishing': game.get('released'),
            'tags': ", ".join([t['name'] for t in game.get('tags', [])]),
            'tba': 1 if game.get('tba') else 0,
            'rating': game.get('rating'),
            'ratings': json.dumps([(r['title'], r['count'], r['percent']) for r in game.get('ratings', [])]),
            'ratings_count': game.get('ratings_count'),
            'review_text_count': game.get('review_text_count'),
            'added_by_status': json.dumps(list(game.get('added_by_status', {}).items())),
            'metacritic': game.get('metacritic'),
            'playtime': game.get('playtime'),
            'updated': game['updated'].split('T')[0] if 'updated' in game else None,
            'dominant_color': game.get('dominant_color'),
            'platforms': clean_platforms(game),
            'stores': json.dumps([
                (s['store']['name'], s['store']['domain']) 
                for s in game.get('stores', [])
            ]),
            'esrb_rating': game['esrb_rating']['name'] if game.get('esrb_rating') else "Not Rated"
        }

        current_game_tuple = tuple(game_map[col] for col in COLUMNS)
        all_game_tuples.append(current_game_tuple)
    connection = sqlite3.connect("games.db")
    cursor = connection.cursor()
    cursor.executemany("INSERT OR IGNORE INTO games VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", all_game_tuples)
    connection.commit()
    connection.close()