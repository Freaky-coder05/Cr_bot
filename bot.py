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

# Load index cache
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

            media = m.document or m.video or m.audio
            if not media:
                continue

            caption = m.caption or "Untitled File"
            size = getattr(media, "file_size", 0)
            new_index.append({"title": caption, "id": m.id, "size": size})
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

    await send_results_page(bot, message.chat.id, results, query, 0, message.from_user.id)


# ───────────── PAGINATION DISPLAY ─────────────
async def send_results_page(bot, chat_id, results, query_text, page, user_id, quality=None):
    PER_PAGE = 7
    start = page * PER_PAGE
    end = start + PER_PAGE

    # Filter results by quality if selected
    filtered_results = results
    if quality:
        filtered_results = [f for f in results if quality in f["title"].lower()]

    current_results = filtered_results[start:end]

    buttons = [
        [InlineKeyboardButton(
            text=f"{f['title'][:40]} ({round(f['size']/1024/1024,1)} MB)" if f.get("size") else f['title'][:45],
            callback_data=f"get|{f['id']}|{user_id}"
        )] for f in current_results
    ]

    # Navigation buttons
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page|{page-1}|{query_text}|{user_id}"))
    if end < len(filtered_results):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page|{page+1}|{query_text}|{user_id}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    # Quality buttons (always at bottom)
    quality_buttons = [
        InlineKeyboardButton("480p", callback_data=f"filter|480p|{query_text}|{page}|{user_id}"),
        InlineKeyboardButton("720p", callback_data=f"filter|720p|{query_text}|{page}|{user_id}"),
        InlineKeyboardButton("1080p", callback_data=f"filter|1080p|{query_text}|{page}|{user_id}")
    ]
    buttons.append(quality_buttons)

    # Send All button
    buttons.append([InlineKeyboardButton("🎬 Send All", callback_data=f"sendall|{query_text}|{user_id}")])

    text = f"🔍 Results for **{query_text}** (Page {page+1}/{(len(filtered_results)-1)//PER_PAGE + 1})"
    if quality:
        text += f"\n🎞 Filter: **{quality.upper()}**"

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=(await bot.send_message(chat_id, "⏳ Loading...")).id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ───────────── CALLBACKS ─────────────
@app.on_callback_query(filters.regex(r"^page\|"))
async def page_navigation(bot, query: CallbackQuery):
    _, page, query_text, user_id = query.data.split("|", 3)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search results!", show_alert=True)

    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]
    await send_results_page(bot, query.message.chat.id, results, query_text, int(page), user_id)


@app.on_callback_query(filters.regex(r"^filter\|"))
async def filter_quality(bot, query: CallbackQuery):
    _, quality, query_text, page, user_id = query.data.split("|", 4)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search results!", show_alert=True)

    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]
    await send_results_page(bot, query.message.chat.id, results, query_text, int(page), user_id, quality)


@app.on_callback_query(filters.regex("^sendall\|"))
async def send_all_results(bot, query: CallbackQuery):
    _, query_text, user_id = query.data.split("|", 2)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search!", show_alert=True)

    results = [f for f in FILE_INDEX if query_text in f["title"].lower()]

    try:
        await bot.send_chat_action(query.from_user.id, "upload_document")
    except Forbidden:
        return await query.answer(
            f"📩 Please start the bot first!\n👉 t.me/{BOT_USERNAME}",
            show_alert=True
        )

    await query.answer("📤 Sending all files...")
    for f in results[:20]:  # safety limit
        try:
            await bot.copy_message(
                chat_id=query.from_user.id,
                from_chat_id=DATABASE_CHANNEL,
                message_id=f["id"]
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)


@app.on_callback_query(filters.regex(r"^get\|"))
async def send_file(bot, query: CallbackQuery):
    _, msg_id, user_id = query.data.split("|", 2)

    if str(query.from_user.id) != str(user_id):
        return await query.answer("⚠️ Not your search result.", show_alert=True)

    try:
        try:
            await bot.send_chat_action(query.from_user.id, "upload_document")
        except Forbidden:
            return await query.answer(
                f"📩 Please start the bot first!\n👉 t.me/{BOT_USERNAME}",
                show_alert=True
            )

        await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DATABASE_CHANNEL,
            message_id=int(msg_id)
        )
        await query.answer("📤 Sent to your DM!", show_alert=False)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ───────────── START ─────────────
print("🤖 File Search Bot started successfully...")
app.run()
