import os
import re
import asyncio
import aiohttp

from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


# =====================================
# CONFIG
# =====================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

PAGE_SIZE = 10

PLAYLISTS = {
    "world": {
        "name": "🌍 All World Channels",
        "url": "https://iptv-org.github.io/iptv/index.m3u"
    },
    "india": {
        "name": "🇮🇳 India FTA",
        "url": "https://iptv-org.github.io/iptv/countries/in.m3u"
    },
    "hindi": {
        "name": "🔤 Hindi Channels",
        "url": "https://iptv-org.github.io/iptv/languages/hin.m3u"
    },
    "news": {
        "name": "📰 World News",
        "url": "https://iptv-org.github.io/iptv/categories/news.m3u"
    },
    "sports": {
        "name": "🏆 World Sports",
        "url": "https://iptv-org.github.io/iptv/categories/sports.m3u"
    }
}


# =====================================
# CLIENTS
# =====================================

bot = Client(
    "ANSH_LIVE_BOT",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = Client(
    "ANSH_LIVE_USER",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

calls = PyTgCalls(user)


# =====================================
# DATA CACHE
# =====================================

cache = {}
active_tasks = {}


# =====================================
# FETCH M3U
# =====================================

async def fetch_playlist(key):

    if key in cache:
        return cache[key]

    url = PLAYLISTS[key]["url"]

    headers = {
        "User-Agent": "ANSH-LIVE-TV/1.0"
    }

    timeout = aiohttp.ClientTimeout(total=60)

    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(url) as response:

                response.raise_for_status()
                content = await response.text()

        channels = []
        name = None

        for line in content.splitlines():

            line = line.strip()

            if line.startswith("#EXTINF"):

                match = re.search(r",(.+)$", line)
                name = match.group(1).strip() if match else "Unknown"

            elif line.startswith(("http://", "https://")):

                if name:

                    channels.append({
                        "name": name,
                        "url": line
                    })

                name = None

        cache[key] = channels

        return channels

    except Exception as error:

        print("PLAYLIST ERROR:", repr(error))
        return None


# =====================================
# MAIN MENU
# =====================================

def main_keyboard():

    buttons = []

    for key, item in PLAYLISTS.items():

        buttons.append([
            InlineKeyboardButton(
                item["name"],
                callback_data=f"cat_{key}_0"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "ℹ️ HELP",
            callback_data="help"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =====================================
# SHOW CHANNELS
# =====================================

async def show_channels(message, key, page=0):

    if key not in PLAYLISTS:
        return

    channels = await fetch_playlist(key)

    if channels is None:

        await message.reply_text(
            "❌ Playlist load nahi hui. Thodi der baad try karo."
        )
        return

    if not channels:

        await message.reply_text(
            "❌ Is category mein channels nahi mile."
        )
        return

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    selected = channels[start:end]

    buttons = []

    for index, channel in enumerate(selected, start=start):

        buttons.append([
            InlineKeyboardButton(
                f"📺 {channel['name'][:45]}",
                callback_data=f"play_{key}_{index}"
            )
        ])

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"cat_{key}_{page-1}"
            )
        )

    if end < len(channels):

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"cat_{key}_{page+1}"
            )
        )

    if navigation:
        buttons.append(navigation)

    buttons.append([
        InlineKeyboardButton(
            "🏠 HOME",
            callback_data="home"
        )
    ])

    await message.reply_text(
        f"📡 {PLAYLISTS[key]['name']}\n\n"
        f"Total channels: {len(channels)}\n"
        f"Page: {page+1}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =====================================
# START
# =====================================

@bot.on_message(filters.command("start"))
async def start_command(client, message):

    await message.reply_text(
        "📺 ANSH LIVE TV\n\n"
        "Welcome!\n"
        "Select your channel category:",
        reply_markup=main_keyboard()
    )


# =====================================
# CHANNELS
# =====================================

@bot.on_message(filters.command("channels"))
async def channels_command(client, message):

    await message.reply_text(
        "📡 SELECT CATEGORY:",
        reply_markup=main_keyboard()
    )


# =====================================
# PLAY
# =====================================

async def play_channel(chat_id, channel):

    url = channel["url"]

    # Only HTTP(S) links are accepted.
    if not url.startswith(("https://", "http://")):
        await bot.send_message(chat_id, "❌ Invalid stream URL.")
        return

    # Do not rebroadcast protected SonyLIV CDN streams.
    if "slivcdn.com" in url.lower():
        await bot.send_message(
            chat_id,
            "❌ Protected stream not supported."
        )
        return

    try:

        await calls.play(
            chat_id,
            MediaStream(url)
        )

        await bot.send_message(
            chat_id,
            f"▶️ NOW PLAYING\n\n"
            f"📺 {channel['name']}"
        )

    except Exception as error:

        print("STREAM ERROR:", repr(error))

        await bot.send_message(
            chat_id,
            "❌ STREAM ERROR\n\n"
            + str(error)[:300]
        )


# =====================================
# CALLBACKS
# =====================================

@bot.on_callback_query()
async def callback_handler(client, query):

    data = query.data

    if data == "home":

        await query.answer()

        await query.message.reply_text(
            "🏠 MAIN MENU",
            reply_markup=main_keyboard()
        )

    elif data == "help":

        await query.answer()

        await query.message.reply_text(
            "/start - Start bot\n"
            "/channels - Categories\n"
            "/play CHANNEL NAME - Search channel\n"
            "/stop - Stop stream"
        )

    elif data.startswith("cat_"):

        await query.answer("Loading...")

        try:

            _, key, page = data.split("_")

            await show_channels(
                query.message,
                key,
                int(page)
            )

        except Exception as error:

            print("CATEGORY ERROR:", repr(error))

    elif data.startswith("play_"):

        await query.answer("Starting...")

        try:

            _, key, index = data.split("_")

            channels = await fetch_playlist(key)

            index = int(index)

            if not channels or index >= len(channels):
                raise IndexError

            await play_channel(
                query.message.chat.id,
                channels[index]
            )

        except Exception as error:

            print("BUTTON ERROR:", repr(error))

            await query.message.reply_text(
                "❌ Channel load nahi hua."
            )


# =====================================
# SEARCH COMMAND
# =====================================

@bot.on_message(filters.command("play"))
async def search_command(client, message):

    if len(message.command) < 2:

        await message.reply_text(
            "Usage:\n/play channel name"
        )
        return

    search = " ".join(
        message.command[1:]
    ).lower()

    await message.reply_text(
        "🔎 Searching channels..."
    )

    for key in PLAYLISTS:

        channels = await fetch_playlist(key)

        if not channels:
            continue

        for channel in channels:

            if search in channel["name"].lower():

                await play_channel(
                    message.chat.id,
                    channel
                )
                return

    await message.reply_text(
        "❌ Channel not found!"
    )


# =====================================
# STOP
# =====================================

@bot.on_message(filters.command("stop"))
async def stop_command(client, message):

    try:

        await calls.leave_call(
            message.chat.id
        )

        await message.reply_text(
            "⏹️ STREAM STOPPED!"
        )

    except Exception as error:

        print("STOP ERROR:", repr(error))

        await message.reply_text(
            "❌ No active stream found."
        )


# =====================================
# MAIN
# =====================================

async def main():

    print("Starting ANSH LIVE TV...")

    try:

        await user.start()
        print("USER CONNECTED")

        await calls.start()
        print("PYTGCALLS STARTED")

        await bot.start()
        print("BOT ONLINE")

        await idle()

    finally:

        if bot.is_connected:
            await bot.stop()

        await calls.stop()

        if user.is_connected:
            await user.stop()


if __name__ == "__main__":

    asyncio.run(main())
