import requests
from bs4 import BeautifulSoup

def check_workshop(app_id):
    workshop_url = f"https://steamcommunity.com/app/{app_id}/workshop/"

    try:
        response = requests.get(workshop_url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            page_title = soup.find('div', {'class': 'apphub_HeaderTop'})
            if page_title and "Workshop" in page_title.get_text():
                return True

            empty_notice = soup.find('div', {'class': 'noItemsNotice'})
            if empty_notice:
                return False

            popular_items_header = soup.find('div', {'class': 'workshopBrowseHeader'})
            if popular_items_header:
                return True

            return False
        elif response.status_code == 404:
            return False
        else:
            print(f"Unexpected HTTP status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

def main():
    print("Workshop Existence Checker")
    while True:
        app_id = input("Enter the AppID of the game (or type 'exit' to quit): ").strip()

        if app_id.lower() == 'exit':
            print("Exiting the script. Goodbye!")
            break

        if not app_id.isdigit():
            print("Error: AppID must be a number.")
            continue

        print("Checking...")
        has_workshop = check_workshop(app_id)

        if has_workshop is True:
            print(f"The game with AppID {app_id} has a Steam Workshop!")
        elif has_workshop is False:
            print(f"The game with AppID {app_id} does not have a Steam Workshop.")
        else:
            print("Could not complete the check.")

if __name__ == "__main__":
    main()
