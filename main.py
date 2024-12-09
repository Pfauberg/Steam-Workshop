import os
import configparser
import asyncio
import json
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import BotCommand
from pyrogram.enums import ParseMode
from datetime import datetime

WELCOME_MESSAGE = (
    "<b>Welcome to the <a href=\"https://t.me/steam_workshop_infobot\">Steam Workshop</a> bot!</b>\n"
    "<blockquote>It tracks updates and new items in Steam Workshop for your selected games.</blockquote>\n"
    "If you want to continue,\n\n"
    "<b>click: /set /set /set</b>\n"
)

WORKSHOP_ITEM_MESSAGE = (
    "<b>[ {game_name} ] – {title}</b>\n\n"
    "<b>💾 Size:</b> {file_size}\n\n"
    "<b>👁️ Views:</b> {views}\n"
    "<b>📥 Subscriptions:</b> {subscriptions} ({lifetime_subscriptions})\n"
    "<b>⭐ Favorited:</b> {favorited} ({lifetime_favorited})\n\n"
    "<b>🏷️ Tags:</b> {tags}\n\n"
    "<b>🔗 [ <a href=\"{item_url}\">View Item</a> ]</b>"
)

COMMANDS_DESCRIPTION = [
    {"command": "start", "description": "Bot's main menu"},
    {"command": "set", "description": "Manage your games list"},
    {"command": "run", "description": "Start monitoring workshops"},
    {"command": "stop", "description": "Stop monitoring workshops"}
]

GAME_LIST_HEADER = "<b>Steam games list:</b>"
GAME_LIST_EMPTY = "No games added yet."
ADD_GAME_USAGE = "To add a game, use: <code>add GAME_ID</code> or <code>add URL</code>"
REMOVE_GAME_USAGE = "To remove a game, use: <code>rm GAME_ID</code>"
ADD_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been added to your list."
ADD_GAME_DUPLICATE = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> is already in your list."
ADD_GAME_INVALID = "Invalid game ID: [ <code>{game_id}</code> ]. {error_message}"
ADD_GAME_NO_WORKSHOP = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> exists but does not have a Steam Workshop."
REMOVE_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been removed from your list."
REMOVE_GAME_NOT_FOUND = "Game [ <code>{game_id}</code> ] is not in your list."
INVALID_ADD_FORMAT = "Invalid format. Use: <code>add GAME_ID</code> or <code>add URL</code>"
INVALID_REMOVE_FORMAT = "Invalid format. Use: <code>rm GAME_ID</code>"
WORKSHOP_CHECK_FAILED = "Could not check if the game has a Steam Workshop."
MONITORING_STARTED = "Monitoring started."
MONITORING_ALREADY_RUNNING = "Monitoring is already running."
MONITORING_NO_GAMES = "You have no games added for monitoring."
MONITORING_STOPPED = "Monitoring stopped."
MONITORING_NOT_RUNNING = "Monitoring is not running."
SET_DISABLED_DURING_MONITORING = "You cannot use /set while monitoring is running. Please stop monitoring first."

config = configparser.ConfigParser()
config.read('config.ini')

api_id = int(config['telegram']['API_ID'].strip('"'))
api_hash = config['telegram']['API_HASH'].strip('"')
bot_token = config['telegram']['BOT_TOKEN'].strip('"')
steam_api_key = config["steam"]["STEAM_API_KEY"].strip('"')

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

last_messages = {}
monitoring_users = {}

USER_GAMES_FOLDER = "user_games"

if not os.path.exists(USER_GAMES_FOLDER):
    os.makedirs(USER_GAMES_FOLDER)


def get_user_dir(user_id):
    path = os.path.join(USER_GAMES_FOLDER, str(user_id))
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_user_games_file(user_id):
    return os.path.join(get_user_dir(user_id), "games.json")


def get_game_items_file(user_id, game_id):
    return os.path.join(get_user_dir(user_id), f"{game_id}.json")


def load_games(user_id):
    games_file = get_user_games_file(user_id)
    try:
        with open(games_file, "r") as file:
            games = json.load(file)
    except:
        games = {}
    return games


def save_games(user_id, games):
    games_file = get_user_games_file(user_id)
    try:
        with open(games_file, "w") as file:
            json.dump(games, file)
    except Exception as e:
        print(f"Error saving games for user {user_id}: {e}")


def load_game_items_info(user_id, game_id):
    path = get_game_items_file(user_id, game_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_game_items_info(user_id, game_id, items_dict):
    path = get_game_items_file(user_id, game_id)
    with open(path, "w") as f:
        json.dump(items_dict, f)


def is_valid_game(game_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data[str(game_id)]["success"]:
                app_data = data[str(game_id)]["data"]
                if app_data["type"] == "game":
                    return True, app_data["name"]
                else:
                    return False, f"Type is {app_data['type']}"
            else:
                return False, "Game ID not found."
        else:
            return False, f"HTTP Error {response.status_code}"
    except Exception:
        return False, "Exception occurred during game validation."


def check_workshop_exists(app_id, api_key):
    url = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
    params = {
        "key": api_key,
        "appid": app_id,
        "query_type": 0,
        "numperpage": 1,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        total_items = data.get("response", {}).get("total", 0)
        if total_items > 0:
            return True
        return False
    except requests.exceptions.RequestException:
        return None


async def delete_last_message(user_id, command, client, chat_id):
    if user_id in last_messages and command in last_messages[user_id]:
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=last_messages[user_id][command])
            del last_messages[user_id][command]
        except:
            pass


def extract_game_id(input_str):
    if input_str.isdigit():
        return input_str
    pattern = r"^https?://store\.steampowered\.com/app/(\d+)/"
    match = re.match(pattern, input_str)
    if match:
        return match.group(1)
    else:
        return None


@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.delete()
    user_id = message.from_user.id
    await delete_last_message(user_id, "start", client, message.chat.id)
    commands = [BotCommand(cmd["command"], cmd["description"]) for cmd in COMMANDS_DESCRIPTION]
    await client.set_bot_commands(commands)
    sent_message = await message.reply(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)
    if user_id not in last_messages:
        last_messages[user_id] = {}
    last_messages[user_id]["start"] = sent_message.id


@app.on_message(filters.private & filters.command("set"))
async def manage_games(client, message):
    await message.delete()
    user_id = message.from_user.id
    if user_id in monitoring_users:
        await message.reply(SET_DISABLED_DURING_MONITORING, parse_mode=ParseMode.HTML)
        return
    await delete_last_message(user_id, "set", client, message.chat.id)
    steam_games = load_games(user_id)
    game_list = "\n".join(
        [f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]
    ) or GAME_LIST_EMPTY
    text = f"{GAME_LIST_HEADER}\n{game_list}\n\n{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    sent_message = await message.reply(text, parse_mode=ParseMode.HTML)
    if user_id not in last_messages:
        last_messages[user_id] = {}
    last_messages[user_id]["set"] = sent_message.id


@app.on_message(filters.private & filters.regex(r"(?i)^add\s+"))
async def add_game(client, message):
    await message.delete()
    user_id = message.from_user.id
    if user_id in monitoring_users:
        await message.reply(SET_DISABLED_DURING_MONITORING, parse_mode=ParseMode.HTML)
        return
    steam_games = load_games(user_id)
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        response_text = INVALID_ADD_FORMAT
    else:
        input_str = parts[1]
        game_id = extract_game_id(input_str)
        if game_id:
            is_valid_, game_name_or_error = is_valid_game(game_id)
            if is_valid_:
                game_name = game_name_or_error
                if game_id not in steam_games:
                    has_workshop = check_workshop_exists(game_id, steam_api_key)
                    if has_workshop is True:
                        steam_games[game_id] = game_name
                        save_games(user_id, steam_games)
                        response_text = ADD_GAME_SUCCESS.format(
                            game_id=game_id, game_name=game_name
                        )
                    elif has_workshop is False:
                        response_text = ADD_GAME_NO_WORKSHOP.format(
                            game_id=game_id, game_name=game_name
                        )
                    else:
                        response_text = WORKSHOP_CHECK_FAILED
                else:
                    response_text = ADD_GAME_DUPLICATE.format(
                        game_id=game_id, game_name=steam_games[game_id]
                    )
            else:
                error_message = game_name_or_error
                response_text = ADD_GAME_INVALID.format(
                    game_id=game_id, error_message=error_message
                )
        else:
            response_text = INVALID_ADD_FORMAT
    await delete_last_message(user_id, "set", client, message.chat.id)
    game_list = "\n".join(
        [f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]
    ) or GAME_LIST_EMPTY
    text = f"{GAME_LIST_HEADER}\n{game_list}\n\n{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    sent_message = await message.reply(f"{response_text}\n\n{text}", parse_mode=ParseMode.HTML)
    if user_id not in last_messages:
        last_messages[user_id] = {}
    last_messages[user_id]["set"] = sent_message.id


@app.on_message(filters.private & filters.regex(r"(?i)^rm\s\d+$"))
async def remove_game(client, message):
    await message.delete()
    user_id = message.from_user.id
    if user_id in monitoring_users:
        await message.reply(SET_DISABLED_DURING_MONITORING, parse_mode=ParseMode.HTML)
        return
    steam_games = load_games(user_id)
    parts = message.text.strip().split()
    if len(parts) != 2:
        response_text = INVALID_REMOVE_FORMAT
    else:
        game_id = parts[1]
        if game_id in steam_games:
            removed_game = steam_games.pop(game_id)
            save_games(user_id, steam_games)
            response_text = REMOVE_GAME_SUCCESS.format(
                game_id=game_id, game_name=removed_game
            )
        else:
            response_text = REMOVE_GAME_NOT_FOUND.format(game_id=game_id)
    await delete_last_message(user_id, "set", client, message.chat.id)
    game_list = "\n".join(
        [f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]
    ) or GAME_LIST_EMPTY
    text = f"{GAME_LIST_HEADER}\n{game_list}\n\n{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    sent_message = await message.reply(f"{response_text}\n\n{text}", parse_mode=ParseMode.HTML)
    if user_id not in last_messages:
        last_messages[user_id] = {}
    last_messages[user_id]["set"] = sent_message.id


@app.on_message(filters.private & filters.command("run"))
async def start_monitoring(client, message):
    await message.delete()
    user_id = message.from_user.id
    if user_id in monitoring_users:
        await message.reply(MONITORING_ALREADY_RUNNING, parse_mode=ParseMode.HTML)
        return
    steam_games = load_games(user_id)
    if not steam_games:
        await message.reply(MONITORING_NO_GAMES, parse_mode=ParseMode.HTML)
        return
    await message.reply(MONITORING_STARTED, parse_mode=ParseMode.HTML)
    monitoring_users[user_id] = {
        "task": asyncio.create_task(monitor_workshops(client, user_id)),
        "last_items": {}
    }


async def monitor_workshops(client, user_id):
    last_items = monitoring_users[user_id]["last_items"]
    try:
        while user_id in monitoring_users:
            steam_games = load_games(user_id)
            for game_id, game_name in steam_games.items():
                first_run = (game_id not in last_items)
                new_items = await get_new_workshop_items(game_id, last_items.get(game_id))
                known_items = load_game_items_info(user_id, game_id)
                if not first_run and new_items:
                    for item in new_items:
                        await process_and_send_item(known_items, user_id, game_id, game_name, item, client, send_if_new_or_updated=True)
                    last_items[game_id] = new_items[0]['publishedfileid']
                    save_game_items_info(user_id, game_id, known_items)
                elif first_run and new_items:
                    first = True
                    for item in new_items:
                        if first:
                            await process_and_send_item(known_items, user_id, game_id, game_name, item, client, send_if_new_or_updated=True)
                            first = False
                        else:
                            await process_and_send_item(known_items, user_id, game_id, game_name, item, client, send_if_new_or_updated=False)
                    last_items[game_id] = new_items[0]['publishedfileid']
                    save_game_items_info(user_id, game_id, known_items)
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in monitoring loop for user {user_id}: {e}")


async def get_new_workshop_items(game_id, last_publishedfileid):
    params = {
        'key': steam_api_key,
        'appid': game_id,
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
    url = 'https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/'
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get('response', {}).get('publishedfiledetails', [])
        if not items:
            return []
        items.sort(key=lambda x: x.get('time_updated', 0), reverse=True)
        if not last_publishedfileid:
            return items
        new_items = []
        for item in items:
            if item['publishedfileid'] == last_publishedfileid:
                break
            new_items.append(item)
        return new_items
    except Exception as e:
        print(f"Error fetching workshop items for game {game_id}: {e}")
        return []


async def process_and_send_item(known_items, user_id, game_id, game_name, item, client, send_if_new_or_updated):
    publishedfileid = item.get('publishedfileid')
    time_updated = int(item.get('time_updated', 0))
    old_time = known_items.get(publishedfileid, 0)
    if time_updated > old_time:
        known_items[publishedfileid] = time_updated
        if send_if_new_or_updated:
            await send_workshop_item(client, user_id, game_name, item)


async def send_workshop_item(client, user_id, game_name, item):
    title = item.get('title', 'No Title')
    file_size_bytes = int(item.get('file_size', 0))
    file_size = "N/A"

    if file_size_bytes > 0:
        if file_size_bytes >= 1_073_741_824:
            file_size = f"{file_size_bytes / 1_073_741_824:.2f} GB"
        elif file_size_bytes >= 1_048_576:
            file_size = f"{file_size_bytes / 1_048_576:.2f} MB"
        else:
            file_size = f"{file_size_bytes / 1024:.2f} KB"

    subscriptions = item.get('subscriptions', 0)
    favorited = item.get('favorited', 0)
    lifetime_subscriptions = item.get('lifetime_subscriptions', 0)
    lifetime_favorited = item.get('lifetime_favorited', 0)
    views = item.get('views', 0)
    tags = ', '.join([tag.get('tag', '') for tag in item.get('tags', [])]) if item.get('tags') else 'N/A'
    item_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item.get('publishedfileid', 'N/A')}"

    message_text = WORKSHOP_ITEM_MESSAGE.format(
        game_name=game_name,
        title=title,
        file_size=file_size,
        subscriptions=subscriptions,
        favorited=favorited,
        lifetime_subscriptions=lifetime_subscriptions,
        lifetime_favorited=lifetime_favorited,
        views=views,
        tags=tags,
        item_url=item_url
    )

    await client.send_message(chat_id=user_id, text=message_text, parse_mode=ParseMode.HTML)


@app.on_message(filters.private & filters.command("stop"))
async def stop_monitoring(client, message):
    await message.delete()
    user_id = message.from_user.id
    if user_id not in monitoring_users:
        await message.reply(MONITORING_NOT_RUNNING, parse_mode=ParseMode.HTML)
        return
    monitoring_users[user_id]["task"].cancel()
    del monitoring_users[user_id]
    await message.reply(MONITORING_STOPPED, parse_mode=ParseMode.HTML)


@app.on_message(filters.private & filters.incoming)
async def delete_user_messages(client, message):
    await message.delete()


if __name__ == "__main__":
    app.run()
