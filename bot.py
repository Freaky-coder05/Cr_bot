import os
import ffmpeg
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
import time

# Load configuration from config.py
from config import API_ID, API_HASH, BOT_TOKEN

bot = Client("video_audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_video = {}  # Dictionary to store the video file path for each user

# Function to show progress for downloads/uploads
async def progress_bar(current, total, message, status):
    try:
        percent = current * 100 / total
        progress_message = f"{status}: {percent:.1f}%\n{current / 1024 / 1024:.1f}MB of {total / 1024 / 1024:.1f}MB"
        await message.edit(progress_message)
    except MessageNotModified:
        pass

# Start message
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello! I am a Video+Audio Merger bot. Send me a video, and then send the audio file you want to merge with it!")

# Function to ask for the new file name
async def ask_for_name(client, message):
    await message.reply("Please provide a new name for the merged video (without the extension).")
    
    # Listen for user's reply with the new name
    try:
        name_msg = await client.listen_for_text(message.chat.id, timeout=30)  # Wait for the user's response
        return name_msg.text.strip()
    except asyncio.TimeoutError:
        await message.reply("No name provided. Merging process aborted due to timeout.")
        return None

# Function to handle video file uploads
@bot.on_message(filters.video | filters.document)
async def handle_video(client, message):
    if message.video or (message.document and message.document.mime_type.startswith("video/")):
        video_progress = await message.reply("Downloading video...")

        # Download the video file
        video_file = await message.download(progress=lambda current, total: asyncio.run(progress_bar(current, total, video_progress, "Downloading video")))
        
        # Store the video file path for this user
        user_video[message.from_user.id] = video_file
        await message.reply("Video received! Now, please send the audio file you want to merge with the video.")
    else:
        await message.reply("Please send a valid video file.")

# Function to handle audio file uploads and merge them with the video
@bot.on_message(filters.audio | filters.document)
async def handle_audio(client, message):
    user_id = message.from_user.id

    # Check if the user has already uploaded a video
    if user_id not in user_video:
        await message.reply("Please upload a video first before sending the audio.")
        return

    # Check if the document is an audio file
    if message.document and not message.document.mime_type.startswith("audio/"):
        await message.reply("Please send a valid audio file.")
        return

    audio_progress = await message.reply("Downloading audio...")

    # Download the audio file
    audio_file = await message.download(progress=lambda current, total: asyncio.run(progress_bar(current, total, audio_progress, "Downloading audio")))

    # Ask the user for a new name for the output file
    new_name = await ask_for_name(client, message)
    if not new_name:
        return  # Abort if no name is provided

    # Set the output file name with the new name provided by the user
    output_file = f"{new_name}.mp4"

    video_file = user_video.pop(user_id)  # Get the video file path and remove from the dictionary

    # FFmpeg command to remove existing audio from the video and add the new audio
    try:
        await message.reply("Merging video and audio...")

        # Merge video with the new audio
        ffmpeg.input(video_file).output(audio_file).output(output_file, codec="copy").run()

        await message.reply(f"Merging complete. The file has been renamed to {new_name}. Uploading the file...")

        # Upload the merged file with a progress bar
        upload_progress = await message.reply("Uploading file...")
        await message.reply_document(
            document=output_file,
            progress=lambda current, total: asyncio.run(progress_bar(current, total, upload_progress, "Uploading file"))
        )

    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")

    finally:
        # Clean up
        os.remove(video_file)
        os.remove(audio_file)
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    bot.run()
