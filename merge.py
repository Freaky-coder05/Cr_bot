import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

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

async def merge_video(client: Client, message: Message):
    user_id = message.from_user.id
    # Ensure user state is initialized
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None}

    # Download video file
    msg = await message.reply("Downloading your video file")
    video_path = await client.download_media(message)
    await msg.edit_text("Video received! Now send an audio file to merge.")

    # Store the video path in user state
    user_states[user_id]["video"] = video_path

    if user_states[user_id]["video"] is None:
        await msg.edit_text("Please send a video file first.")
        return

    # Download audio file
    await msg.edit_text("Downloading your audio")
    audio_path = await client.download_media(message)
    user_states[user_id]["audio"] = audio_path

    # Ask for a new file name
    await msg.edit_text("Please send the new file name (without extension) for the merged file.")

    if user_states[user_id]["audio"] is None:
        await message.reply("Please send an audio file first.")
        return

    # Get video and audio paths from user states
    video_path = user_states[user_id]["video"]
    audio_path = user_states[user_id]["audio"]
    
    # Create output file path
    new_file_name = message.text.strip()
    output_path = f"{new_file_name}.mp4"  # Set output file with .mp4 extension

    await message.reply("Merging video and audio...")

    # Merge video and audio
    await merge_video_audio(video_path, audio_path, output_path)
    await message.edit_text("Uploading your file")
    await message.reply_document(output_path)

    # Clean up files
    os.remove(video_path)
    os.remove(audio_path)
    os.remove(output_path)

    # Reset user state
    user_states[user_id] = {"video": None, "audio": None}
