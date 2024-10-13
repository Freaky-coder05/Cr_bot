import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN

# Configurations
WATERMARK_PATH = "default_watermark.png"  # Default watermark image path
DEFAULT_WATERMARK_TEXT = "Anime_Warrior_Tamil"  # Default watermark text
POSITIONS = {
    "top-left": "10:10",
    "top-right": "main_w-overlay_w-10:10",
    "bottom-left": "10:main_h-overlay_h-10",
    "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
}

# Create your bot
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to hold user watermark settings
user_watermarks = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hi, I am a watermark adder bot ☘️")

# Function to add watermark
async def add_watermark(video_path, user_id):
    user_settings = user_watermarks.get(user_id, {})
    watermark_text = user_settings.get('text', DEFAULT_WATERMARK_TEXT)
    position = user_settings.get('position', 'top-left')
    width = user_settings.get('width', 100)
    opacity = user_settings.get('opacity', 0.5)

    position_xy = POSITIONS.get(position, "10:10")
    output_path = f"watermarked_{os.path.basename(video_path)}"

    try:
        # Use FFmpeg to add the watermark asynchronously
        command = [
            'ffmpeg', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
            '-c:a', 'copy', output_path
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await process.communicate()

        if process.returncode != 0:
            raise Exception("Error during FFmpeg execution.")

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

# Adjust watermark settings
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message):
    user_id = message.from_user.id

    # Inline keyboard buttons for editing watermark settings
    buttons = [
        [InlineKeyboardButton("Set Position", callback_data="set_position")],
        [InlineKeyboardButton("Set Width", callback_data="set_width")],
        [InlineKeyboardButton("Set Opacity", callback_data="set_opacity")]
    ]

    await message.reply_text("Select an option to edit watermark settings:", reply_markup=InlineKeyboardMarkup(buttons))

# Handling the callback for settings
@app.on_callback_query(filters.regex("set_position|set_width|set_opacity"))
async def on_callback_query(client, callback_query):
    setting = callback_query.data

    if setting == "set_position":
        # Show position options
        position_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Top-Left", callback_data="pos_top-left"),
             InlineKeyboardButton("Top-Right", callback_data="pos_top-right")],
            [InlineKeyboardButton("Bottom-Left", callback_data="pos_bottom-left"),
             InlineKeyboardButton("Bottom-Right", callback_data="pos_bottom-right")],
            [InlineKeyboardButton("Center", callback_data="pos_center")]
        ])
        await callback_query.message.edit_text("Choose watermark position:", reply_markup=position_keyboard)

    elif setting == "set_width":
        # Show width adjustment options
        width_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("50 px", callback_data="width_50"),
             InlineKeyboardButton("100 px", callback_data="width_100")],
            [InlineKeyboardButton("150 px", callback_data="width_150"),
             InlineKeyboardButton("200 px", callback_data="width_200")]
        ])
        await callback_query.message.edit_text("Choose watermark width:", reply_markup=width_keyboard)

    elif setting == "set_opacity":
        # Show opacity adjustment options
        opacity_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.2", callback_data="opacity_0.2"),
             InlineKeyboardButton("0.5", callback_data="opacity_0.5")],
            [InlineKeyboardButton("0.8", callback_data="opacity_0.8"),
             InlineKeyboardButton("1.0", callback_data="opacity_1.0")]
        ])
        await callback_query.message.edit_text("Choose watermark opacity:", reply_markup=opacity_keyboard)

# Handle watermark position, width, and opacity changes
@app.on_callback_query(filters.regex("pos_|width_|opacity_"))
async def adjust_watermark_settings(client, callback_query):
    user_id = callback_query.from_user.id
    setting = callback_query.data

    if "pos_" in setting:
        position = setting.split("_")[1]
        user_watermarks[user_id] = user_watermarks.get(user_id, {})
        user_watermarks[user_id]['position'] = position
        await callback_query.message.edit_text(f"Watermark position set to {position}")

    elif "width_" in setting:
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
