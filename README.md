# **🎮 Steam Workshop Telegram Bot 🎮**

## **🌟 Overview**

The Steam Workshop Telegram Bot is a dedicated tool designed to monitor updates and additions in the Steam Workshop for selected games. Users receive real-time notifications about new or updated Workshop items with detailed information.

---

## **🚀 Features**

### **🔍 Workshop Monitoring**

- Tracks updates and new items in the Steam Workshop for user-selected games.
- Automatically sends notifications to users when changes occur.

### **📁 User-Specific Storage**

- Stores all user data, including:
  - Selected games for monitoring.
  - Known Workshop items to avoid duplicate notifications.

### **🔔 Detailed Notifications**

- Provides comprehensive details about each Workshop item, including:
  - Item title.
  - File size.
  - Number of subscriptions and lifetime subscriptions.
  - Favorites and lifetime favorites.
  - Tags.
  - Direct link to the Workshop item.

### **🕹️ User-Friendly Interface**

- Inline navigation buttons:
  - Start/stop monitoring.
  - View and manage selected games.
- Intuitive menu layout for easy interaction.

### **⚙️ Customizable Filters**

- Allows users to set filters for Workshop updates based on parameters like:
  - File size.
  - Subscriptions.
  - Favorites.
- Reset filters with a single command.

---

## **🛠️ Installation Guide**

### **Prerequisites**

- Python 3.11 or later.
- Telegram Bot API credentials.
- Steam Web API key.
- Required Python libraries: `pyrogram`, `requests`, and others listed in `requirements.txt`.

### **Where to Get API Keys**

#### Telegram Bot API Key&#x20;

1. Open Telegram and search for [@BotFather](https://t.me/botfather), the official Telegram bot for managing bots.
2. Start a chat with BotFather and use the `/newbot` command to create a new bot.
3. Follow the instructions to set up your bot and receive your API token (e.g., `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ`).
4. Copy the token provided (e.g., `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ`).

#### Telegram API ID and Hash

1. Visit the [Telegram API Authorization](https://my.telegram.org/auth) page and log in with your Telegram account.
2. Click on "API Development Tools."
3. Fill out the required form to create a new application.
4. After submission, you will receive your `API_ID` and `API_HASH`.

#### Steam Web API Key

1. Go to the [Steam Web API Key page](https://steamcommunity.com/dev/apikey).
2. Log in with your Steam account.
3. Enter a domain name (e.g., `localhost` if you are testing locally).
4. Click "Register" to receive your API key.
5. Copy the key provided (e.g., `ABCDEF1234567890ABCDEF1234567890`).

---

## **Step-by-Step Installation**

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Pfauberg/Steam-Workshop.git
   cd Steam-Workshop
   ```

2. **Set Up Python Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Required Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the Bot**

   - Rename a `config_example.ini` to a `config.ini` file in the project directory:
     ```ini
     [telegram]
     API_ID = "your_telegram_api_id"
     API_HASH = "your_telegram_api_hash"
     BOT_TOKEN = "your_bot_token"

     [steam]
     STEAM_API_KEY = "your_steam_api_key"
     ```

5. **Run the Bot**

   ```bash
   python main.py
   ```

6. **Start Interacting**

   - Open Telegram and start a conversation with your bot.
   - Use `/start` to begin.

---

## **🔧 Usage Instructions**

Some commands need to be typed as plain text and sent directly to the bot. The case does not matter, but the structure must be correct.

### **Examples:**

- Add a game for monitoring:
  ```
  add 123456
  ```
  or
  ```
  add https://store.steampowered.com/app/123456/
  ```
- Remove a game from monitoring:
  ```
  rm 123456
  ```

The bot provides a clear interface where the required command structures are displayed. Simply follow the instructions provided by the bot.

---

## **🌟 Try It Out**

You can test the bot directly on Telegram: [@steam\_workshop\_infobot](https://t.me/steam_workshop_infobot) [Temporarily unavailable]

---
