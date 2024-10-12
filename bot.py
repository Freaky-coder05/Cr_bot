import os
import subprocess
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import CRUNCHYROLL_USERNAME, CRUNCHYROLL_PASSWORD, BOT_TOKEN, API_HASH, API_ID
from time import sleep


# Initialize the Pyrogram Client
app = Client("crunchyroll_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def download_progress(process: subprocess.Popen, message: Message):
    """Simulate a progress indicator for the download process and send updates to Telegram."""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        if 'Duration' in line or 'time=' in line:
            # Example: Parse and display download progress here
            message.edit_text(f"Downloading: {line.strip()}")
            sleep(1)  # Simulate delay for updates

async def upload_progress(message: Message):
    """Simulate upload progress and update the Telegram message."""
    for i in range(1, 101, 10):
        await message.edit_text(f"Uploading: {i}% complete")
        await asyncio.sleep(0.5)  # Simulating delay for upload progress

@app.on_message(filters.command('start'))
async def start(_, message: Message):
    await message.reply_text("Welcome to the Crunchyroll Downloader Bot!\nUse /download <anime_url> to download a Crunchyroll video.")

@app.on_message(filters.command('download'))
async def download_video(_, message: Message):
    # Extract URL from the message
    if len(message.command) < 2:
        await message.reply_text("Please provide the anime URL. Usage: /download <anime_url>")
        return
    
    anime_url = message.command[1]

    try:
        msg = await message.reply_text(f"Starting DRM download for {anime_url}...")

        # Download video using Crunchyroll Downloader v3 (drm-protected video)
        process = subprocess.Popen(
            ['cr-dl', anime_url, '-u', CRUNCHYROLL_USERNAME, '-p', CRUNCHYROLL_PASSWORD, '--no-mux'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Monitor download progress
        await asyncio.to_thread(download_progress, process, msg)

        # Simulate upload progress after download completes
        await msg.edit_text("Download completed. Starting upload...")
        await upload_progress(msg)

        # After download, upload the file to the user (this is simulated here, adjust with actual file path)
        downloaded_file = f'{anime_url.split("/")[-1]}.mp4'  # Assume the video file is saved with this name
        await app.send_video(message.chat.id, downloaded_file, caption=f"Downloaded successfully from {anime_url}")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

if __name__ == '__main__':
    app.run()
