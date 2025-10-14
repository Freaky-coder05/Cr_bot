from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton,CallbackQuery
import json, os
import asyncio
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

from pyrogram.errors import FloodWait



API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DB_CHANNEL = -1002134913785  # your database channel ID

ADMINS = [6299192020]     # Your Telegram user ID (for indexing command)
# -----------------------------------------


# ------------- CONFIG -------------

DB_FILE = "files.json"
# ----------------------------------

app = Client("FileSearchBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

lock = asyncio.Lock()
file_data = {}

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        file_data = json.load(f)

# ----------- INDEX FILES -----------
@app.on_message(filters.command(["index", "indexfiles"]) & filters.user(ADMINS))
async def index_files(bot, message):
    """Index files from a Telegram channel (bot must be admin there)"""
    if lock.locked():
        return await message.reply("⚠️ Wait until previous process completes.")

    while True:
        last_msg = await bot.ask(
            text=(
                "📨 Forward me **the last message** of the channel to index.\n\n"
                "Make sure the bot is **admin** in that channel.\n"
                "Forward with quotes (not as copy)."
            ),
            chat_id=message.from_user.id,
        )
        try:
            last_msg_id = last_msg.forward_from_message_id
            chat = last_msg.forward_from_chat
            chat_id = chat.username or chat.id
            await bot.get_messages(chat_id, last_msg_id)
            break
        except Exception as e:
            await last_msg.reply_text(f"❌ Invalid message: {e}")
            continue

    msg = await message.reply("⏳ Indexing started...")
    total_files = 0
    async with lock:
        try:
            total = last_msg_id + 1
            current = 1
            progress = 0
            while current < total:
                try:
                    m = await bot.get_messages(chat_id, current)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    continue
                except Exception:
                    current += 1
                    continue

                for ftype in ("document", "video", "audio"):
                    media = getattr(m, ftype, None)
                    if media:
                        file_name = media.file_name or "NoName"
                        file_data[file_name.lower()] = {
                            "file_name": file_name,
                            "message_id": m.id,
                            "chat_id": chat_id,
                        }
                        total_files += 1
                        break

                current += 1
                progress += 1
                if progress >= 20:
                    await msg.edit(f"📤 Indexed: {current}/{total} | Saved: {total_files}")
                    progress = 0

        except Exception as e:
            await msg.edit(f"⚠️ Error: {e}")
        else:
            with open(DB_FILE, "w") as f:
                json.dump(file_data, f, indent=2)
            await msg.edit(f"✅ Done! {total_files} files saved locally.")

# ----------- SEARCH COMMAND -----------
@app.on_message(filters.command("search"))
async def search_files(bot, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: `/search keyword`", quote=True)

    query = msg.text.split(" ", 1)[1].lower()
    results = [v for k, v in file_data.items() if query in k]

    if not results:
        return await msg.reply_text("❌ No files found.")

    buttons = [
        [InlineKeyboardButton(f"{v['file_name']}", callback_data=f"{msg.from_user.id}:{v['chat_id']}:{v['message_id']}")]
        for v in results[:10]
    ]

    await msg.reply_text(f"🔍 Results for: **{query}**", reply_markup=InlineKeyboardMarkup(buttons))

# ----------- BUTTON HANDLER -----------
@app.on_callback_query()
async def cb_handler(bot, query):
    try:
        user_id, chat_id, msg_id = query.data.split(":")
        msg_id = int(msg_id)

        if str(query.from_user.id) != user_id:
            return await query.answer("❌ Not your query! Use /search.", show_alert=True)

        await query.answer()
        await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=chat_id,
            message_id=msg_id
        )

    except Exception as e:
        await query.message.reply_text(f"Error: {e}")

# ----------- START -----------
@app.on_message(filters.command("start"))
async def start(_, m):
    await m.reply_text("🤖 File Search Bot Ready!\nUse /search <keyword> to find files.")

print("✅ File Search Bot Started...")
app.run()
