import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN  # Ensure you have your API ID, API HASH, and BOT TOKEN in config.py


app = Client("video_audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Command to start the bot
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply("Welcome! Send a video file first, and then send an audio file to merge them.")

# Function to merge video and audio
async def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    # FFmpeg command to replace existing audio with new audio
    command = [
        'ffmpeg', '-y',  # Overwrite without asking
        '-i', video_path,  # Input video
        '-i', audio_path,  # Input audio
        '-c:v', 'copy',  # Copy video without re-encoding
        '-c:a', 'aac',  # Encode audio to AAC
        '-map', '0:v:0',  # Use first video stream from the input
        '-map', '1:a:0',  # Use audio from the new audio file
        output_path  # Output file
    ]
    
    # Run the command
    subprocess.run(command)

# Handle video file
@app.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    # Download video file
    video_path = await client.download_media(message)
    await message.reply("Video received! Now send an audio file to merge.")

    # Wait for the audio file
    audio_message = await client.listen(message.chat.id)

    if audio_message.audio or audio_message.document:
        audio_path = await client.download_media(audio_message)

        # Ask for a new file name
        await message.reply("Please send the new file name (without extension) for the merged file.")
        
        # Listen for the new file name
        name_message = await client.listen(message.chat.id)
        new_file_name = name_message.text.strip()  # Get the file name from the user's message

        # Create output file path
        output_path = f"{new_file_name}.mp4"  # Set output file with .mp4 extension

        await message.reply("Merging video and audio...")

        # Merge video and audio
        await merge_video_audio(video_path, audio_path, output_path)

        await message.reply_document(output_path)

        # Clean up files
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)

    else:
        await message.reply("Please send a valid audio file.")

if __name__ == "__main__":
    app.run()
