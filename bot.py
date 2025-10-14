import os
import json
import asyncio
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyromod import listen
from pyrogram.errors import FloodWait, Forbidden
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

# ───────────── CONFIG ─────────────
API_ID = 24435985
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DATABASE_CHANNEL = -1003094784222
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
    await asyncio.sleep(300)
    try:
        await sent_msg.delete()
    except:
        pass


# ───────────── PAGINATION DISPLAY ─────────────
async def send_results_page(bot, chat_id, results, query, page, user_id, quality_filter=None, edit_msg=None):
    PER_PAGE = 7
    filtered_results = [f for f in results if query in f["title"].lower()]
    if quality_filter:
        filtered_results = [f for f in filtered_results if quality_filter.lower() in f["title"].lower()]

    start = page * PER_PAGE
    end = start + PER_PAGE
    current_results = filtered_results[start:end]

    if not current_results:
        text = f"❌ No {quality_filter or ''} results found for **{query}**."
        if edit_msg:
            return await edit_msg.edit_text(text)
        else:
            return await bot.send_message(chat_id, text)

    # Build inline buttons
    buttons = [
        [InlineKeyboardButton(text=f["title"][:60],
                              callback_data=f"get|{f['id']}|{user_id}")]
        for f in current_results
    ]

    # Send All button
    buttons.insert(0, [InlineKeyboardButton("📤 Send All",
        callback_data=f"sendall|{page}|{urllib.parse.quote(query)}|{user_id}|{quality_filter or 'all'}")])

    # Quality filters
    buttons.insert(1, [
        InlineKeyboardButton("480p", callback_data=f"filter|480p|{urllib.parse.quote(query)}|{page}|{user_id}"),
        InlineKeyboardButton("720p", callback_data=f"filter|720p|{urllib.parse.quote(query)}|{page}|{user_id}"),
        InlineKeyboardButton("1080p", callback_data=f"filter|1080p|{urllib.parse.quote(query)}|{page}|{user_id}")
    ])

    # Navigation
    nav_row = []
    if start > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Back",
                    callback_data=f"page|{page-1}|{urllib.parse.quote(query)}|{user_id}|{quality_filter or 'all'}"))
    if end < len(filtered_results):
        nav_row.append(InlineKeyboardButton("➡️ Next",
                    callback_data=f"page|{page+1}|{urllib.parse.quote(query)}|{user_id}|{quality_filter or 'all'}"))
    if nav_row:
        buttons.append(nav_row)

    text = f"🔍 Results for **{query}** ({quality_filter or 'All Qualities'})\nPage {page+1}/{(len(filtered_results)-1)//PER_PAGE + 1}"

    if edit_msg:
        return await edit_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        return await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))


# ───────────── PAGE CALLBACK ─────────────
@app.on_callback_query(filters.regex(r"^page\|"))
async def page_callback(bot, query: CallbackQuery):
    _, page, query_text, user_id, quality_filter = query.data.split("|", 4)
    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your results!", show_alert=True)
    query_text = urllib.parse.unquote(query_text)
    await send_results_page(bot, query.message.chat.id, FILE_INDEX, query_text, int(page), user_id,
                            None if quality_filter == "all" else quality_filter, query.message)


# ───────────── QUALITY FILTER CALLBACK ─────────────
@app.on_callback_query(filters.regex(r"^filter\|"))
async def filter_callback(bot, query: CallbackQuery):
    _, quality, query_text, page, user_id = query.data.split("|", 4)
    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your results!", show_alert=True)
    query_text = urllib.parse.unquote(query_text)
    await send_results_page(bot, query.message.chat.id, FILE_INDEX, query_text, int(page), user_id, quality, query.message)


# ───────────── SEND FILE CALLBACK ─────────────
@app.on_callback_query(filters.regex(r"^get\|"))
async def send_file(bot, query: CallbackQuery):
    try:
        _, msg_id, user_id = query.data.split("|")
        if str(query.from_user.id) != str(user_id):
            return await query.answer("⚠️ Not your result!", show_alert=True)

        await bot.send_chat_action(query.from_user.id, "upload_document")
        await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DATABASE_CHANNEL,
            message_id=int(msg_id)
        )
        await query.answer("📤 Sent to your DM!", show_alert=False)
    except Forbidden:
        await query.answer(f"📩 Start bot first!\n👉 t.me/{BOT_USERNAME}", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ───────────── SEND ALL CALLBACK ─────────────
@app.on_callback_query(filters.regex(r"^sendall\|"))
async def send_all(bot, query: CallbackQuery):
    _, page, query_text, user_id, quality_filter = query.data.split("|", 4)
    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your results!", show_alert=True)

    query_text = urllib.parse.unquote(query_text)
    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]
    if quality_filter != "all":
        results = [f for f in results if quality_filter.lower() in f["title"].lower()]

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
        await query.answer(f"📦 Sent all {len(selected)} {quality_filter} files!", show_alert=True)
    except Forbidden:
        await query.answer(f"📩 Start bot first!\n👉 t.me/{BOT_USERNAME}", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ───────────── START ─────────────
print("🤖 File Search Bot started successfully...")
app.run()
