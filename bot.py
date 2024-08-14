import os
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, request, jsonify
from config import API_ID, API_HASH, BOT_TOKEN, FLASK_PORT
from datetime import datetime

# Initialize the Telegram client
bot = Client(
    "sync_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize Flask
app = Flask(__name__)

# Function to synchronize video and audio using FFmpeg
async def sync_video_audio(input_video, output_video):
    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-async", "1",  # Ensure audio sync
        output_video
    ]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.communicate()

@bot.on_message(filters.command("sync") & filters.video)
async def sync_handler(bot, message: Message):
    # Download the video file
    video_path = await message.download()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"synced_{timestamp}_{os.path.basename(video_path)}"

    # Notify user that the synchronization process has started
    await message.reply_text("🔄 Synchronizing video and audio... Please wait.")

    # Run the synchronization function
    await sync_video_audio(video_path, output_path)

    # Send the synchronized video back to the user
    await message.reply_video(output_path)

    # Cleanup: Remove the downloaded and processed files
    os.remove(video_path)
    os.remove(output_path)

    # Notify user that the synchronization is complete
    await message.reply_text("✅ Synchronization complete! Here is your video.")

if __name__ == "__main__":
    bot.run()
