import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

# Default watermark image path
WATERMARK_PATH = "default_watermark.png"

# Create your bot using your token from config
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hi, I am a watermark adder bot ☘️")

# Handle image upload to set as the new watermark
@app.on_message(filters.photo)
async def handle_image(client, message: Message):
    global WATERMARK_PATH
    # Download the image and set it as the watermark
    download_message = await message.reply("Downloading watermark image...")
    image_path = await message.download()
    
    # Update the global watermark path to the new image
    WATERMARK_PATH = image_path
    
    await download_message.edit_text("Watermark added successfully ✅")

# Handle video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()

    progress_message = await message.reply("Processing...")

    # Add watermark (using the updated WATERMARK_PATH)
    final_video_path = await add_watermark(video_path, message.from_user.id, progress_message)

    if final_video_path is None:
        await progress_message.edit("❌ Failed to add watermark. Please try again.")
    else:
        # Update the message to indicate the start of the upload process
        await progress_message.edit("Watermark added successfully! Uploading the video...")

        # Upload the final watermarked video
        await message.reply_video(final_video_path)

        # Clean up the files
        os.remove(video_path)
        os.remove(final_video_path)

        await progress_message.edit("✅ Video uploaded successfully.")

async def add_watermark(video_path, user_id, progress_message):
    global WATERMARK_PATH
    output_path = f"watermarked_{os.path.basename(video_path)}"

    try:
        # Start the FFmpeg process to add watermark with transparency handling
        command = [
            'ffmpeg', '-i', video_path, '-i', WATERMARK_PATH,
            '-filter_complex', '[1][0]scale2ref=w=iw*0.15:h=ow*0.15[wm][vid];[vid][wm]overlay=10:10',  # Scale the watermark and overlay
            '-c:a', 'copy', output_path
        ]

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

app.run()
