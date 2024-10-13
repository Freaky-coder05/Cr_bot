import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import API_ID, API_HASH, BOT_TOKEN

# Configurations
WATERMARK_PATH = "default_watermark.png"  # Default watermark path
WATERMARK_WIDTH = 100  # Default watermark width in pixels
WATERMARK_OPACITY = 0.5  # Default watermark opacity

# Create your bot using your token from config
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to hold user watermark settings
user_watermarks = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hi, I am a watermark adder bot ☘️")

# Valid positions
POSITIONS = {
    "top-left": "10:10",
    "top-right": "main_w-overlay_w-10:10",
    "bottom-left": "10:main_h-overlay_h-10",
    "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
}

# Function to add watermark to video
def add_watermark(video_path, user_id):
    # Get user-specific settings, or use defaults
    watermark_path = user_watermarks.get(user_id, {}).get('path', WATERMARK_PATH)
    width = user_watermarks.get(user_id, {}).get('width', WATERMARK_WIDTH)
    opacity = user_watermarks.get(user_id, {}).get('opacity', WATERMARK_OPACITY)
    position = user_watermarks.get(user_id, {}).get('position', "top-left")

    output_path = f"watermarked_{os.path.basename(video_path)}"
    position_xy = POSITIONS.get(position, "10:10")

    try:
        # Run FFmpeg command to add image watermark
        command = [
            'ffmpeg', '-i', video_path,
            '-i', watermark_path,
            '-filter_complex',
            f"[1]scale={width}:-1[wm];[0][wm]overlay={position_xy}:format=auto:alpha={opacity}",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
            '-c:a', 'copy', output_path
        ]

        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

# Set watermark settings (position, size, transparency)
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message):
    user_id = message.from_user.id

    # Initialize user settings if not already present
    if user_id not in user_watermarks:
        user_watermarks[user_id] = {}

    buttons = [
        [
            InlineKeyboardButton("Position", callback_data="edit_position"),
            InlineKeyboardButton("Size", callback_data="edit_size"),
            InlineKeyboardButton("Transparency", callback_data="edit_opacity"),
        ]
    ]

    await message.reply_text("Edit watermark settings:", reply_markup=InlineKeyboardMarkup(buttons))

# Callback for editing watermark settings
@app.on_callback_query(filters.regex("edit_(position|size|opacity)"))
async def on_edit_settings(client, callback_query):
    user_id = callback_query.from_user.id

    # Initialize user settings if not already present
    if user_id not in user_watermarks:
        user_watermarks[user_id] = {}

    setting = callback_query.data.split("_")[1]

    if setting == "position":
        # Provide position options
        position_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Top-Left", callback_data="pos_top-left"),
             InlineKeyboardButton("Top-Right", callback_data="pos_top-right")],
            [InlineKeyboardButton("Bottom-Left", callback_data="pos_bottom-left"),
             InlineKeyboardButton("Bottom-Right", callback_data="pos_bottom-right")],
            [InlineKeyboardButton("Center", callback_data="pos_center")]
        ])
        await callback_query.message.edit_text("Choose watermark position:", reply_markup=position_keyboard)

    elif setting == "size":
        # Provide size options
        size_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("50px", callback_data="size_50"),
             InlineKeyboardButton("100px", callback_data="size_100")],
            [InlineKeyboardButton("150px", callback_data="size_150"),
             InlineKeyboardButton("200px", callback_data="size_200")]
        ])
        await callback_query.message.edit_text("Choose watermark size:", reply_markup=size_keyboard)

    elif setting == "opacity":
        # Provide opacity options
        opacity_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.2", callback_data="opacity_0.2"),
             InlineKeyboardButton("0.5", callback_data="opacity_0.5")],
            [InlineKeyboardButton("0.8", callback_data="opacity_0.8"),
             InlineKeyboardButton("1.0", callback_data="opacity_1.0")]
        ])
        await callback_query.message.edit_text("Choose watermark opacity:", reply_markup=opacity_keyboard)

# Handle position, size, and opacity callbacks
@app.on_callback_query(filters.regex("pos_|size_|opacity_"))
async def adjust_watermark_settings(client, callback_query):
    user_id = callback_query.from_user.id

    # Initialize user settings if not already present
    if user_id not in user_watermarks:
        user_watermarks[user_id] = {}

    data = callback_query.data

    if data.startswith("pos_"):
        position = data.split("_")[1]
        user_watermarks[user_id]['position'] = position
        await callback_query.message.edit_text(f"Position set to {position}")

    elif data.startswith("size_"):
        size = int(data.split("_")[1])
        user_watermarks[user_id]['width'] = size
        await callback_query.message.edit_text(f"Watermark size set to {size}px")

    elif data.startswith("opacity_"):
        opacity = float(data.split("_")[1])
        user_watermarks[user_id]['opacity'] = opacity
        await callback_query.message.edit_text(f"Opacity set to {opacity}")

# Set custom watermark text
@app.on_message(filters.command("set_watermark") & filters.reply)
async def set_custom_watermark(client, message):
    user_id = message.from_user.id
    watermark_text = message.reply_to_message.text

    # Save custom watermark text in user settings
    user_watermarks[user_id] = {'path': watermark_text}

    await message.reply_text(f"Custom watermark set to: {watermark_text}")

# Handling video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    # Initialize user settings if not already present
    user_id = message.from_user.id
    if user_id not in user_watermarks:
        user_watermarks[user_id] = {}

    # Start downloading the video
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()

    # Add watermark to the downloaded video
    await download_message.edit("Adding watermark...")
    watermarked_video_path = add_watermark(video_path, user_id)

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
