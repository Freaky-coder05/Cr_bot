import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyromod import listen
from pyrogram.errors import FloodWait, Forbidden
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DATABASE_CHANNEL = -1003094784222  # your database channel ID

ADMINS = [6299192020]


INDEX_FILE = "index.json"
BOT_USERNAME = "Ghjjjoooo_bot"  # without @




# ───────────── INIT ─────────────
app = Client("searchbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
lock = asyncio.Lock()

# Load cache
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r") as f:
        FILE_INDEX = json.load(f)
else:
    FILE_INDEX = []


# ───────────── INDEX COMMAND ─────────────
@app.on_message(filters.command(['index']) & filters.user(ADMINS))
async def index_files(bot, message):
    if lock.locked():
        return await message.reply("⏳ Another indexing is in progress. Please wait.")

    await message.reply("📩 Forward the **last message** of your channel (with quotes).")

    last_msg = await bot.ask(message.chat.id, "Now forward the last message from the channel (not as copy).")
    try:
        chat_id = (
            last_msg.forward_from_chat.username
            if last_msg.forward_from_chat.username
            else last_msg.forward_from_chat.id
        )
        last_msg_id = last_msg.forward_from_message_id
    except Exception as e:
        return await last_msg.reply(f"❌ Invalid message: {e}")

    msg = await message.reply("📦 Indexing started...")
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

            media = m.document or m.video or m.audio
            caption = m.caption or media.file_name or "Untitled File"
            size = round(media.file_size / 1048576, 2)

            new_index.append({"title": f"[{size} MB] {caption}", "id": m.id})
            total_files += 1

            if total_files % 25 == 0:
                await msg.edit(f"📄 Indexed {total_files} files...")

    FILE_INDEX.clear()
    FILE_INDEX.extend(new_index)
    with open(INDEX_FILE, "w") as f:
        json.dump(FILE_INDEX, f, indent=2)

    await msg.edit(f"✅ Indexed {total_files} files successfully!")


# ───────────── SEARCH COMMAND ─────────────
@app.on_message(filters.command("search"))
async def search_files(bot, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/search Naruto`", quote=True)

    query = " ".join(message.command[1:]).lower()

    results = [f for f in FILE_INDEX if query in f["title"].lower()]
    if not results:
        return await message.reply("❌ No results found.", quote=True)

    sent_msg = await send_results_page(bot, message.chat.id, results, query, 0, message.from_user.id)

    # Auto delete after 5 minutes
    await asyncio.sleep(300)
    try:
        await sent_msg.delete()
    except:
        pass


# ───────────── PAGINATION DISPLAY ─────────────
async def send_results_page(bot, chat_id, results, query, page, user_id):
    PER_PAGE = 7
    start = page * PER_PAGE
    end = start + PER_PAGE
    current_results = results[start:end]

    buttons = [
        [InlineKeyboardButton(text=f["title"][:60], callback_data=f"get_{f['id']}_{user_id}")]
        for f in current_results
    ]

    # Add Send All button
    buttons.insert(0, [InlineKeyboardButton("📤 Send All", callback_data=f"sendall_{page}_{query}_{user_id}")])

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}_{query}_{user_id}"))
    if end < len(results):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page_{page+1}_{query}_{user_id}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    msg = await bot.send_message(
        chat_id,
        f"🔍 Results for **{query}** (Page {page+1}/{(len(results)-1)//PER_PAGE + 1})",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return msg


# ───────────── PAGINATION CALLBACK ─────────────
@app.on_callback_query(filters.regex(r"^page_"))
async def page_navigation(bot, query: CallbackQuery):
    _, page, query_text, user_id = query.data.split("_", 3)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search results!", show_alert=True)

    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]
    await query.message.delete()
    await send_results_page(bot, query.message.chat.id, results, query_text, int(page), user_id)


# ───────────── SEND FILE ─────────────
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file(bot, query: CallbackQuery):
    _, msg_id, user_id = query.data.split("_")

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search result. Use /search yourself.", show_alert=True)

    try:
        try:
            await bot.send_chat_action(query.from_user.id, "upload_document")
        except Forbidden:
            return await query.answer(f"📩 Please start the bot first!\n👉 t.me/{BOT_USERNAME}", show_alert=True)

        await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DATABASE_CHANNEL,
            message_id=int(msg_id)
        )
        await query.answer("📤 Sent to your DM!", show_alert=False)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ───────────── SEND ALL FILES ON PAGE ─────────────
@app.on_callback_query(filters.regex(r"^sendall_"))
async def send_all(bot, query: CallbackQuery):
    _, page, query_text, user_id = query.data.split("_", 3)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search results!", show_alert=True)

    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]
    PER_PAGE = 7
    start = int(page) * PER_PAGE
    end = start + PER_PAGE
    selected = results[start:end]

    try:
        for f in selected:
            await bot.copy_message(
                chat_id=query.from_user.id,
                from_chat_id=DATABASE_CHANNEL,
                message_id=f["id"]
            )
        await query.answer("📦 Sent all 7 files to your DM!", show_alert=True)
    except Forbidden:
        await query.answer(f"📩 Please start the bot first!\n👉 t.me/{BOT_USERNAME}", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ───────────── START ─────────────
print("🤖 File Search Bot started successfully...")
app.run()
