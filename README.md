# Steam Workshop Telegram Bot

## Idea
A Telegram bot that delivers real-time updates about mods in the Steam Workshop for selected games.

## Current Features
- **File: `main.py`**
  - `/start`: Displays the command menu.
  - `/set`: Allows users to configure which games to monitor for mod updates.
- **File: `final_workshop_script.py`**
  - Retrieves the latest updated Workshop items for a specific game using its Steam App ID.
  - Fetches detailed information about each Workshop item.

## Future Features
- **Commands to be added by integrating `final_workshop_script.py` into `main.py`:**  
  - `/run`: Start monitoring Steam Workshop updates for games configured via `/set`.  
  - `/stop`: Stop the monitoring process.  
- Like/Dislike system for mods to manage a favorites list and a blacklist.  
- Advanced filters in `/set` to customize updates based on specific criteria (e.g., mod tags, update frequency, etc.).