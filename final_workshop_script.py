import requests
from datetime import datetime
import configparser
import sys
import json

config_file = "config.ini"
config = configparser.ConfigParser()
config.read(config_file)
try:
    api_key = config["steam"]["STEAM_API_KEY"].strip('"')
except KeyError:
    print("Error: Could not find the API key in config.ini.")
    sys.exit(1)

def main():
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
        'return_tags': True,
        'return_kv_tags': True,
        'return_previews': True,
        'return_children': True,
        'return_short_description': True,
        'return_for_sale_data': True,
        'return_details': True,
        'return_vote_data': True,
        'return_playtime_stats': 1,
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        data = response.json()
        items = data.get('response', {}).get('publishedfiledetails', [])
        if items:
            print("\nWorkshop items sorted by Last Updated:")
            publishedfileids = []
            for item in items:
                title = item.get('title', 'No Title')
                time_updated = int(item.get('time_updated', 0))
                readable_time = datetime.utcfromtimestamp(time_updated).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Title: {title}, Last Updated: {readable_time}")
                publishedfileids.append(item.get('publishedfileid'))

            url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
            payload = {
                "key": api_key,
                "itemcount": len(publishedfileids),
            }
            for idx, fileid in enumerate(publishedfileids):
                payload[f"publishedfileids[{idx}]"] = fileid

            try:
                detail_response = requests.post(url, data=payload)
                detail_response.raise_for_status()
                detail_data = detail_response.json()

                if "response" in detail_data and "publishedfiledetails" in detail_data["response"]:
                    details_list = detail_data["response"]["publishedfiledetails"]
                    print("\nDetailed Workshop Item Information:")
                    for details in details_list:
                        print(json.dumps(details, indent=4, ensure_ascii=False))
                else:
                    print("No detailed information found.")
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")
                sys.exit(1)
            except ValueError as e:
                print(f"Response processing error: {e}")
                sys.exit(1)
        else:
            print("No items found for the specified game.")
    else:
        print(f"Error: {response.status_code}, Message: {response.text}")

if __name__ == "__main__":
    main()
