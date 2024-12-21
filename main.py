import os
import configparser
import asyncio
import json
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified


GAME_LIST_HEADER = "<b>Steam games list:</b>"
GAME_LIST_EMPTY = "No games added yet."
ADD_GAME_USAGE = "To add a game, type: <code>Add GAME_ID</code> or <code>Add URL</code>"
REMOVE_GAME_USAGE = "To remove a game, type: <code>Rm GAME_ID</code>"

ADD_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been added to your list."
ADD_GAME_DUPLICATE = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> is already in your list."
ADD_GAME_INVALID = "Invalid game ID: [ <code>{game_id}</code> ]. {error_message}"
ADD_GAME_NO_WORKSHOP = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> exists but does not have a Steam Workshop."
REMOVE_GAME_SUCCESS = "Game [ <code>{game_id}</code> ] - <b>\"{game_name}\"</b> has been removed from your list."
REMOVE_GAME_NOT_FOUND = "Game [ <code>{game_id}</code> ] is not in your list."
INVALID_ADD_FORMAT = "Invalid format. Use: <code>add GAME_ID</code> or <code>add URL</code>"
INVALID_REMOVE_FORMAT = "Incorrect format. Use: <code>rm GAME_ID</code>"
WORKSHOP_CHECK_FAILED = "Could not check if the game has a Steam Workshop."

MONITORING_STARTED = "Monitoring started."
MONITORING_ALREADY_RUNNING = "Monitoring is already running."
MONITORING_NO_GAMES = "You have no games added for monitoring."
MONITORING_STOPPED = "Monitoring stopped."
MONITORING_NOT_RUNNING = "Monitoring is not running."
SET_DISABLED_DURING_MONITORING = "You cannot modify the game list while monitoring is running."

WORKSHOP_ITEM_MESSAGE = (
    "<b>[ {game_name} ] – {title}</b> <i>{item_type}</i>\n\n"
    "<b>💾 Size:</b> {file_size}\n\n"
    "<b>📥 Subscriptions:</b> {subscriptions} ({lifetime_subscriptions})\n\n"
    "<b>⭐ Favorited:</b> {favorited} ({lifetime_favorited})\n\n"
    "<b>🏷️ Tags:</b> {tags}\n\n"
    "<b>🔗 [ <a href=\"{item_url}\">View Item</a> ]</b>"
)

SET_MENU_TEMPLATE = (
    "{game_list_header}\n"
    "{game_list}\n\n"
    "{add_game_usage}\n"
    "{remove_game_usage}\n\n"
    "{footer}"
)

WELCOME_MESSAGE = "<b>❗️ W E L C O M E ❗️</b>"

SETTINGS_SUBMENU_TEXT_UPDATED = (
    "<b>[ Last Updated ] ⚙️ Settings Page</b> ⚙️\n\n"
    "📝 <b>Current filters:</b>\n<blockquote>{current_filters}</blockquote>\n\n"
    "🛠 <b>Set filters using these examples (send the command as a message):</b>\n"
    "<blockquote><code>set size >100mb</code> <b>- Filter by file size</b>\n"
    "<code>set subs <10000</code> <b>- Filter by subscriptions</b>\n"
    "<code>set ltfavs off</code> <b>- Disable lifetime favorited filter</b></blockquote>\n\n"
    "☑️ <b>Available filters:</b>\n"
    "<blockquote><code>size</code> <b>- File size</b>\n"
    "<code>subs</code> <b>- Subscriptions</b>\n"
    "<code>ltsubs</code> <b>- Lifetime subscriptions</b>\n"
    "<code>favs</code> <b>- Favorited</b>\n"
    "<code>ltfavs</code> <b>- Lifetime favorited</b></blockquote>\n\n"
    "⚙️ <b>Operators:</b> [ <code>></code>  ] <b>and</b> [ <code><</code>  ]\n"
    "📐 <b>Use</b> [ <code>kb</code>  ][ <code>mb</code>  ][ <code>gb</code>  ] <b>for size</b>\n\n"
    "<b>To reset all filters, type:</b> <code>Reset</code>"
)

SETTINGS_SUBMENU_TEXT_NEW = (
    "<b>[ Most Recent ] ⚙️ Settings Page</b> ⚙️\n\n"
    "📝 <b>Current filters:</b>\n<blockquote>{current_filters}</blockquote>\n\n"
    "🛠 <b>Set filters using these examples (send the command as a message):</b>\n"
    "<blockquote><code>set size >100mb</code> <b>- Filter by file size</b>\n"
    "<code>set subs <10000</code> <b>- Filter by subscriptions</b>\n"
    "<code>set ltfavs off</code> <b>- Disable lifetime favorited filter</b></blockquote>\n\n"
    "☑️ <b>Available filters:</b>\n"
    "<blockquote><code>size</code> <b>- File size</b>\n"
    "<code>subs</code> <b>- Subscriptions</b>\n"
    "<code>ltsubs</code> <b>- Lifetime subscriptions</b>\n"
    "<code>favs</code> <b>- Favorited</b>\n"
    "<code>ltfavs</code> <b>- Lifetime favorited</b></blockquote>\n\n"
    "⚙️ <b>Operators:</b> [ <code>></code>  ] <b>and</b> [ <code><</code>  ]\n"
    "📐 <b>Use</b> [ <code>kb</code>  ][ <code>mb</code>  ][ <code>gb</code>  ] <b>for size</b>\n\n"
    "<b>To reset all filters, type:</b> <code>Reset</code>"
)


config = configparser.ConfigParser()
config.read('config.ini')

api_id = int(config['telegram']['API_ID'].strip('"'))
api_hash = config['telegram']['API_HASH'].strip('"')
bot_token = config['telegram']['BOT_TOKEN'].strip('"')
steam_api_key = config["steam"]["STEAM_API_KEY"].strip('"')

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

running_tasks = {}

USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({"users": {}}, f)


def load_all_data():
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_all_data(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_user_data(user_id):
    data = load_all_data()
    users = data.get("users", {})
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "games": {},
            "filters_updated": {},
            "filters_new": {},
            "known_items": {},
            "last_items": {},
            "known_items_new": {},
            "last_items_new": {},
            "runtime": {
                "is_monitoring": False,
                "last_messages": {},
                "user_mode": None,
                "send_updated_enabled": True,
                "send_new_enabled": True
            }
        }
        data["users"] = users
        save_all_data(data)
    return data, users[user_id_str]


def save_user_data(user_id, user_data):
    data = load_all_data()
    data["users"][str(user_id)] = user_data
    save_all_data(data)


def user_is_known(user_id):
    data = load_all_data()
    return str(user_id) in data.get("users", {})


def add_user_to_known(user_id):
    _, _ = get_user_data(user_id)


def load_games(user_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("games", {})


def save_games(user_id, games):
    data, user_data = get_user_data(user_id)
    user_data["games"] = games
    save_user_data(user_id, user_data)


def load_user_filters_updated(user_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("filters_updated", {})


def save_user_filters_updated(user_id, filters_data):
    data, user_data = get_user_data(user_id)
    user_data["filters_updated"] = filters_data
    save_user_data(user_id, user_data)


def load_user_filters_new(user_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("filters_new", {})


def save_user_filters_new(user_id, filters_data):
    data, user_data = get_user_data(user_id)
    user_data["filters_new"] = filters_data
    save_user_data(user_id, user_data)


def set_user_filter_updated(user_id, filter_name, filter_data):
    data, user_data = get_user_data(user_id)
    f = user_data.get("filters_updated", {})
    if filter_data is None:
        if filter_name in f:
            del f[filter_name]
    else:
        f[filter_name] = filter_data
    user_data["filters_updated"] = f
    user_data["known_items"] = {}
    user_data["last_items"] = {}
    save_user_data(user_id, user_data)


def set_user_filter_new(user_id, filter_name, filter_data):
    data, user_data = get_user_data(user_id)
    f = user_data.get("filters_new", {})
    if filter_data is None:
        if filter_name in f:
            del f[filter_name]
    else:
        f[filter_name] = filter_data
    user_data["filters_new"] = f
    user_data["known_items_new"] = {}
    user_data["last_items_new"] = {}
    save_user_data(user_id, user_data)


def load_game_items_info(user_id, game_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("known_items", {}).get(game_id, {})


def save_game_items_info(user_id, game_id, items_dict):
    data, user_data = get_user_data(user_id)
    known_items = user_data.get("known_items", {})
    known_items[game_id] = items_dict
    user_data["known_items"] = known_items
    save_user_data(user_id, user_data)


def load_game_items_info_new(user_id, game_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("known_items_new", {}).get(game_id, {})


def save_game_items_info_new(user_id, game_id, items_dict):
    data, user_data = get_user_data(user_id)
    known_items_new = user_data.get("known_items_new", {})
    known_items_new[game_id] = items_dict
    user_data["known_items_new"] = known_items_new
    save_user_data(user_id, user_data)


def get_last_publishedfileid(user_id, game_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("last_items", {}).get(game_id)


def set_last_publishedfileid(user_id, game_id, file_id):
    data, user_data = get_user_data(user_id)
    last_items = user_data.get("last_items", {})
    last_items[game_id] = file_id
    user_data["last_items"] = last_items
    save_user_data(user_id, user_data)


def get_last_publishedfileid_new(user_id, game_id):
    _, user_data = get_user_data(user_id)
    return user_data.get("last_items_new", {}).get(game_id)


def set_last_publishedfileid_new(user_id, game_id, file_id):
    data, user_data = get_user_data(user_id)
    last_items_new = user_data.get("last_items_new", {})
    last_items_new[game_id] = file_id
    user_data["last_items_new"] = last_items_new
    save_user_data(user_id, user_data)


def get_user_runtime_data(user_id):
    _, user_data = get_user_data(user_id)
    return user_data.setdefault("runtime", {})


def save_user_runtime_data(user_id, runtime_data):
    data, user_data = get_user_data(user_id)
    user_data["runtime"] = runtime_data
    save_user_data(user_id, user_data)


def get_last_message_id(user_id, command):
    r = get_user_runtime_data(user_id)
    lm = r.setdefault("last_messages", {})
    return lm.get(command)


def set_last_message_id(user_id, command, msg_id):
    r = get_user_runtime_data(user_id)
    lm = r.setdefault("last_messages", {})
    lm[command] = msg_id
    save_user_runtime_data(user_id, r)


def delete_last_message_id(user_id, command):
    r = get_user_runtime_data(user_id)
    lm = r.setdefault("last_messages", {})
    if command in lm:
        del lm[command]
    save_user_runtime_data(user_id, r)


def set_user_mode(user_id, mode):
    r = get_user_runtime_data(user_id)
    r["user_mode"] = mode
    save_user_runtime_data(user_id, r)


def get_user_mode(user_id):
    r = get_user_runtime_data(user_id)
    return r.get("user_mode", None)


def set_monitoring_status(user_id, status_bool):
    r = get_user_runtime_data(user_id)
    r["is_monitoring"] = status_bool
    save_user_runtime_data(user_id, r)


def is_user_monitoring(user_id):
    r = get_user_runtime_data(user_id)
    return r.get("is_monitoring", False)


def get_send_updated_enabled(user_id):
    r = get_user_runtime_data(user_id)
    return r.get("send_updated_enabled", True)


def set_send_updated_enabled(user_id, status):
    r = get_user_runtime_data(user_id)
    r["send_updated_enabled"] = status
    save_user_runtime_data(user_id, r)


def get_send_new_enabled(user_id):
    r = get_user_runtime_data(user_id)
    return r.get("send_new_enabled", True)


def set_send_new_enabled(user_id, status):
    r = get_user_runtime_data(user_id)
    r["send_new_enabled"] = status
    save_user_runtime_data(user_id, r)


def format_filters(filters_dict):
    if not filters_dict:
        return "No filters set."
    lines = []
    for key, val in filters_dict.items():
        op, value = val
        if key == "size":
            if value >= 1024**3:
                readable = f"{value/(1024**3):.2f}gb"
            elif value >= 1024**2:
                readable = f"{value/(1024**2):.2f}mb"
            elif value >= 1024:
                readable = f"{value/1024:.2f}kb"
            else:
                readable = f"{value}b"
            lines.append(f"{key}: {op}{readable}")
        else:
            lines.append(f"{key}: {op}{value}")
    return "\n".join(lines)


def parse_size(s):
    s = s.lower()
    if s.endswith("kb"):
        val = float(s.replace("kb","")) * 1024
    elif s.endswith("mb"):
        val = float(s.replace("mb","")) * 1024**2
    elif s.endswith("gb"):
        val = float(s.replace("gb","")) * 1024**3
    else:
        val = float(s)
    return int(val)


def parse_filter_command(command_str):
    parts = command_str.split(maxsplit=3)
    if len(parts) < 3:
        return None
    f_name = parts[1].lower().strip()
    f_cond = parts[2].strip()
    if f_cond == "off":
        return (f_name, None)
    if f_cond[0] in ['>', '<']:
        op = f_cond[0]
        val_str = f_cond[1:].strip()
        if f_name == "size":
            if not re.match(r"^\d+(\.\d{1,2})?(kb|mb|gb)?$", val_str, re.IGNORECASE):
                return None
            try:
                value = parse_size(val_str)
            except ValueError:
                return None
        else:
            if not val_str.isdigit():
                return None
            value = int(val_str)
            if value < 0:
                return None
        return (f_name, (op, value))
    return None


def check_filters_updated(user_id, item):
    f_dict = load_user_filters_updated(user_id)
    if not f_dict:
        return True
    fs = int(item.get('file_size', 0))
    sb = int(item.get('subscriptions', 0))
    fv = int(item.get('favorited', 0))
    ls = int(item.get('lifetime_subscriptions', 0))
    lf = int(item.get('lifetime_favorited', 0))
    for f_name, (op, val) in f_dict.items():
        actual = None
        if f_name == 'size':
            actual = fs
        elif f_name == 'subs':
            actual = sb
        elif f_name == 'favs':
            actual = fv
        elif f_name == 'ltsubs':
            actual = ls
        elif f_name == 'ltfavs':
            actual = lf
        if op == '>' and not (actual >= val):
            return False
        if op == '<' and not (actual <= val):
            return False
    return True


def check_filters_new(user_id, item):
    f_dict = load_user_filters_new(user_id)
    if not f_dict:
        return True
    fs = int(item.get('file_size', 0))
    sb = int(item.get('subscriptions', 0))
    fv = int(item.get('favorited', 0))
    ls = int(item.get('lifetime_subscriptions', 0))
    lf = int(item.get('lifetime_favorited', 0))
    for f_name, (op, val) in f_dict.items():
        actual = None
        if f_name == 'size':
            actual = fs
        elif f_name == 'subs':
            actual = sb
        elif f_name == 'favs':
            actual = fv
        elif f_name == 'ltsubs':
            actual = ls
        elif f_name == 'ltfavs':
            actual = lf
        if op == '>' and not (actual >= val):
            return False
        if op == '<' and not (actual <= val):
            return False
    return True


async def delete_last_message(user_id, command, client, chat_id):
    msg_id = get_last_message_id(user_id, command)
    if msg_id:
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=msg_id)
        except:
            pass
        delete_last_message_id(user_id, command)


def extract_game_id(input_str):
    if input_str.isdigit():
        return input_str
    pattern = r"^https?://store\.steampowered\.com/app/(\d+)/"
    match = re.match(pattern, input_str)
    if match:
        return match.group(1)
    return None


async def show_settings_menu(client, user_id, message=None, text_prefix=""):
    steam_games = load_games(user_id)
    game_list = "\n".join([f"[ <code>{gid}</code> ] - {gn}" for gid, gn in steam_games.items()]) or GAME_LIST_EMPTY
    if is_user_monitoring(user_id):
        ftr = "Monitoring is running."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Stop 🔴", callback_data="stop_monitoring")]])
    else:
        if steam_games:
            ftr = "Press Run to start monitoring."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Settings ⚙️", callback_data="open_settings_submenu")],
                [InlineKeyboardButton("🟢 Run", callback_data="run_monitoring")]
            ])
        else:
            ftr = "Add some games to start monitoring."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Settings ⚙️", callback_data="open_settings_submenu")]
            ])
    txt = SET_MENU_TEMPLATE.format(
        game_list_header=GAME_LIST_HEADER,
        game_list=game_list,
        add_game_usage=ADD_GAME_USAGE,
        remove_game_usage=REMOVE_GAME_USAGE,
        footer=ftr
    )
    full = f"{text_prefix}{txt}".strip()
    if message:
        await delete_last_message(user_id, "settings", client, message.chat.id)
        sent = await message.reply(full, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await delete_last_message(user_id, "settings", client, user_id)
        sent = await client.send_message(user_id, full, parse_mode=ParseMode.HTML, reply_markup=kb)
    set_last_message_id(user_id, "settings", sent.id)


def is_valid_game(game_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
        r = requests.get(url)
        if r.status_code == 200:
            d = r.json()
            if d[str(game_id)]["success"]:
                app_data = d[str(game_id)]["data"]
                if app_data["type"] == "game":
                    return True, app_data["name"]
                else:
                    return False, f"Type is {app_data['type']}"
            else:
                return False, "Game ID not found."
        else:
            return False, f"HTTP Error {r.status_code}"
    except:
        return False, "Exception occurred during game validation."


def check_workshop_exists(app_id, api_key):
    u = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
    p = {"key": api_key, "appid": app_id, "query_type": 0, "numperpage": 1}
    try:
        r = requests.get(u, params=p)
        r.raise_for_status()
        d = r.json()
        total_items = d.get("response", {}).get("total", 0)
        return total_items > 0
    except:
        return None


@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.delete()
    user_id = message.from_user.id
    cmds = [
        BotCommand("start", "❗️ M E N U ❗️"),
        BotCommand("help", "📄 D O C S 📄")
    ]
    await client.set_bot_commands(cmds)
    if not user_is_known(user_id):
        await client.send_message(user_id, WELCOME_MESSAGE)
        add_user_to_known(user_id)
    if is_user_monitoring(user_id) and user_id not in running_tasks:
        running_tasks[user_id] = asyncio.create_task(monitor_workshops(client, user_id))
    await show_settings_menu(client, user_id, message)


@app.on_message(filters.private & filters.command("help"))
async def help_command(client, message):
    await message.delete()
    user_id = message.from_user.id
    await client.send_message(user_id, WELCOME_MESSAGE, parse_mode=ParseMode.HTML)


@app.on_callback_query(filters.regex("^run_monitoring$"))
async def run_monitoring_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in running_tasks:
        await callback_query.answer(MONITORING_ALREADY_RUNNING, show_alert=True)
        return
    steam_games = load_games(user_id)
    if not steam_games:
        await callback_query.answer(MONITORING_NO_GAMES, show_alert=True)
        return
    running_tasks[user_id] = asyncio.create_task(monitor_workshops(client, user_id))
    set_monitoring_status(user_id, True)
    await callback_query.answer(MONITORING_STARTED, show_alert=True)
    glist = '\n'.join([f'[ <code>{g}</code> ] - {steam_games[g]}' for g in steam_games]) or GAME_LIST_EMPTY
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Stop 🔴", callback_data="stop_monitoring")]])
    await callback_query.message.edit_text(
        text=f"{GAME_LIST_HEADER}\n{glist}\n\n"
             f"{ADD_GAME_USAGE}\n{REMOVE_GAME_USAGE}\n\n"
             "Monitoring is running.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


@app.on_callback_query(filters.regex("^stop_monitoring$"))
async def stop_monitoring_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in running_tasks:
        set_monitoring_status(user_id, False)
        await callback_query.answer(MONITORING_NOT_RUNNING, show_alert=True)
        return
    running_tasks[user_id].cancel()
    del running_tasks[user_id]
    set_monitoring_status(user_id, False)
    await callback_query.answer(MONITORING_STOPPED, show_alert=True)
    await show_settings_menu(client, user_id, callback_query.message)


@app.on_callback_query(filters.regex("^open_settings_submenu$"))
async def open_settings_submenu_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    set_user_mode(user_id, "settings_submenu_main")
    text = "<b>Settings Menu</b>\n\nChoose which filters you want to configure."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Last Updated 🔄", callback_data="open_settings_submenu_updated")],
        [InlineKeyboardButton("Most Recent 🆕", callback_data="open_settings_submenu_new")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_main_menu")]
    ])
    await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)


@app.on_callback_query(filters.regex("^open_settings_submenu_updated$"))
async def open_settings_submenu_updated(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    set_user_mode(user_id, "settings_submenu_updated")
    filters_upd = load_user_filters_updated(user_id)
    current_filters_text = format_filters(filters_upd)
    updated_enabled = get_send_updated_enabled(user_id)
    status_btn_text = "Last Updated: ON ✅" if updated_enabled else "Last Updated: OFF ❌"
    text = SETTINGS_SUBMENU_TEXT_UPDATED.format(current_filters=current_filters_text)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(status_btn_text, callback_data="toggle_send_updated")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
    ])
    await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)


@app.on_callback_query(filters.regex("^open_settings_submenu_new$"))
async def open_settings_submenu_new(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    set_user_mode(user_id, "settings_submenu_new")
    filters_n = load_user_filters_new(user_id)
    current_filters_text = format_filters(filters_n)
    new_enabled = get_send_new_enabled(user_id)
    status_btn_text = "Most Recent: ON ✅" if new_enabled else "Most Recent: OFF ❌"
    text = SETTINGS_SUBMENU_TEXT_NEW.format(current_filters=current_filters_text)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(status_btn_text, callback_data="toggle_send_new")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
    ])
    await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)


@app.on_callback_query(filters.regex("^toggle_send_updated$"))
async def toggle_send_updated(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    current = get_send_updated_enabled(user_id)
    set_send_updated_enabled(user_id, not current)
    filters_upd = load_user_filters_updated(user_id)
    current_filters_text = format_filters(filters_upd)
    updated_enabled = get_send_updated_enabled(user_id)
    status_btn_text = "Last Updated: ON ✅" if updated_enabled else "Last Updated: OFF ❌"
    text = SETTINGS_SUBMENU_TEXT_UPDATED.format(current_filters=current_filters_text)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(status_btn_text, callback_data="toggle_send_updated")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
    ])
    try:
        await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except MessageNotModified:
        pass
    await callback_query.answer()


@app.on_callback_query(filters.regex("^toggle_send_new$"))
async def toggle_send_new(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    current = get_send_new_enabled(user_id)
    set_send_new_enabled(user_id, not current)
    filters_n = load_user_filters_new(user_id)
    current_filters_text = format_filters(filters_n)
    new_enabled = get_send_new_enabled(user_id)
    status_btn_text = "Most Recent: ON ✅" if new_enabled else "Most Recent: OFF ❌"
    text = SETTINGS_SUBMENU_TEXT_NEW.format(current_filters=current_filters_text)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(status_btn_text, callback_data="toggle_send_new")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
    ])
    try:
        await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except MessageNotModified:
        pass
    await callback_query.answer()


@app.on_callback_query(filters.regex("^back_to_settings_main$"))
async def back_to_settings_main(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    set_user_mode(user_id, "settings_submenu_main")
    text = "<b>Settings Menu</b>\n\nChoose which filters you want to configure."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Last Updated", callback_data="open_settings_submenu_updated")],
        [InlineKeyboardButton("Most Recent", callback_data="open_settings_submenu_new")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_main_menu")]
    ])
    await callback_query.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)


@app.on_callback_query(filters.regex("^back_to_main_menu$"))
async def back_to_main_menu_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    set_user_mode(user_id, None)
    steam_games = load_games(user_id)
    gl = "\n".join([f"[ <code>{gid}</code> ] - {steam_games[gid]}" for gid in steam_games]) or GAME_LIST_EMPTY
    if is_user_monitoring(user_id):
        ftr = "Monitoring is running."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Stop 🔴", callback_data="stop_monitoring")]])
    else:
        if steam_games:
            ftr = "Press Run to start monitoring."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Settings ⚙️", callback_data="open_settings_submenu")],
                [InlineKeyboardButton("🟢 Run", callback_data="run_monitoring")]
            ])
        else:
            ftr = "Add some games to start monitoring."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Settings ⚙️", callback_data="open_settings_submenu")]
            ])
    menu_text = SET_MENU_TEMPLATE.format(
        game_list_header=GAME_LIST_HEADER,
        game_list=gl,
        add_game_usage=ADD_GAME_USAGE,
        remove_game_usage=REMOVE_GAME_USAGE,
        footer=ftr
    )
    await callback_query.message.edit_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=kb)


@app.on_message(filters.private & filters.regex(r"(?i)^add\s+"))
async def add_game(client, message):
    user_id = message.from_user.id
    if is_user_monitoring(user_id):
        await message.delete()
        w = await message.reply(SET_DISABLED_DURING_MONITORING, parse_mode=ParseMode.HTML)
        await show_settings_menu(client, user_id)
        await asyncio.sleep(12)
        await client.delete_messages(chat_id=message.chat.id, message_ids=[w.id])
        return
    await message.delete()
    steam_games = load_games(user_id)
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        resp = INVALID_ADD_FORMAT
    else:
        inp = parts[1]
        gid = extract_game_id(inp)
        if gid:
            ok, nm = is_valid_game(gid)
            if ok:
                if gid not in steam_games:
                    ws = check_workshop_exists(gid, steam_api_key)
                    if ws is True:
                        steam_games[gid] = nm
                        save_games(user_id, steam_games)
                        resp = ADD_GAME_SUCCESS.format(game_id=gid, game_name=nm)
                    elif ws is False:
                        resp = ADD_GAME_NO_WORKSHOP.format(game_id=gid, game_name=nm)
                    else:
                        resp = WORKSHOP_CHECK_FAILED
                else:
                    resp = ADD_GAME_DUPLICATE.format(game_id=gid, game_name=steam_games[gid])
            else:
                resp = ADD_GAME_INVALID.format(game_id=gid, error_message=nm)
        else:
            resp = INVALID_ADD_FORMAT
    await show_settings_menu(client, user_id, message, text_prefix=resp + "\n\n")


@app.on_message(filters.private & filters.regex(r"(?i)^rm\s\d+$"))
async def remove_game(client, message):
    user_id = message.from_user.id
    if is_user_monitoring(user_id):
        await message.delete()
        w = await message.reply(SET_DISABLED_DURING_MONITORING, parse_mode=ParseMode.HTML)
        await show_settings_menu(client, user_id)
        await asyncio.sleep(12)
        await client.delete_messages(chat_id=message.chat.id, message_ids=[w.id])
        return
    await message.delete()
    steam_games = load_games(user_id)
    parts = message.text.strip().split()
    if len(parts) != 2:
        resp = INVALID_REMOVE_FORMAT
    else:
        gid = parts[1]
        if gid in steam_games:
            rmv = steam_games.pop(gid)
            save_games(user_id, steam_games)
            data, user_data = get_user_data(user_id)
            kn = user_data.get("known_items", {})
            if gid in kn:
                del kn[gid]
            lt = user_data.get("last_items", {})
            if gid in lt:
                del lt[gid]
            knn = user_data.get("known_items_new", {})
            if gid in knn:
                del knn[gid]
            ltn = user_data.get("last_items_new", {})
            if gid in ltn:
                del ltn[gid]
            user_data["known_items"] = kn
            user_data["last_items"] = lt
            user_data["known_items_new"] = knn
            user_data["last_items_new"] = ltn
            save_user_data(user_id, user_data)
            resp = REMOVE_GAME_SUCCESS.format(game_id=gid, game_name=rmv)
        else:
            resp = REMOVE_GAME_NOT_FOUND.format(game_id=gid)
    await show_settings_menu(client, user_id, message, text_prefix=resp + "\n\n")


async def monitor_workshops(client, user_id):
    try:
        while True:
            if not is_user_monitoring(user_id):
                break
            steam_games = load_games(user_id)
            for gid, gname in steam_games.items():
                last_upd = get_last_publishedfileid(user_id, gid)
                last_new = get_last_publishedfileid_new(user_id, gid)
                new_updated = await get_new_workshop_items(21, gid, last_upd, "time_updated")
                new_new = await get_new_workshop_items(1, gid, last_new, "time_created")
                if new_updated:
                    set_last_publishedfileid(user_id, gid, new_updated[0]['publishedfileid'])
                if new_new:
                    set_last_publishedfileid_new(user_id, gid, new_new[0]['publishedfileid'])
                known_items = load_game_items_info(user_id, gid)
                known_items_new = load_game_items_info_new(user_id, gid)
                first_updated = (last_upd is None)
                first_new = (last_new is None)
                if get_send_updated_enabled(user_id):
                    for it in new_updated:
                        await process_and_send_item(known_items, user_id, gid, gname, it, client, not first_updated, "updated")
                    save_game_items_info(user_id, gid, known_items)
                if get_send_new_enabled(user_id):
                    for it in new_new:
                        await process_and_send_item_new(known_items_new, user_id, gid, gname, it, client, not first_new, "new")
                    save_game_items_info_new(user_id, gid, known_items_new)
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print("monitor_workshops error:", e)
    finally:
        set_monitoring_status(user_id, False)
        if user_id in running_tasks:
            del running_tasks[user_id]


async def get_new_workshop_items(q_type, game_id, last_publishedfileid, sort_key):
    prms = {
        'key': steam_api_key,
        'appid': game_id,
        'query_type': q_type,
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
        r = requests.get(url, params=prms)
        r.raise_for_status()
        data = r.json()
        items = data.get('response', {}).get('publishedfiledetails', [])
        if not items:
            return []
        items.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
        if not last_publishedfileid:
            return items
        new_items = []
        for i in items:
            if i['publishedfileid'] == last_publishedfileid:
                break
            new_items.append(i)
        return new_items
    except:
        return []


async def process_and_send_item(known_items, user_id, gid, gname, item, client, send_if_ok, t):
    pfid = item.get('publishedfileid')
    tu = int(item.get('time_updated', 0))
    old = known_items.get(pfid, 0)
    if tu > old:
        known_items[pfid] = tu
        while len(known_items) > 100:
            oldest = min(known_items, key=known_items.get)
            if oldest != pfid:
                del known_items[oldest]
            else:
                break
        if send_if_ok and check_filters_updated(user_id, item):
            await send_workshop_item(client, user_id, gname, item, t)


async def process_and_send_item_new(known_items_new, user_id, gid, gname, item, client, send_if_ok, t):
    pfid = item.get('publishedfileid')
    tc = int(item.get('time_created', 0))
    old = known_items_new.get(pfid, 0)
    if tc > old:
        known_items_new[pfid] = tc
        while len(known_items_new) > 100:
            oldest = min(known_items_new, key=known_items_new.get)
            if oldest != pfid:
                del known_items_new[oldest]
            else:
                break
        if send_if_ok and check_filters_new(user_id, item):
            await send_workshop_item(client, user_id, gname, item, t)


async def send_workshop_item(client, user_id, gname, item, t):
    itype = " (updated)" if (t == "updated") else " (new)"
    ttl = item.get('title', 'No Title')
    fsb = int(item.get('file_size', 0))
    fs = "N/A"
    if fsb > 0:
        if fsb >= 1073741824:
            fs = f"{fsb / 1073741824:.2f} GB"
        elif fsb >= 1048576:
            fs = f"{fsb / 1048576:.2f} MB"
        else:
            fs = f"{fsb / 1024:.2f} KB"
    sb = item.get('subscriptions', 0)
    fv = item.get('favorited', 0)
    ls = item.get('lifetime_subscriptions', 0)
    lf = item.get('lifetime_favorited', 0)
    tags = ', '.join([tg.get('tag', '') for tg in item.get('tags', [])]) if item.get('tags') else 'N/A'
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item.get('publishedfileid', 'N/A')}"
    msg = WORKSHOP_ITEM_MESSAGE.format(
        game_name=gname,
        title=ttl,
        file_size=fs,
        subscriptions=sb,
        favorited=fv,
        lifetime_subscriptions=ls,
        lifetime_favorited=lf,
        tags=tags,
        item_url=url,
        item_type=itype
    )
    await client.send_message(user_id, msg, parse_mode=ParseMode.HTML)


@app.on_message(filters.private & filters.incoming & ~filters.command("start") & ~filters.command("help"))
async def handle_incoming_private(client, message):
    user_id = message.from_user.id
    txt = message.text.strip().lower()
    mode = get_user_mode(user_id)
    if mode == "settings_submenu_updated":
        if txt == "reset":
            save_user_filters_updated(user_id, {})
            data, user_data = get_user_data(user_id)
            user_data["known_items"] = {}
            user_data["last_items"] = {}
            save_user_data(user_id, user_data)
            f = load_user_filters_updated(user_id)
            ft = format_filters(f)
            show_txt = SETTINGS_SUBMENU_TEXT_UPDATED.format(current_filters=ft)
            await message.delete()
            try:
                await client.edit_message_text(
                    user_id,
                    get_last_message_id(user_id, "settings"),
                    show_txt,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Last Updated: ON ✅" if get_send_updated_enabled(user_id) else "Last Updated: OFF ❌",
                                              callback_data="toggle_send_updated")],
                        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
                    ])
                )
            except MessageNotModified:
                pass
            return
        if txt.startswith("set "):
            parsed = parse_filter_command(txt)
            await message.delete()
            if parsed is None:
                return
            n, d = parsed
            vf = ["size", "subs", "favs", "ltsubs", "ltfavs"]
            if n not in vf:
                return
            set_user_filter_updated(user_id, n, d)
            f = load_user_filters_updated(user_id)
            ft = format_filters(f)
            show_txt = SETTINGS_SUBMENU_TEXT_UPDATED.format(current_filters=ft)
            try:
                await client.edit_message_text(
                    user_id,
                    get_last_message_id(user_id, "settings"),
                    show_txt,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Last Updated: ON ✅" if get_send_updated_enabled(user_id) else "Last Updated: OFF ❌",
                                              callback_data="toggle_send_updated")],
                        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
                    ])
                )
            except MessageNotModified:
                pass
            return
    if mode == "settings_submenu_new":
        if txt == "reset":
            save_user_filters_new(user_id, {})
            data, user_data = get_user_data(user_id)
            user_data["known_items_new"] = {}
            user_data["last_items_new"] = {}
            save_user_data(user_id, user_data)
            f = load_user_filters_new(user_id)
            ft = format_filters(f)
            show_txt = SETTINGS_SUBMENU_TEXT_NEW.format(current_filters=ft)
            await message.delete()
            try:
                await client.edit_message_text(
                    user_id,
                    get_last_message_id(user_id, "settings"),
                    show_txt,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Most Recent: ON ✅" if get_send_new_enabled(user_id) else "Most Recent: OFF ❌",
                                              callback_data="toggle_send_new")],
                        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
                    ])
                )
            except MessageNotModified:
                pass
            return
        if txt.startswith("set "):
            parsed = parse_filter_command(txt)
            await message.delete()
            if parsed is None:
                return
            n, d = parsed
            vf = ["size", "subs", "favs", "ltsubs", "ltfavs"]
            if n not in vf:
                return
            set_user_filter_new(user_id, n, d)
            f = load_user_filters_new(user_id)
            ft = format_filters(f)
            show_txt = SETTINGS_SUBMENU_TEXT_NEW.format(current_filters=ft)
            try:
                await client.edit_message_text(
                    user_id,
                    get_last_message_id(user_id, "settings"),
                    show_txt,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Most Recent: ON ✅" if get_send_new_enabled(user_id) else "Most Recent: OFF ❌",
                                              callback_data="toggle_send_new")],
                        [InlineKeyboardButton("◀️ Back", callback_data="back_to_settings_main")]
                    ])
                )
            except MessageNotModified:
                pass
            return
    await message.delete()


if __name__ == "__main__":
    app.run()
