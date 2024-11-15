import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN  # Ensure you have your API ID, API HASH, and BOT TOKEN in config.py

app = Client("video_audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Create a dictionary to keep track of user states
user_states = {}

# Subtitle file content
subtitle_content = """1
00:00:00,000 --> 00:00:10,000
T.me:Anime_Warrior_Tamil

2
00:05:00,000 --> 00:05:10,000
T.me:Anime_Warrior_Tamil

3
00:10:00,000 --> 00:10:10,000
T.me:Anime_Warrior_Tamil

4
00:15:00,000 --> 00:15:10,000
T.me:Anime_Warrior_Tamil
"""

# Function to write subtitle content to a file
def write_subtitle_file():
    with open("subtitle.srt", "w") as f:
        f.write(subtitle_content)

# Command to start the bot
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    # Initialize user state
    user_states[user_id] = {"video": None, "audio": None}
    await message.reply("Welcome! Send a video file first, and then send an audio file to merge them.")

# Function to merge video, audio, and add subtitles
async def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    # Write the subtitle file
    write_subtitle_file()
    
    # FFmpeg command to replace existing audio, add new audio, and add subtitles
    command = [
        'ffmpeg', '-y',  # Overwrite without asking
        '-i', video_path,  # Input video
        '-i', audio_path,  # Input audio
        '-vf', "subtitles=subtitle.srt:force_style='Alignment=6'",  # Add subtitles at the top center
        '-c:v', 'libx264',  # Re-encode video to apply subtitle filter
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
    user_id = message.from_user.id
    # Ensure user state is initialized
    if user_id not in user_states:
        user_states[user_id] = {"video": None, "audio": None}

    # Download video file
    await message.reply("Downloading video ")
    video_path = await client.download_media(message)
    await message.reply("Video received! Now send an audio file to merge.")

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
   
    audio_path = await client.download_media(message)
    user_states[user_id]["audio"] = audio_path

    # Ask for a new file name
    await message.reply("Please send the new file name (without extension) for the merged file.")

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

    await message.reply("Merging video and audio with subtitles...")

    # Merge video and audio with subtitles
    await merge_video_audio(video_path, audio_path, output_path)
    await message.reply("uploading file")
    await message.reply_document(output_path)

    # Clean up files
    os.remove(video_path)
    os.remove(audio_path)
    os.remove(output_path)
    os.remove("subtitle.srt")

    # Reset user state
    user_states[user_id] = {"video": None, "audio": None}

if __name__ == "__main__":
    app.run()
