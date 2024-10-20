import os
import shutil
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN, CRUNCHYROLL_USER, CRUNCHYROLL_PASS

# Create the bot client
bot = Client("crunchyroll_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to download Crunchyroll video with DRM using yt-dlp and N_m3u8DL-RE
async def download_drm_video(url, output_dir):
    try:
        # Extract M3U8 URL using yt-dlp
        m3u8_command = [
            "yt-dlp", "--username", CRUNCHYROLL_USER, "--password", CRUNCHYROLL_PASS, 
            "--get-url", url
        ]
        process = await asyncio.create_subprocess_exec(*m3u8_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"Error extracting M3U8 URL: {stderr.decode()}")
            return None

        m3u8_url = stdout.decode().strip()

        # Download the DRM video using N_m3u8DL-RE
        drm_command = [
            "/usr/local/bin/N_m3u8DL-RE", m3u8_url, "-M", "mp4", "-o", output_dir
        ]
        process = await asyncio.create_subprocess_exec(*drm_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"DRM Download error: {stderr.decode()}")
            return None

        # Find the downloaded video file in the output directory
        for file in os.listdir(output_dir):
            if file.endswith(".mp4"):
                return os.path.join(output_dir, file)

        return None
    except Exception as e:
        print(f"Exception during DRM video download: {e}")
        return None

# Function to send the video back to the user after downloading
async def send_video(bot, message, video_file):
    await message.reply_text("Uploading video...")
    await bot.send_video(chat_id=message.chat.id, video=video_file)
    shutil.rmtree(os.path.dirname(video_file))  # Clean up the output directory

# Start command handler
@bot.on_message(filters.command("start"))
async def start(bot, message):
    await message.reply_text("Welcome! Send a Crunchyroll link to download the video, including DRM-protected videos.")

# Download command handler
@bot.on_message(filters.text & filters.private)
async def handle_download(bot, message):
    url = message.text

    # Reply to indicate the download is starting
    await message.reply_text("Downloading video...")

    # Define the output directory for DRM video
    output_dir = f"./downloads/{message.chat.id}_crunchyroll_video"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Download the DRM-protected video
    video_file = await download_drm_video(url, output_dir)

    # Check if download was successful
    if video_file:
        await send_video(bot, message, video_file)
    else:
        await message.reply_text("Failed to download the video. Please check the link or your credentials.")

# Run the bot
bot.run()
