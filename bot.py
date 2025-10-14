from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton,CallbackQuery
import json, os
import asyncio
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DB_CHANNEL = -1002134913785  # your database channel ID

OWNER_ID = 6299192020         # Your Telegram user ID (for indexing command)
# -----------------------------------------

app = Client("FileSearchBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
DB_FILE = "files.json"

# Load existing data
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        file_data = json.load(f)
else:
    file_data = {}

# ----------- INDEX COMMAND --------------
@app.on_message(filters.command("index") & filters.user(OWNER_ID))
async def index_files(_, msg):
    await msg.reply_text("📦 Indexing files from channel, please wait...")

    all_files = {}
    async for m in app.get_chat_history(DB_CHANNEL):
        if m.document:
            all_files[m.document.file_name.lower()] = {
                "file_name": m.document.file_name,
                "message_id": m.id,
                "file_size": m.document.file_size
            }

    with open(DB_FILE, "w") as f:
        json.dump(all_files, f, indent=2)

    global file_data
    file_data = all_files

    await msg.reply_text(f"✅ Indexed {len(all_files)} files from channel.")

# ----------- SEARCH COMMAND --------------
@app.on_message(filters.command("search"))
async def search_files(_, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: `/search Naruto`", quote=True)

    query = msg.text.split(" ", 1)[1].lower()
    results = [v for k, v in file_data.items() if query in k]

    if not results:
        return await msg.reply_text("❌ No results found.")

    buttons = []
    for i, file in enumerate(results[:10]):
        buttons.append([InlineKeyboardButton(
            f"{file['file_name']}", callback_data=f"{msg.from_user.id}:{file['message_id']}")])

    await msg.reply_text(
        f"🔍 **Results for:** {query}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------- CALLBACK HANDLER --------------
@app.on_callback_query()
async def cb_handler(_, query: CallbackQuery):
    try:
        user_id, msg_id = query.data.split(":")
        msg_id = int(msg_id)

        if str(query.from_user.id) != user_id:
            return await query.answer("❌ Not your query! Use /search.", show_alert=True)

        await query.answer()
        await app.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DB_CHANNEL,
            message_id=msg_id
        )

    except Exception as e:
        await query.message.reply_text(f"Error: {e}")

# ----------- START COMMAND --------------
@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text("🤖 File Search Bot Ready!\nUse /search <query> to find files.")

print("✅ File Search Bot Started...")
app.run()
