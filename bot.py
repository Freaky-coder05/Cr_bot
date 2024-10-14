import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN


app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Status messages for downloading and uploading
DOWNLOAD_STATUS = "Downloading video..."
ADDING_WATERMARK_STATUS = "Adding watermark..."
UPLOAD_STATUS = "Uploading video..."

# Start message when the bot starts
START_MESSAGE = "Hello! I am a watermark adder bot. Send me a video and I'll add a watermark!"

# Command to start the bot and display start message
@app.on_message(filters.command(["start"]))
async def start(client, message):
    await message.reply_text(START_MESSAGE)

# Function to download, process, and upload the video
@app.on_message(filters.video | filters.document)
async def add_watermark(client, message):
    if message.video or message.document:
        # Sending download status message
        status = await message.reply_text(DOWNLOAD_STATUS)
        
        # Downloading the video
        file_path = await message.download()
        await status.edit_text(ADDING_WATERMARK_STATUS)
        
        # Output video path
        output_file = "watermarked_" + file_path
        
        # FFmpeg command for adding watermark
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vf", "drawtext=text='Anime_Warrior_Tamil':fontsize=15:fontcolor=white@0.5:fontfile='/Windows/Fonts/georgiab.ttf'",
            "-c:a", "copy", output_file
        ]
        
        # Running the FFmpeg command
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await process.communicate()

        if os.path.exists(output_file):
            # Uploading the video after watermark is added
            await status.edit_text(UPLOAD_STATUS)
            await message.reply_video(output_file)
            os.remove(output_file)
        else:
            await status.edit_text("Failed to add watermark.")
        
        # Removing the original downloaded file
        os.remove(file_path)

# Running the bot
app.run()
