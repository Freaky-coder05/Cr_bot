import os
import subprocess
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Load configuration
from config import API_ID, API_HASH, BOT_TOKEN, CRUNCHYROLL_USERNAME, CRUNCHYROLL_PASSWORD

# Initialize the bot
bot = Client("crunchyroll_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start command to greet the user
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Welcome to Crunchyroll Downloader Bot! Send me the Crunchyroll URL of the anime episode to download.")

# Handle Crunchyroll video download request
@bot.on_message(filters.text & filters.private)
async def download_video(client, message):
    anime_url = message.text.strip()
    
    # Check if the message is a valid URL (basic validation)
    if not anime_url.startswith("http"):
        await message.reply("Please send a valid Crunchyroll URL.")
        return

    # Notify user that download is starting
    await message.reply("Starting to download the video. Please wait...")

    # Define the output directory for downloaded videos
    output_dir = "/path/to/downloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Call the Crunchyroll Downloader script
    process = subprocess.Popen(
        ['python', '/path/to/Crunchyroll-Downloader-v3/cr-dl.py', anime_url, '-u', CRUNCHYROLL_USERNAME, '-p', CRUNCHYROLL_PASSWORD, '--no-mux', '--output', output_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # Reading the process output and sending progress updates
    output_lines = []
    for line in process.stdout:
        output_lines.append(line)
        if "Downloading" in line or "Progress" in line:
            await message.reply(line.strip())

    # Wait for the process to finish
    process.wait()

    # Check if the video has been downloaded
    video_filename = find_video_file(output_dir)
    if video_filename:
        video_path = os.path.join(output_dir, video_filename)
        
        # Notify user and upload the video
        await message.reply("Download complete! Uploading the video now...")
        await client.send_video(chat_id=message.chat.id, video=video_path)

        # Notify that the upload is complete
        await message.reply("Upload complete!")
    else:
        await message.reply("Error: Could not download the video. Please check the URL or try again later.")

# Helper function to find the downloaded video file in the output directory
def find_video_file(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".mp4"):
            return filename
    return None

# Run the bot
bot.run()
