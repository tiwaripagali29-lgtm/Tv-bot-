import os
import re
import asyncio
from urllib.parse import urlparse

from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


# ==================================
# CONFIG
# ==================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

M3U_FILE = "channels.m3u"


# ==================================
# CLIENTS
# ==================================

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


# ==================================
# M3U LOADER
# ==================================

def load_channels():

    channels = []
    name = None

    if not os.path.exists(M3U_FILE):
        return channels

    with open(M3U_FILE, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if line.startswith("#EXTINF"):

                match = re.search(r",(.+)$", line)
                name = match.group(1).strip() if match else None

            elif line.startswith(("http://", "https://")):

                if name:
                    channels.append({
                        "name": name,
                        "url": line
                    })

                name = None

    return channels


# ==================================
# STREAM VALIDATION
# ==================================

def valid_stream(url):

    try:
        host = urlparse(url).hostname or ""

        # Protected SonyLIV CDN streams are not supported.
        if host.endswith("slivcdn.com"):
            return False

        return url.startswith(("http://", "https://"))

    except Exception:
        return False


# ==================================
# START
# ==================================

@bot.on_message(filters.command("start"))
async def start_command(client, message):

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📺 ALL CHANNELS",
                callback_data="channels"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ HELP",
                callback_data="help"
            )
        ]
    ])

    await message.reply_text(
        "📺 ANSH LIVE TV\n\n"
        "Welcome to Live TV Bot!\n\n"
        "Select your option:",
        reply_markup=keyboard
    )


# ==================================
# CHANNEL LIST
# ==================================

async def send_channels(message):

    channels = load_channels()

    if not channels:
        await message.reply_text(
            "❌ No channels found in channels.m3u"
        )
        return

    buttons = []

    for index, channel in enumerate(channels):

        buttons.append([
            InlineKeyboardButton(
                f"📺 {channel['name'][:50]}",
                callback_data=f"play_{index}"
            )
        ])

    await message.reply_text(
        "📡 AVAILABLE CHANNELS",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@bot.on_message(filters.command("channels"))
async def channels_command(client, message):
    await send_channels(message)


# ==================================
# PLAY CHANNEL
# ==================================

async def play_channel(chat_id, channel):

    url = channel["url"]

    if not valid_stream(url):
        await bot.send_message(
            chat_id,
            "❌ This stream is not supported. "
            "Use an authorized public stream."
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
            + str(error)[:400]
        )


# ==================================
# CALLBACK BUTTONS
# ==================================

@bot.on_callback_query()
async def callback_handler(client, query):

    data = query.data

    if data == "channels":

        await query.answer()
        await send_channels(query.message)

    elif data == "help":

        await query.answer()

        await query.message.reply_text(
            "/start - Start bot\n"
            "/channels - All channels\n"
            "/play CHANNEL NAME - Play channel\n"
            "/stop - Stop stream"
        )

    elif data.startswith("play_"):

        await query.answer("Starting stream...")

        try:

            index = int(data.replace("play_", ""))

            channels = load_channels()

            if index < 0 or index >= len(channels):
                raise IndexError

            channel = channels[index]

            await play_channel(
                query.message.chat.id,
                channel
            )

        except (ValueError, IndexError):

            await query.message.reply_text(
                "❌ Channel not found!"
            )


# ==================================
# PLAY COMMAND
# ==================================

@bot.on_message(filters.command("play"))
async def play_command(client, message):

    if len(message.command) < 2:

        await message.reply_text(
            "Usage:\n/play DD National"
        )
        return

    search = " ".join(
        message.command[1:]
    ).lower()

    channels = load_channels()

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


# ==================================
# STOP COMMAND
# ==================================

@bot.on_message(filters.command("stop"))
async def stop_command(client, message):

    try:

        await calls.leave_call(message.chat.id)

        await message.reply_text(
            "⏹️ STREAM STOPPED!"
        )

    except Exception as error:

        print("STOP ERROR:", repr(error))

        await message.reply_text(
            "❌ No active stream or call found."
        )


# ==================================
# MAIN
# ==================================

async def main():

    print("Starting ANSH LIVE TV...")

    try:

        await user.start()
        print("User session connected!")

        await calls.start()
        print("PyTgCalls started!")

        await bot.start()
        print("ANSH LIVE TV BOT ONLINE!")

        await idle()

    finally:

        if bot.is_connected:
            await bot.stop()

        await calls.stop()

        if user.is_connected:
            await user.stop()


if __name__ == "__main__":
    asyncio.run(main())
