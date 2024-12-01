import requests
import json
import re
import configparser
import sys

def load_api_key(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    try:
        return config["steam"]["STEAM_API_KEY"].strip('"')
    except KeyError:
        print("Error: Could not find the API key in config.ini.")
        sys.exit(1)

def extract_published_file_id(workshop_url):
    match = re.search(r"id=(\d+)", workshop_url)
    if match:
        return match.group(1)
    else:
        print("Error: Unable to extract PublishedFileID from the URL.")
        sys.exit(1)

def get_workshop_details(api_key, published_file_id):
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    payload = {
        "key": api_key,
        "itemcount": 1,
        "publishedfileids[0]": published_file_id
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()

        if "response" in data and "publishedfiledetails" in data["response"]:
            return data["response"]["publishedfiledetails"][0]
        else:
            raise ValueError("Unexpected API response format.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Response processing error: {e}")
        sys.exit(1)

def main():
    config_file = "config.ini"
    api_key = load_api_key(config_file)

    print("Workshop Item Parser")
    while True:
        workshop_url = input("Enter the Steam Workshop item URL (or type 'exit' to quit): ").strip()
        if workshop_url.lower() == 'exit':
            print("Exiting the script. Goodbye!")
            break

        published_file_id = extract_published_file_id(workshop_url)
        details = get_workshop_details(api_key, published_file_id)

        print("\nWorkshop Item Details:")
        print(json.dumps(details, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
