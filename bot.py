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
        # Start the FFmpeg process
        command = [
            'ffmpeg', '-hwaccel', 'auto', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize={width}:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}:alpha={opacity}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'copy', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        start_time = time.time()  # Start time to calculate elapsed and remaining time

        # Mock progress loop (since FFmpeg doesn't provide real-time progress)
        for i in range(total_steps):
            await asyncio.sleep(2)  # Simulate time taken per step
            progress += 1
            elapsed_time = time.time() - start_time
            estimated_time_left = (elapsed_time / progress) * (total_steps - progress)
            progress_bar = "⬢" * progress + "⬡" * (total_steps - progress)

            await progress_message.edit_text(f"Processing... {progress_bar} {progress * 10}%\nEstimated time left: {int(estimated_time_left)} seconds")

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
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

# Callback for editing watermark settings
@app.on_callback_query(filters.regex("^pos_"))
async def change_watermark_position(client, callback_query):
    position = callback_query.data.split("_")[1].replace("-", "_")
    user_id = callback_query.from_user.id

    if user_id in user_watermarks:
        user_watermarks[user_id]['position'] = position
    else:
        user_watermarks[user_id] = {'position': position}

    await callback_query.answer(f"Watermark position updated to {position.replace('_', ' ').title()} ✅")

@app.on_callback_query(filters.regex("set_width|set_opacity"))
async def on_callback_query(client, callback_query):
    setting = callback_query.data

    if setting == "set_width":
        width_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("50 px", callback_data="width_50"),
             InlineKeyboardButton("100 px", callback_data="width_100")],
            [InlineKeyboardButton("150 px", callback_data="width_150"),
             InlineKeyboardButton("200 px", callback_data="width_200")]
        ])
        await callback_query.message.edit_text("Choose watermark width:", reply_markup=width_keyboard)

    elif setting == "set_opacity":
        opacity_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.2", callback_data="opacity_0.2"),
             InlineKeyboardButton("0.5", callback_data="opacity_0.5")],
            [InlineKeyboardButton("0.8", callback_data="opacity_0.8"),
             InlineKeyboardButton("1.0", callback_data="opacity_1.0")]
        ])
        await callback_query.message.edit_text("Choose watermark opacity:", reply_markup=opacity_keyboard)

# Handle watermark position, width, and opacity changes
@app.on_callback_query(filters.regex("width_|opacity_"))
async def adjust_watermark_settings(client, callback_query):
    user_id = callback_query.from_user.id
    setting = callback_query.data

    if "width_" in setting:
        width = int(setting.split("_")[1])
        user_watermarks[user_id]['width'] = width
        await callback_query.message.edit_text(f"Watermark width set to {width} px")
    elif "opacity_" in setting:
        opacity = float(setting.split("_")[1])
        user_watermarks[user_id]['opacity'] = opacity
        await callback_query.message.edit_text(f"Watermark opacity set to {opacity}")

# Handling video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()

    progress_message = await message.reply("Adding watermark...")

    watermarked_video_path = await add_watermark(video_path, message.from_user.id, progress_message)

    if watermarked_video_path is None:
        await progress_message.edit("❌ Failed to add watermark. Please try again.")
    else:
        await progress_message.edit("Uploading watermarked video...")
        await message.reply_video(watermarked_video_path)

        os.remove(video_path)
        os.remove(watermarked_video_path)

app.run()
