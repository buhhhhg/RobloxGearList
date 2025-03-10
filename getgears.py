import requests
import time
import csv
from itertools import cycle

base_url = "https://catalog.roblox.com/v2/search/items/details"
api_mullvad = "https://api.mullvad.net/www/relays/wireguard/"

response = requests.get(api_mullvad)
proxiess = []
try:
    json_data = response.json()
    if isinstance(json_data, list):
        for relay in json_data:
            if isinstance(relay, dict) and relay.get("active"):
                fqdn = relay.get("fqdn")
                port = relay.get("socks_port")
                proxiess.append(f"{fqdn}:{port}")
    else:
        print("Unexpected response format:", json_data)
except ValueError as e:
    print("Failed to parse JSON:", str(e))

proxies = cycle(proxiess)

def get_roblox_made_gear():
    gear_items = []
    cursors = []
    url = f"{base_url}?IncludeNotForSale=true&limit=120&AssetTypeIds=19"
    local_proxies = proxies

    def make_request(current_url):
        tries = 1
        limit = 10
        delay = 25

        while True:
            if tries >= limit:
                print(f"Request limit exceeded ({limit}) - Breaking")
                return None

            response = requests.get(current_url, proxies={'http': next(local_proxies)})

            if response.status_code == 429:
                tries += 1
                print(f"Received 429 status code. Retrying after {delay} seconds...")
                time.sleep(delay)
                continue

            return response

    def list_in_list(sub_list: list, main_list: list) -> bool:
        return all(element in main_list for element in sub_list)

    LOOP = True
    while LOOP:
        response = make_request(url)
        
        if not response:
            print("Response is None - continuing")
            continue

        if response.status_code == 200:
            data = response.json()
            items = data.get('data', [])
            cursor = data.get('nextPageCursor', None)

            # if cursor in cursors:
            #     print("Duplicate cursor found. Possibly looping back - Breaking loop")
            #     LOOP = False
            #     break

            if cursor:
                cursors.append(cursor)
                url = f"{base_url}?IncludeNotForSale=true&limit=120&AssetTypeIds=19&cursor={cursor}"

            if not items:
                break
            
            for item in items:
                if list_in_list(items, gear_items):
                    print("Duplicate list found. Possibly looping back - Continuing")
                    LOOP = False
                    continue
    
                gear_items.append(item)

            print(f"✅ Appended {len(items)} gear items")
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            break
        
        time.sleep(10)

    return gear_items

roblox_gear_items = get_roblox_made_gear()
data = [["id", "name"]]
final = ""

for gear in roblox_gear_items:
    data.append([gear['id'], gear['name']])
    final += f"ID: {gear['id']}, Name: {gear['name']}\n"

final = final.removesuffix('\n')

with open('data.csv', 'w', newline="", encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerows(data)

with open('data.txt', 'w', encoding='utf-8') as file:
    file.write(final)

print('')
print("Total gears scraped:", str(len(roblox_gear_items)))