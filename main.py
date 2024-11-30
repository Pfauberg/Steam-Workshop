import configparser
import asyncio
import json
from pyrogram import Client, filters
from pyrogram.types import BotCommand
from pyrogram.enums import ParseMode
import requests

WELCOME_TEXT = "<b>Welcome! Available commands:</b>"
COMMANDS_DESCRIPTION = [
    {"command": "start", "description": "Bot's main menu"},
    {"command": "set", "description": "Manage your games list"},
]
GAME_LIST_HEADER = "<b>Steam games list:</b>"
GAME_LIST_EMPTY = "No games added yet."
ADD_GAME_USAGE = "To add a game, use: <code>add GAME_ID</code>"
REMOVE_GAME_USAGE = "To remove a game, use: <code>rm GAME_ID</code>"
ADD_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been added to your list."
ADD_GAME_DUPLICATE = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> is already in your list."
ADD_GAME_INVALID = "Invalid game ID: [ <code>{game_id}</code> ]. No such game found on Steam."
REMOVE_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been removed from your list."
REMOVE_GAME_NOT_FOUND = "Game [ <code>{game_id}</code> ] is not in your list."
INVALID_ADD_FORMAT = "Invalid format. Use: <code>add GAME_ID</code>"
INVALID_REMOVE_FORMAT = "Invalid format. Use: <code>rm GAME_ID</code>"

config = configparser.ConfigParser()
config.read('config.ini')

api_id = int(config['telegram']['API_ID'].strip('"'))
api_hash = config['telegram']['API_HASH'].strip('"')
bot_token = config['telegram']['BOT_TOKEN'].strip('"')

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

last_messages = {}
steam_games = {}

GAMES_FILE = "steam_games.json"


def load_games():
    global steam_games
    try:
        with open(GAMES_FILE, "r") as file:
            steam_games = json.load(file)
    except:
        steam_games = {}


def save_games():
    try:
        with open(GAMES_FILE, "w") as file:
            json.dump(steam_games, file)
    except:
        pass


def is_valid_game(game_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data[str(game_id)]["success"]:
                return True, data[str(game_id)]["data"]["name"]
        return False, None
    except:
        return False, None


async def delete_last_message(user_id, command, client, chat_id):
    if user_id in last_messages and command in last_messages[user_id]:
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=last_messages[user_id][command])
            del last_messages[user_id][command]
        except:
            pass


async def auto_delete_message(user_id, command, delay, client, chat_id):
    await asyncio.sleep(delay)
    if user_id in last_messages and command in last_messages[user_id]:
        await delete_last_message(user_id, command, client, chat_id)


@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.delete()
    await delete_last_message(message.from_user.id, "start", client, message.chat.id)
    commands = [BotCommand(cmd["command"], cmd["description"]) for cmd in COMMANDS_DESCRIPTION]
    await client.set_bot_commands(commands)
    text = WELCOME_TEXT
    for cmd in commands:
        text += f"\n<blockquote>/{cmd.command} - {cmd.description}</blockquote>"
    sent_message = await message.reply(text, parse_mode=ParseMode.HTML)
    if message.from_user.id not in last_messages:
        last_messages[message.from_user.id] = {}
    last_messages[message.from_user.id]["start"] = sent_message.id


@app.on_message(filters.private & filters.command("set"))
async def manage_games(client, message):
    await message.delete()
    await delete_last_message(message.from_user.id, "set", client, message.chat.id)
    game_list = "\n".join([f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]) or GAME_LIST_EMPTY
    text = (
        f"{GAME_LIST_HEADER}\n{game_list}\n\n"
        f"{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    )
    sent_message = await message.reply(text, parse_mode=ParseMode.HTML)
    if message.from_user.id not in last_messages:
        last_messages[message.from_user.id] = {}
    last_messages[message.from_user.id]["set"] = sent_message.id
    asyncio.create_task(auto_delete_message(message.from_user.id, "set", 300, client, message.chat.id))


@app.on_message(filters.private & filters.regex(r"^add\s\d+$"))
async def add_game(client, message):
    global steam_games
    await message.delete()
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        response_text = INVALID_ADD_FORMAT
    else:
        game_id = parts[1]
        is_valid, game_name = is_valid_game(game_id)
        if is_valid:
            if game_id not in steam_games:
                steam_games[game_id] = game_name
                save_games()
                response_text = ADD_GAME_SUCCESS.format(game_id=game_id, game_name=game_name)
            else:
                response_text = ADD_GAME_DUPLICATE.format(game_id=game_id, game_name=steam_games[game_id])
        else:
            response_text = ADD_GAME_INVALID.format(game_id=game_id)
    await delete_last_message(message.from_user.id, "set", client, message.chat.id)
    game_list = "\n".join([f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]) or GAME_LIST_EMPTY
    text = (
        f"{GAME_LIST_HEADER}\n{game_list}\n\n"
        f"{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    )
    sent_message = await message.reply(f"{response_text}\n\n{text}", parse_mode=ParseMode.HTML)
    if message.from_user.id not in last_messages:
        last_messages[message.from_user.id] = {}
    last_messages[message.from_user.id]["set"] = sent_message.id
    asyncio.create_task(auto_delete_message(message.from_user.id, "set", 300, client, message.chat.id))


@app.on_message(filters.private & filters.regex(r"^rm\s\d+$"))
async def remove_game(client, message):
    global steam_games
    await message.delete()
    parts = message.text.split()
    if len(parts) != 2:
        response_text = INVALID_REMOVE_FORMAT
    else:
        game_id = parts[1]
        if game_id in steam_games:
            removed_game = steam_games.pop(game_id)
            save_games()
            response_text = REMOVE_GAME_SUCCESS.format(game_id=game_id, game_name=removed_game)
        else:
            response_text = REMOVE_GAME_NOT_FOUND.format(game_id=game_id)
    await delete_last_message(message.from_user.id, "set", client, message.chat.id)
    game_list = "\n".join([f"[ <code>{game_id}</code> ] - {game_name}" for game_id, game_name in steam_games.items()]) or GAME_LIST_EMPTY
    text = (
        f"{GAME_LIST_HEADER}\n{game_list}\n\n"
        f"{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}"
    )
    sent_message = await message.reply(f"{response_text}\n\n{text}", parse_mode=ParseMode.HTML)
    if message.from_user.id not in last_messages:
        last_messages[message.from_user.id] = {}
    last_messages[message.from_user.id]["set"] = sent_message.id
    asyncio.create_task(auto_delete_message(message.from_user.id, "set", 300, client, message.chat.id))


@app.on_message(filters.private & filters.incoming)
async def delete_user_messages(client, message):
    await message.delete()


if __name__ == "__main__":
    load_games()
    app.run()
