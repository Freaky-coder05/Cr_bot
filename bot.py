import os
import asyncio
import time
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

async def add_watermark(video_path, user_id, progress_message):
    # Fetch user-specific watermark settings or use defaults
    watermark_text = user_watermarks.get(user_id, {}).get('text', 'Anime_Warrior_Tamil')  # Default watermark text
    position = user_watermarks.get(user_id, {}).get('position', "top-left")  # Default position
    position_xy = POSITIONS.get(position, "10:10")
    width = user_watermarks.get(user_id, {}).get('width', 15)  # Default width in pixels
    opacity = user_watermarks.get(user_id, {}).get('opacity', 0.5)  # Default opacity

    output_path = f"watermarked_{os.path.basename(video_path)}"
    total_steps = 10  # Define total steps for the progress bar
    progress = 0  # Initialize progress

    try:
        # Start the FFmpeg process to add watermark
        command = [
            'ffmpeg', '-hwaccel', 'auto', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize={width}:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}:alpha={opacity}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'copy', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        start_time = time.time()  # Start time to calculate elapsed and remaining time

        # Mock progress loop for watermarking
        for i in range(total_steps):
            await asyncio.sleep(2)  # Simulate time taken per step
            progress += 1
            elapsed_time = time.time() - start_time
            estimated_time_left = (elapsed_time / progress) * (total_steps - progress)
            progress_bar = "⬢" * progress + "⬡" * (total_steps - progress)

            await progress_message.edit_text(f"Adding watermark... {progress_bar} {progress * 10}%\nEstimated time left: {int(estimated_time_left)} seconds")

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

        # Proceed to encoding step after watermarking
        await progress_message.edit_text("Watermark added successfully! Starting encoding...")

        # Call encoding function with a separate progress bar
        encoded_video_path = await encode_video(output_path, progress_message)

        if encoded_video_path is None:
            return None

        return encoded_video_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None


async def encode_video(watermarked_path, progress_message):
    encoded_output_path = f"encoded_{os.path.basename(watermarked_path)}"
    total_steps = 10  # Define total steps for encoding progress bar
    progress = 0  # Initialize progress

    try:
        # Simulate FFmpeg encoding command
        command = [
            'ffmpeg', '-i', watermarked_path,
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-strict', 'experimental', encoded_output_path
        ]

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        start_time = time.time()

        # Mock progress loop for encoding
        for i in range(total_steps):
            await asyncio.sleep(2)  # Simulate time taken per step
            progress += 1
            elapsed_time = time.time() - start_time
            estimated_time_left = (elapsed_time / progress) * (total_steps - progress)
            progress_bar = "⬢" * progress + "⬡" * (total_steps - progress)

            await progress_message.edit_text(f"Encoding... {progress_bar} {progress * 10}%\nEstimated time left: {int(estimated_time_left)} seconds")

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg encoding error: {stderr.decode()}")

        return encoded_output_path

    except Exception as e:
        print(f"Error during encoding: {e}")
        return None


# Command to edit watermark settings
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message):
    user_id = message.from_user.id

    # Create inline buttons for adjusting watermark position, size, and transparency
    buttons = [
        [
            InlineKeyboardButton("Top-Left", callback_data="pos_top_left"),
            InlineKeyboardButton("Top-Right", callback_data="pos_top_right")
        ],
        [
            InlineKeyboardButton("Bottom-Left", callback_data="pos_bottom_left"),
            InlineKeyboardButton("Bottom-Right", callback_data="pos_bottom_right")
        ],
        [InlineKeyboardButton("Center", callback_data="pos_center")]
    ]

    await message.reply_text("Select watermark position:", reply_markup=InlineKeyboardMarkup(buttons))

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
        # Update the message to indicate the start of the upload process
        await progress_message.edit("Encoding completed! Uploading the video...")

        # Upload the final encoded video
        await message.reply_video(final_video_path)

        # Clean up the files
        os.remove(video_path)
        os.remove(final_video_path)

        # Edit the message to show upload is complete
        await progress_message.edit("✅ Video uploaded successfully.")

app.run()
