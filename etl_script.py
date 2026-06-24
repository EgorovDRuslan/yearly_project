import requests
from requests.exceptions import HTTPError
import json
import load_data
import time
import os

URL = 'https://api.rawg.io/api/games'
try:
    with open('RAWG_API_KEY', 'r') as f:
        API = f.read().strip()
except FileNotFoundError:
    print("Error: RAWG_API_KEY file not found.")
    exit(1)
STATE_FILE = 'etl_state.json'
REQUESTS_LIMIT = 3000

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"current_page": 1}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

state = load_state()
page_number = state.get("current_page", 1)
requests_used_total = 0

print(f"Starting ETL process from page {page_number}. Request limit: {REQUESTS_LIMIT}")

while requests_used_total < REQUESTS_LIMIT:
    params = {
        'key' : API,
        'page': page_number 
    }
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status()
        requests_used_total += 1
        
        data_json = response.json()

        with open("rawg_response.json", "w", encoding='utf-8') as f:
            json.dump(data_json, f, indent=4, ensure_ascii=False)
        
        requests_left = REQUESTS_LIMIT - requests_used_total
        if requests_left <= 0:
            break
            
        print(f"Processing page {page_number}... (Used {requests_used_total}/{REQUESTS_LIMIT} requests)")
        
        requests_used_by_details = load_data.start(data_json, requests_left)
        requests_used_total += requests_used_by_details
        
        print(f"Page {page_number} processed. Entries found: {len(data_json.get('results', []))}. Total API requests used: {requests_used_total}")

        page_number += 1 
        state["current_page"] = page_number
        save_state(state)

        time.sleep(1.0)
        
        if not data_json.get('next'):
            print("No more pages available from RAWG API.")
            break

    except HTTPError as http_err:
        print(f"HTTP error has occured: {http_err}, while retrieving game on page number {page_number}")
        break
    except Exception as err:
        print(f"Error on page {page_number}: {err}")
        break

print(f"ETL completed. Stopped at page {page_number}. Total requests used: {requests_used_total}.")