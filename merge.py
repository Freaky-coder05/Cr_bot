import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)


# Create a dictionary to keep track of user states
user_states = {}


# Function to merge video and audio
async def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    # FFmpeg command to replace existing audio with new audio
    command = [
        'ffmpeg', '-y',  # Overwrite without asking
        '-i', video_path,  # Input video
        '-i', audio_path,  # Input audio
        '-c:v', 'copy',  # Copy video without re-encoding
        '-c:a', 'copy',  # Encode audio to AAC
        '-map', '0:v:0',  # Use first video stream from the input
        '-map', '1:a:0',  # Use audio from the new audio file
        output_path  # Output file
    ]
    
    # Run the command
    subprocess.run(command)

# Handle video file
@app.on_message(filters.video)
async def merge_video(client: Client, message: Message):
    user_id = message.from_user.id
    # Ensure user state is initialized
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None}

    # Download video file
    msg = await message.reply("Downloading your video")
    video_path = await client.download_media(message)
    await msg.edit_text("Video received! Now send an audio file to merge.")

    # Store the video path in user state
    user_states[user_id]["video"] = video_path

# Handle audio file
@app.on_message(filters.audio | filters.document)
async def handle_audio(client: Client, message: Message):
    user_id = message.from_user.id
    # Ensure user state is initialized
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None}

    if user_states[user_id]["video"] is None:
        await message.reply("Please send a video file first.")
        return

    # Download audio file
    msg = await message.reply("Downloading your audio")
    audio_path = await client.download_media(message)
    user_states[user_id]["audio"] = audio_path

    # Ask for a new file name
    await msg.edit_text("Please send the new file name (without extension) for the merged file.")

# Handle new file name
@app.on_message(filters.text)
async def handle_file_name(client: Client, message: Message):
    user_id = message.from_user.id
    # Ensure user state is initialized
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None}

    if user_states[user_id]["audio"] is None:
        await message.reply("Please send an audio file first.")
        return

    # Get video and audio paths from user states
    video_path = user_states[user_id]["video"]
    audio_path = user_states[user_id]["audio"]
    
    # Create output file path
    new_file_name = message.text.strip()
    output_path = f"{new_file_name}.mp4"  # Set output file with .mp4 extension

    await msg.edit_text("Merging video and audio...")

    # Merge video and audio
    await merge_video_audio(video_path, audio_path, output_path)
    await msg.edit_text("Uploading your audio file")

    await message.reply_document(output_path)

    # Clean up files
    os.remove(video_path)
    os.remove(audio_path)
    os.remove(output_path)

    # Reset user state
    user_states[user_id] = {"video": None, "audio": None}
