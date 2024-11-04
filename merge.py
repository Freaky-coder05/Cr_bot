import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to track user states
user_states = {}

# Function to handle video/audio merging in a single function
@app.on_message(filters.video | filters.document | filters.audio | filters.text)
async def merge_video(client: Client, message: Message):
    user_id = message.from_user.id

    # Initialize user state if not present
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None, "filename": None}

    user_state = user_states[user_id]

    # Step 1: Handle Video File
    if (message.video or message.document) and user_state["video"] is None:
        msg = await message.reply("Downloading your video...")
        video_path = await client.download_media(message)
        user_state["video"] = video_path
        await msg.edit_text("Video received! Now send an audio file to merge.")
        return

    # Step 2: Handle Audio File
    if (message.audio or message.document) and user_state["video"] and user_state["audio"] is None:
        msg = await message.reply("Downloading your audio...")
        audio_path = await client.download_media(message)
        user_state["audio"] = audio_path
        await msg.edit_text("Audio received! Now send the new file name (without extension).")
        return

    # Step 3: Handle Filename Input
    if message.text and user_state["video"] and user_state["audio"] and user_state["filename"] is None:
        new_file_name = message.text.strip()
        user_state["filename"] = f"{new_file_name}.mp4"  # Output filename with extension
        output_path = user_state["filename"]

        msg = await message.reply("Merging video and audio...")

        # FFmpeg command to merge video and audio
        command = [
            'ffmpeg', '-y',  # Overwrite without asking
            '-i', user_state["video"],  # Input video
            '-i', user_state["audio"],  # Input audio
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'copy',  # Copy audio
            '-map', '0:v:0',  # Use video stream from input video
            '-map', '1:a:0',  # Use audio stream from new audio
            output_path  # Output file
        ]

        # Run FFmpeg command
        subprocess.run(command)
        
        await msg.edit_text("Uploading your merged video...")

        # Send the output file to user
        await message.reply_document(output_path)

        # Clean up files
        os.remove(user_state["video"])
        os.remove(user_state["audio"])
        os.remove(output_path)

        # Reset user state
        user_states[user_id] = {"video": None, "audio": None, "filename": None}
