import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN

# Configurations
WATERMARK_PATH = "default_watermark.png"  # Default watermark path
WATERMARK_POS = "top-left"  # Default watermark position
WATERMARK_WIDTH = 100  # Default watermark width in pixels
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

async def add_watermark(video_path, user_id):
    # Fetch user-specific watermark settings or use defaults
    watermark_text = user_watermarks.get(user_id, {}).get('text', 'Anime_Warrior_Tamil')  # Default watermark text
    position = user_watermarks.get(user_id, {}).get('position', "top-left")  # Default position
    position_xy = POSITIONS.get(position, "10:10")  # Default to 10:10 if no match
    watermark_width = user_watermarks.get(user_id, {}).get('width', WATERMARK_WIDTH)  # Default watermark width
    watermark_opacity = user_watermarks.get(user_id, {}).get('opacity', WATERMARK_OPACITY)  # Default watermark opacity

    output_path = f"watermarked_{os.path.basename(video_path)}"

    try:
        # Run FFmpeg command to add text watermark
        command = [
            'ffmpeg', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}",
            '-filter_complex', f"[1:v]scale={watermark_width}:-1[wm];[0:v][wm]overlay={position_xy}:format=auto:alpha={watermark_opacity}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
            '-c:a', 'copy', output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {process.stderr.decode()}")

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

# Set watermark by replying to a text message
@app.on_message(filters.command("set_watermark") & filters.reply)
async def set_watermark(client, message):
    if message.reply_to_message and message.reply_to_message.text:
        watermark_text = message.reply_to_message.text
        user_id = message.from_user.id

        # Save the watermark text for the user
        user_watermarks[user_id] = {'text': watermark_text}

        await message.reply_text(f"Watermark set successfully ✅\nWatermark: {watermark_text}")
    else:
        await message.reply_text("Please reply to a text message to set the watermark.")
        
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

    # Send a message with the buttons
    await message.reply_text("Select watermark position:", reply_markup=InlineKeyboardMarkup(buttons))

# Handle callback queries to update watermark settings
@app.on_callback_query(filters.regex("^pos_"))
async def change_watermark_position(client, callback_query):
    position = callback_query.data.split("_")[1].replace("-", "_")
    user_id = callback_query.from_user.id

    if user_id in user_watermarks:
        user_watermarks[user_id]['position'] = position
    else:
        user_watermarks[user_id] = {'position': position}

    await callback_query.answer(f"Watermark position updated to {position.replace('_', ' ').title()} ✅")
    
# Handling video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    # Start downloading the video
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()

    # Add watermark to the downloaded video
    await download_message.edit("Adding watermark...")
    watermarked_video_path = await add_watermark(video_path, message.from_user.id)

    if watermarked_video_path is None:
        await download_message.edit("❌ Failed to add watermark. Please try again.")
    else:
        # Upload the watermarked video
        await download_message.edit("Uploading watermarked video...")
        await message.reply_video(watermarked_video_path)

        # Cleanup
        os.remove(video_path)
        os.remove(watermarked_video_path)

# Run the bot
app.run()
