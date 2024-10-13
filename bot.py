import os
import asyncio
import time
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

# Configurations
WATERMARK_PATH = "default_watermark.png"  # Default watermark path
WATERMARK_POS = "top-left"  # Default watermark position
WATERMARK_WIDTH = 50  # Default watermark width in pixels
WATERMARK_OPACITY = 0.5  # Default opacity for the watermark

# Create your bot using your token from config
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to hold user watermark settings
user_watermarks = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hi, I am a watermark adder bot ☘️")

# Valid predefined positions and their corresponding x:y coordinates
POSITIONS = {
    "top-left": "10:10",
    "top-right": "main_w-overlay_w-10:10",
    "bottom-left": "10:main_h-overlay_h-10",
    "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
}

# Helper function to get video duration in seconds using FFmpeg
async def get_video_duration(video_path):
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error fetching video duration: {e}")
        return None

# Function to parse FFmpeg progress from its stderr output
def parse_ffmpeg_progress(line):
    match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    return None

# Function to handle watermarking and encoding progress dynamically
async def add_watermark(video_path, user_id, progress_message):
    # Fetch user-specific watermark settings or use defaults
    watermark_text = user_watermarks.get(user_id, {}).get('text', 'Anime_Warrior_Tamil')  # Default watermark text
    position = user_watermarks.get(user_id, {}).get('position', "top-left")  # Default position
    position_xy = POSITIONS.get(position, "10:10")
    width = user_watermarks.get(user_id, {}).get('width', 15)  # Default width in pixels
    opacity = user_watermarks.get(user_id, {}).get('opacity', 0.5)  # Default opacity

    output_path = f"watermarked_{os.path.basename(video_path)}"

    # Get video duration to calculate progress
    video_duration = await get_video_duration(video_path)
    if not video_duration:
        await progress_message.edit_text("❌ Failed to retrieve video duration.")
        return None

    try:
        # Run FFmpeg command to add text watermark with hardware acceleration
        command = [
            'ffmpeg', '-hwaccel', 'auto', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize={width}:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}:alpha={opacity}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'copy', '-y', output_path
        ]

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        progress = 0

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            # Decode the stderr line from bytes to string
            line = line.decode('utf-8').strip()

            # Parse progress from FFmpeg output
            current_time = parse_ffmpeg_progress(line)
            if current_time is not None:
                progress = int((current_time / video_duration) * 100)
                estimated_time_left = (video_duration - current_time) / 100  # Simple estimation
                progress_bar = "⬢" * (progress // 10) + "⬡" * (10 - (progress // 10))

                await progress_message.edit_text(f"Adding watermark... {progress_bar} {progress}%\nEstimated time left: {int(estimated_time_left)} seconds")

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

        await progress_message.edit_text("Watermark added successfully! Starting encoding...")

        # Encode the watermarked video
        encoded_video_path = await encode_video(output_path, progress_message, video_duration)

        if encoded_video_path is None:
            return None

        return encoded_video_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

# Function to handle encoding progress dynamically
async def encode_video(watermarked_path, progress_message, video_duration):
    encoded_output_path = f"encoded_{os.path.basename(watermarked_path)}"

    try:
        # FFmpeg encoding command with optimizations to reduce output file size
        command = [
            'ffmpeg', '-i', watermarked_path,
            '-c:v', 'libx264', '-crf', '28', '-preset', 'fast',  # Increased CRF to reduce file size
            '-c:a', 'aac', '-b:a', '128k',  # Optimize audio size
            '-movflags', '+faststart',  # Helps with streaming and playback
            '-y', encoded_output_path
        ]

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        progress = 0

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            # Decode the stderr line from bytes to string
            line = line.decode('utf-8').strip()

            # Parse progress from FFmpeg output
            current_time = parse_ffmpeg_progress(line)
            if current_time is not None:
                progress = int((current_time / video_duration) * 100)
                estimated_time_left = (video_duration - current_time) / 100  # Simple estimation
                progress_bar = "⬢" * (progress // 10) + "⬡" * (10 - (progress // 10))

                await progress_message.edit_text(f"Encoding... {progress_bar} {progress}%\nEstimated time left: {int(estimated_time_left)} seconds")

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg encoding error: {stderr.decode()}")

        return encoded_output_path

    except Exception as e:
        print(f"Error during encoding: {e}")
        return None

# Handle video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()

    progress_message = await message.reply("Processing...")

    # Add watermark and encode the video
    final_video_path = await add_watermark(video_path, message.from_user.id, progress_message)

    if final_video_path is None:
        await progress_message.edit("❌ Failed to add watermark and encode. Please try again.")
    else:
        await progress_message.edit("Encoding completed! Uploading the video...")

        # Upload the final encoded video
        await message.reply_video(final_video_path)

        # Clean up the files
        os.remove(video_path)
        os.remove(final_video_path)

        await progress_message.edit("✅ Video uploaded successfully.")

app.run()
