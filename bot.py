import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN  

# Initialize bot
bot = Client("episodes_arranger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user files before processing
user_files = {}

# Regex pattern to detect episode numbers (e.g., "Episode 01", "EP_05", "E12", etc.)
EPISODE_PATTERN = re.compile(r'(?:ep|episode|e)(\d+)', re.IGNORECASE)

@bot.on_message(filters.private & filters.document | filters.video)
async def receive_files(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
    
    file_name = message.document.file_name if message.document else message.video.file_name
    file_id = message.document.file_id if message.document else message.video.file_id
    
    # Extract episode number
    match = EPISODE_PATTERN.search(file_name)
    episode_number = int(match.group(1)) if match else 9999  # Default to 9999 if no number found

    user_files[user_id].append({"file_id": file_id, "file_name": file_name, "ep_no": episode_number})
    
    await message.reply_text(f"✅ Received `{file_name}`. Send all episodes, then type `/arrange`.")

@bot.on_message(filters.private & filters.command("arrange"))
async def arrange_episodes(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_files or len(user_files[user_id]) == 0:
        await message.reply_text("❌ No episodes found. Send video files first!")
        return

    await message.reply_text("🔄 Sorting episodes in order...")

    # Sort episodes based on detected episode number
    sorted_files = sorted(user_files[user_id], key=lambda x: x["ep_no"])

    await message.reply_text("✅ Sorted! Uploading...")

    for i, file in enumerate(sorted_files, start=1):
        new_name = f"Episode {i}.mp4"  # Rename in proper order
        await client.send_document(
            chat_id=message.chat.id,
            document=file["file_id"],
            file_name=new_name,
            caption=f"📺 `{new_name}` (Ordered)"
        )
        await asyncio.sleep(2)  # Small delay to avoid flooding

    # Clear files after uploading
    del user_files[user_id]
    await message.reply_text("✅ All episodes uploaded in correct order!")

@bot.on_message(filters.private & filters.command("clear"))
async def clear_files(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_files:
        del user_files[user_id]
        await message.reply_text("🗑️ Cleared all uploaded files!")
    else:
        await message.reply_text("❌ No files to clear.")

@bot.on_message(filters.private & filters.command("start"))
async def start_message(client, message: Message):
    await message.reply_text(
        "👋 Welcome to the **Episodes Arranger Bot**!\n\n"
        "📥 Send me episodes one by one.\n"
        "📌 Once all episodes are sent, type `/arrange`.\n"
        "🔄 I will sort and upload them in order!"
    )

# Start the bot
bot.run()
