import requests
from requests.exceptions import HTTPError
import json
import load_data
import time

URL = 'https://api.rawg.io/api/games'
API = '755e964103a14e4f94dad0a1a06e9947'

page_number = 2
while page_number <= 3:
    params = {
    'key' : API,
    'page': page_number 
    }
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status()
        data_json = response.json()

        with open("rawg_response.json", "w", encoding='utf-8') as f:
            json.dump(data_json, f, indent=4, ensure_ascii=False)
        
        load_data.start(data_json)

        page_number = page_number + 1 

        print(f"{len(data_json['results'])} entries has been retrived ")
        time.sleep(1.0)
    except HTTPError as http_err:
        print(f"HTTP error has occured: {http_err}, while retrieving game on page number {page_number}")
    except Exception as err:
        print(f"Error on page {page_number}: {err}")
        break