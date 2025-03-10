import requests
import time
import csv
from itertools import cycle

base_url = "https://catalog.roblox.com/v2/search/items/details"

response: requests.Response = requests.get("https://api.mullvad.net/www/relays/wireguard/")
raw_proxies = []

try:
    json_data = response.json()
    if not isinstance(json_data, list):
        print("Unexpected response format:", json_data)

    for relay in json_data:
        if isinstance(relay, dict) and relay.get("active"):
            fqdn = relay.get("fqdn")
            port = relay.get("socks_port")
            raw_proxies.append(f"{fqdn}:{port}")

except ValueError as e:
    print("Failed to parse JSON:", str(e))

proxies = cycle(raw_proxies)

def get_roblox_made_gear():
    gear_items = []
    cursors = []
    append = "?IncludeNotForSale=true&limit=120&AssetTypeIds=19"
    url = base_url + append
    local_proxies = proxies

    def make_request(current_url):
        tries = 1
        limit = 5
        delay = 30

        while True:
            if tries >= limit:
                print(f"❗ Request limit exceeded ({limit}) - Breaking")
                return None

            response = requests.get(current_url, proxies={'http': next(local_proxies)})

            if response.status_code == 429:
                tries += 1
                print(f"❗ Received 429 status code. Retrying after {delay} seconds...")
                time.sleep(delay)
                continue

            return response

    def list_in_list(sub_list: list, main_list: list) -> bool:
        return all(element in main_list for element in sub_list)

    LOOP = True
    while LOOP:
        response: requests.Response | None = make_request(url)
        
        if not response:
            print("❗ Response is None - continuing loop")
            continue

        if response.status_code != 200:
            print(f"❗ Failed to fetch data. Status code: {response.status_code}")
            break

        data: dict = response.json()
        items: list = data.get('data', [])
        cursor: str | None = data.get('nextPageCursor', None)

        # if cursor in cursors:
        #     print("Duplicate cursor found. Possibly looping back - Breaking loop")
        #     LOOP = False
        #     break

        if cursor:
            cursors.append(cursor)
            url = f"{base_url}{append}&cursor={cursor}"

        if not items:
            break
        
        if list_in_list(items, gear_items):
            print("❗ Duplicate list found. Possibly looping back - Broke loop")
            LOOP = False
            break

        for item in items:
            gear_items.append(item)

        print(f"✅ Appended {len(items)} gear items")
        
        time.sleep(0.01)

    return gear_items

roblox_gear_items = get_roblox_made_gear()
data: list[list[str]] = [["id", "name"]]
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
print("Total gears scraped:", len(roblox_gear_items))