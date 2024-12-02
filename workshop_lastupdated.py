import requests
from datetime import datetime
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
api_key = config['steam']['STEAM_API_KEY'].strip('"')

BASE_URL = 'https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/'

try:
    app_id = int(input("Enter the App ID of the game's workshop to parse: "))
except ValueError:
    print("Invalid input. Please enter a numeric App ID.")
    exit(1)

params = {
    'key': api_key,
    'appid': app_id,
    'query_type': 21,
    'numperpage': 10,
    'page': 1,
    'return_metadata': True,
}

response = requests.get(BASE_URL, params=params)

if response.status_code == 200:
    data = response.json()
    items = data.get('response', {}).get('publishedfiledetails', [])
    if items:
        print("\nWorkshop items sorted by Last Updated:")
        for item in items:
            title = item.get('title', 'No Title')
            time_updated = int(item.get('time_updated', 0))
            readable_time = datetime.utcfromtimestamp(time_updated).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Title: {title}, Last Updated: {readable_time}")
    else:
        print("No items found for the specified game.")
else:
    print(f"Error: {response.status_code}, Message: {response.text}")
