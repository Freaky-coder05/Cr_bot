from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


API_ID =  24435985              # your API ID
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7758738938:AAFfwe6FlwIU22cwDdzhqWqlLSeJo9V1p_Q"
DB_CHANNEL = -1002134913785  # your database channel ID

bot = Client("FileSearchBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory dictionary to remember which user created which search
user_search_map = {}


# ===========================
# /start command
# ===========================
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("👋 Hello! Use `/search <name>` to find anime files.")


# ===========================
# /search command
# ===========================
@bot.on_message(filters.command("search"))
async def search_files(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("❌ Usage: `/search Naruto Shippuden`", quote=True)

    msg = await message.reply_text("🔎 Searching in database...")
    results = []
    async for msg_in_channel in client.search_messages(DB_CHANNEL, query=query, filter="document", limit=50):
        if not msg_in_channel.document:
            continue
        title = msg_in_channel.document.file_name
        size = round(msg_in_channel.document.file_size / (1024 * 1024), 2)
        message_id = msg_in_channel.id
        results.append((f"[{size} MB] {title}", message_id))

    if not results:
        return await msg.edit("❌ No results found.")

    # Create inline buttons
    buttons = [
        [InlineKeyboardButton(text=name[:60], callback_data=f"get_{message.from_user.id}_{mid}")]
        for name, mid in results[:10]
    ]

    markup = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("PAGE 1 / 1", callback_data="noop")]])

    await msg.edit_text(
        f"🔍 **Results for:** `{query}`\n\n⚠️ After 5 minutes this message will be automatically deleted.",
        reply_markup=markup
    )

    # Save the user ID for this message
    user_search_map[msg.id] = message.from_user.id

    # Auto delete after 5 minutes
    await asyncio.sleep(300)
    try:
        await msg.delete()
        if msg.id in user_search_map:
            del user_search_map[msg.id]
    except:
        pass


# ===========================
# Button click — message.copy
# ===========================
@bot.on_callback_query(filters.regex("^get_"))
async def get_file(client, query):
    # Extract original user ID and message ID
    data = query.data.split("_", 2)
    owner_id = int(data[1])
    msg_id = int(data[2])

    # Check if the button clicker is the same person
    if query.from_user.id != owner_id:
        return await query.answer("⚠️ Not your search result. Please use /search command.", show_alert=True)

    await query.answer("📤 Sending file privately...")

    try:
        await client.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=DB_CHANNEL,
            message_id=msg_id
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Failed to send file.\nError: {e}")


# ===========================
# Ignore non-functional buttons
# ===========================
@bot.on_callback_query(filters.regex("^noop"))
async def ignore(_, query):
    await query.answer("Navigation placeholder", show_alert=False)


print("🤖 File Search Bot Started...")
bot.run()
