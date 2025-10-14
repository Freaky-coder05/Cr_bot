import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyromod import listen
from pyrogram.errors import FloodWait
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DATABASE_CHANNEL = -1003094784222  # your database channel ID

ADMINS = [6299192020]

INDEX_FILE = "index.json"

app = Client("searchbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
lock = asyncio.Lock()

# Load index from file
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r") as f:
        FILE_INDEX = json.load(f)
else:
    FILE_INDEX = []


# ───────────────────────────────────────
# INDEX FILES
# ───────────────────────────────────────
@app.on_message(filters.command(['index']) & filters.user(ADMINS))
async def index_files(bot, message):
    """Index all media from a channel and store titles in a local JSON."""
    if lock.locked():
        return await message.reply("Please wait, another indexing is in progress.")

    await message.reply("Forward the **last message** of the channel (with quote).")

    last_msg = await bot.ask(message.chat.id, "📩 Now forward the last message from the channel.")
    try:
        chat_id = (
            last_msg.forward_from_chat.username
            if last_msg.forward_from_chat.username
            else last_msg.forward_from_chat.id
        )
        last_msg_id = last_msg.forward_from_message_id
    except Exception as e:
        return await last_msg.reply(f"Invalid message: {e}")

    msg = await message.reply("Indexing started...")

    total_files = 0
    new_index = []

    async with lock:
        for i in range(1, last_msg_id + 1):
            try:
                m = await bot.get_messages(chat_id, i)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except Exception:
                continue

            if not (m.document or m.video or m.audio):
                continue

            caption = m.caption or "No Title"
            new_index.append({"title": caption, "id": m.id})
            total_files += 1

            if total_files % 20 == 0:
                await msg.edit(f"Indexed {total_files} files...")

    FILE_INDEX.clear()
    FILE_INDEX.extend(new_index)

    with open(INDEX_FILE, "w") as f:
        json.dump(FILE_INDEX, f, indent=2)

    await msg.edit(f"✅ Indexed {total_files} files!")


# ───────────────────────────────────────
# SEARCH COMMAND
# ───────────────────────────────────────
@app.on_message(filters.command("search"))
async def search_files(bot, message):
    if len(message.command) < 2:
        return await message.reply("Usage: /search Naruto")

    query = " ".join(message.command[1:]).lower()

    results = [
        f for f in FILE_INDEX if query in f["title"].lower()
    ][:10]  # Limit to top 10 results

    if not results:
        return await message.reply("❌ No results found.")

    buttons = [
        [InlineKeyboardButton(text=f["title"][:40], callback_data=f"get_{f['id']}_{message.from_user.id}")]
        for f in results
    ]

    await message.reply(
        f"🔍 Results for **{query}**:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ───────────────────────────────────────
# CALLBACK HANDLER
# ───────────────────────────────────────
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file(bot, query: CallbackQuery):
    _, msg_id, user_id = query.data.split("_")

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search result. Use /search yourself.", show_alert=True)

    try:
        await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DATABASE_CHANNEL,
            message_id=int(msg_id)
        )
        await query.answer("📤 Sent to your DM!", show_alert=False)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


print("🤖 Bot is running...")
app.run()
