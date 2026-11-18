import os
import re
import asyncio

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram import idle
from pytgcalls import PyTgCalls

# =========================
# CONFIGURATION
# =========================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]

M3U_FILE = "channels.m3u"

# =========================
# TELEGRAM CLIENTS
# =========================

bot = Client(
    "ansh_live_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = Client(
    "ansh_stream_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

calls = PyTgCalls(user)

# =========================
# M3U READER
# =========================

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

                if match:
                    name = match.group(1).strip()

            elif line.startswith("http") and name:

                channels.append({
                    "name": name,
                    "url": line
                })

                name = None

    return channels


# =========================
# START COMMAND
# =========================

@bot.on_message(filters.command("start"))
async def start(client, message):

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
        "📺 ANSH LIVE TV BOT\n\n"
        "Welcome!\n"
        "Watch authorized live streams.\n\n"
        "Select an option below.",
        reply_markup=keyboard
    )


# =========================
# CHANNEL LIST
# =========================

async def show_channels(message):

    channels = load_channels()

    if not channels:
        await message.reply_text(
            "❌ No authorized M3U channels found!"
        )
        return

    buttons = []

    for i, channel in enumerate(channels):

        buttons.append([
            InlineKeyboardButton(
                f"📺 {channel['name']}",
                callback_data=f"play:{i}"
            )
        ])

    await message.reply_text(
        "📡 AVAILABLE CHANNELS",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@bot.on_message(filters.command("channels"))
async def channels_command(client, message):
    await show_channels(message)


# =========================
# BUTTON HANDLER
# =========================

@bot.on_callback_query()
async def button_handler(client, query):

    if query.data == "channels":

        await show_channels(query.message)

    elif query.data == "help":

        await query.message.reply_text(
            "/start - Start bot\n"
            "/channels - Channel list\n"
            "/play CHANNEL NAME - Play channel\n"
            "/stop - Stop streaming"
        )

    elif query.data.startswith("play:"):

        index = int(query.data.split(":")[1])

        channels_list = load_channels()

        if index >= len(channels_list):
            await query.answer("Channel not found!", show_alert=True)
            return

        channel = channels_list[index]

        await play_channel(
            query.message.chat.id,
            channel
        )

        await query.answer("Channel selected!")


# =========================
# PLAY FUNCTION
# =========================

async def play_channel(chat_id, channel):

    try:

        await calls.play(
            chat_id,
            channel["url"]
        )

        await bot.send_message(
            chat_id,
            f"▶️ NOW PLAYING\n\n"
            f"📺 {channel['name']}"
        )

    except Exception as error:

        await bot.send_message(
            chat_id,
            f"❌ Stream error:\n{str(error)[:300]}"
        )


# =========================
# PLAY COMMAND
# =========================

@bot.on_message(filters.command("play"))
async def play_command(client, message):

    if len(message.command) < 2:

        await message.reply_text(
            "Usage:\n/play Sony SAB HD"
        )
        return

    search_name = " ".join(message.command[1:]).lower()

    channels_list = load_channels()

    for channel in channels_list:

        if search_name in channel["name"].lower():

            await play_channel(
                message.chat.id,
                channel
            )

            return

    await message.reply_text(
        "❌ Channel not found!"
    )


# =========================
# STOP COMMAND
# =========================

@bot.on_message(filters.command("stop"))
async def stop_command(client, message):

    try:

        await calls.leave_call(message.chat.id)

        await message.reply_text(
            "⏹️ LIVE STREAM STOPPED!"
        )

    except Exception:

        await message.reply_text(
            "❌ No active stream found."
        )


# =========================
# RUN BOT
# =========================

async def main():

    print("Starting ANSH LIVE TV...")

    await user.start()
    await calls.start()
    await bot.start()

    print("ANSH LIVE TV BOT STARTED!")

    await idle()

    await bot.stop()
    await calls.stop()
    await user.stop()


if __name__ == "__main__":
    asyncio.run(main())
