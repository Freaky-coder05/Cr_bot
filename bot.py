from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton,CallbackQuery
import json, os
import asyncio
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

from pyrogram.errors import FloodWait
     # Your Telegram user ID (for indexing command)

import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyromod import listen  # Enables .ask()
from pyrogram.errors import FloodWait

API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DATABASE_CHANNEL = -1002134913785  # your database channel ID

ADMINS = [6299192020]
# ─────────────────────────────
# BOT INITIALIZATION
# ─────────────────────────────
app = Client("searchbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
lock = asyncio.Lock()


# ─────────────────────────────
# INDEX FILES (ADMIN ONLY)
# ─────────────────────────────
@app.on_message(filters.command(['index', 'indexfiles']) & filters.user(ADMINS))
async def index_files(bot, message):
    """Save files from a channel into the bot’s cache (no DB, just memory)."""
    if lock.locked():
        return await message.reply('Wait until the previous process completes.')

    await message.reply_text(
        "📨 Forward me the **last message** of a channel that I should index.\n\n"
        "Make sure the bot is **admin** there and forward *with quotes*, not as a copy."
    )

    try:
        last_msg = await bot.ask(
            chat_id=message.from_user.id,
            text="Now forward the last post from the channel."
        )
    except Exception:
        return await message.reply("⏰ Timeout. Please try /index again.")

    try:
        chat_id = (
            last_msg.forward_from_chat.username
            if last_msg.forward_from_chat.username
            else last_msg.forward_from_chat.id
        )
        last_msg_id = last_msg.forward_from_message_id
        await bot.get_messages(chat_id, last_msg_id)
    except Exception as e:
        return await last_msg.reply_text(
            f"This is an invalid message.\n\nError: `{e}`"
        )

    msg = await message.reply('Processing...⏳')
    total_files = 0

    async with lock:
        current = 1
        while current <= last_msg_id:
            try:
                m = await bot.get_messages(chat_id, current)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except Exception:
                current += 1
                continue

            if m and (m.document or m.video or m.audio):
                total_files += 1

            if current % 20 == 0:
                await msg.edit(f"📦 Indexed {current}/{last_msg_id} messages...")
            current += 1

        await msg.edit(f"✅ Indexed {total_files} files from channel!")


# ─────────────────────────────
# SEARCH COMMAND
# ─────────────────────────────
@app.on_message(filters.command("search"))
async def search_files(bot, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/search Naruto`", quote=True)

    query = " ".join(message.command[1:]).lower()
    results = []
    async for msg in bot.search_messages(
        chat_id=DATABASE_CHANNEL,
        query=query,
        filter=enums.MessagesFilter.VIDEO
    ):
        title = msg.caption or "No Title"
        results.append((title[:40], msg.id))

    if not results:
        return await message.reply("❌ No results found.", quote=True)

    buttons = [
        [InlineKeyboardButton(text=title, callback_data=f"get_{msg_id}_{message.from_user.id}")]
        for title, msg_id in results[:10]
    ]

    await message.reply(
        f"🔍 Results for **{query}**:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file(bot, query: CallbackQuery):
    _, msg_id, user_id = query.data.split("_")

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search result. Please use /search.", show_alert=True)

    try:
        msg = await bot.get_messages(DATABASE_CHANNEL, int(msg_id))
        await msg.copy(query.from_user.id)
        await query.answer("📤 Sent to your DM!", show_alert=False)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ─────────────────────────────
# START BOT
# ─────────────────────────────
print("🤖 Bot started...")
app.run()
