import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

# Configurations
WATERMARK_PATH = "default_watermark.png"  # Default watermark path
WATERMARK_POS = "top-right"  # Default watermark position
WATERMARK_WIDTH = 100  # Default watermark width in pixels
WATERMARK_OPACITY = 0.5  # Default opacity for the watermark

# Create your bot using your token from config
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to hold user watermark settings
user_watermarks = {}

@app.on_message(filters.command("start"))
async def start(client, message):
# Function to add watermark to video
    await message.reply_text("Hi iam a watermark adder bot ☘️")
    
async def add_watermark(video_path, user_id):
    # Fetch user settings or use default
    watermark = user_watermarks.get(user_id, {}).get('path', WATERMARK_PATH)
    position = user_watermarks.get(user_id, {}).get('position', WATERMARK_POS)
    width = user_watermarks.get(user_id, {}).get('width', WATERMARK_WIDTH)
    opacity = user_watermarks.get(user_id, {}).get('opacity', WATERMARK_OPACITY)

    output_path = f"watermarked_{os.path.basename(video_path)}"
    
    # FFmpeg command to add watermark
    ffmpeg.input(video_path).output(
        output_path,
        vf=f"movie={watermark} [watermark]; [in][watermark] overlay={position}",
        filter_complex=f"[0]scale=w={width}:h={-1}[scaled]",
        video_bitrate="800k"
    ).run()
    
    return output_path

# Command to set watermark
@app.on_message(filters.command("set_watermark") & filters.reply)
async def set_watermark(client, message: Message):
    # Assuming the replied-to message contains the watermark image
    if message.reply_to_message.photo or message.reply_to_message.document:
        watermark_path = await message.reply_to_message.download()
        user_watermarks[message.from_user.id] = {"path": watermark_path}
        await message.reply("Watermark set successfully ✅")
    else:
        await message.reply("Please reply to an image or document to set it as watermark.")

# Command to edit watermark settings
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Position", callback_data="set_position")],
        [InlineKeyboardButton("Width", callback_data="set_width")],
        [InlineKeyboardButton("Opacity", callback_data="set_opacity")]
    ])
    await message.reply("Select the setting to edit:", reply_markup=keyboard)

# Callback for editing watermark settings
@app.on_callback_query(filters.regex("set_position|set_width|set_opacity"))
async def on_callback_query(client, callback_query):
    setting = callback_query.data

    if setting == "set_position":
        # Show position options
        position_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Top-Left", callback_data="pos_top-left"),
             InlineKeyboardButton("Top-Right", callback_data="pos_top-right")],
            [InlineKeyboardButton("Bottom-Left", callback_data="pos_bottom-left"),
             InlineKeyboardButton("Bottom-Right", callback_data="pos_bottom-right")]
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

    # Upload the watermarked video
    await download_message.edit("Uploading watermarked video...")
    await message.reply_video(watermarked_video_path)

    # Cleanup
    os.remove(video_path)
    os.remove(watermarked_video_path)

# Run the bot
app.run()
