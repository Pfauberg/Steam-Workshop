# Steam Workshop Telegram Bot

## Idea
A Telegram bot that delivers real-time updates about mods in the Steam Workshop for selected games.

## Current Features
- **File: `main.py`**
  - `/start`: Displays the command menu.
  - `/set`: Allows users to manage their list of games for monitoring mod updates.
    - Add games using `add GAME_ID` or `add URL`.
    - Remove games using `rm GAME_ID`.
    - View the current list of monitored games.
  - `/run`: Starts monitoring Steam Workshop updates for the games configured via `/set`.
  - `/stop`: Stops the monitoring process.
  - Automatically deletes incoming user messages to maintain a clean chat interface.

## Future Features
- **Message Styling:** Improve the visual appearance of mod update messages for better readability and presentation.
- **Like/Dislike System:** React to mods with likes or dislikes to manage a favorites list or blacklist.
- **Advanced Filters:** Customize `/set` to filter updates based on specific mod characteristics, such as tags or update frequency.