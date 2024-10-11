import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN, FFMPEG_PATH

# Create a Pyrogram client
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global watermark settings (defaults)
watermark_text = None
watermark_opacity = 1.0  # 1.0 means full visibility, 0.0 means fully transparent
watermark_position = "top-right"
watermark_width = 100

# Start message
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Welcome to the Video Watermark Adder bot! Use /add_watermark to set the watermark text.")

# Add watermark command to set watermark text
@app.on_message(filters.command("add_watermark"))
async def add_watermark(client, message):
    await message.reply("Please send the text you want to use as a watermark.")

# Handle setting the watermark text (avoid treating commands as watermark text)
@app.on_message(filters.text & ~filters.command)
async def set_watermark(client, message):
    global watermark_text
    watermark_text = message.text.strip()
    await message.reply(f"Watermark text set to: {watermark_text}. Now you can send a video, and I will add the watermark automatically.")

# Edit watermark settings using inline buttons
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Transparency", callback_data="set_transparency")],
        [InlineKeyboardButton("Position", callback_data="set_position")],
        [InlineKeyboardButton("Width", callback_data="set_width")]
    ])
    await message.reply("Adjust watermark settings:", reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(client, callback_query):
    global watermark_opacity, watermark_position, watermark_width
    data = callback_query.data

    if data == "set_transparency":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("100%", callback_data="opacity_1.0")],
            [InlineKeyboardButton("75%", callback_data="opacity_0.75")],
            [InlineKeyboardButton("50%", callback_data="opacity_0.5")],
            [InlineKeyboardButton("25%", callback_data="opacity_0.25")],
        ])
        await callback_query.message.reply("Choose watermark transparency:", reply_markup=keyboard)
    elif data.startswith("opacity_"):
        watermark_opacity = float(data.split("_")[1])
        await callback_query.message.reply(f"Transparency set to {int(watermark_opacity * 100)}%")

    elif data == "set_position":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Top Right", callback_data="position_top-right")],
            [InlineKeyboardButton("Top Left", callback_data="position_top-left")],
            [InlineKeyboardButton("Bottom Right", callback_data="position_bottom-right")],
            [InlineKeyboardButton("Bottom Left", callback_data="position_bottom-left")],
        ])
        await callback_query.message.reply("Choose watermark position:", reply_markup=keyboard)
    elif data.startswith("position_"):
        watermark_position = data.split("_")[1]
        await callback_query.message.reply(f"Position set to {watermark_position.replace('-', ' ').title()}")

    elif data == "set_width":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("100px", callback_data="width_100")],
            [InlineKeyboardButton("200px", callback_data="width_200")],
            [InlineKeyboardButton("300px", callback_data="width_300")],
        ])
        await callback_query.message.reply("Choose watermark width:", reply_markup=keyboard)
    elif data.startswith("width_"):
        watermark_width = int(data.split("_")[1])
        await callback_query.message.reply(f"Watermark width set to {watermark_width}px")

# Automatically process video or document files for watermarking
@app.on_message(filters.video | filters.document)
async def watermark_video(client, message):
    global watermark_text, watermark_opacity, watermark_position, watermark_width

    # Ensure watermark text is set
    if not watermark_text:
        await message.reply("Please set a watermark text first using /add_watermark.")
        return

    # Notify user that the video is being downloaded
    await message.reply("Downloading video...")

    # Download the video or document
    file_path = await message.download()
    await message.reply("Download completed. Adding watermark...")

    # Generate watermark position settings
    position_dict = {
        "top-right": "main_w-overlay_w-10:10",
        "top-left": "10:10",
        "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
        "bottom-left": "10:main_h-overlay_h-10"
    }
    position = position_dict.get(watermark_position, "main_w-overlay_w-10:10")
    output_file = f"watermarked_{message.video.file_name if message.video else message.document.file_name}"

    # Construct FFmpeg command
    ffmpeg_cmd = [
        FFMPEG_PATH, "-i", file_path, "-vf",
        f"drawtext=text='{watermark_text}':fontcolor=white@{watermark_opacity}:fontsize={watermark_width}:x={position}",
        output_file
    ]

    try:
        # Run FFmpeg command to add watermark
        subprocess.run(ffmpeg_cmd, check=True)
        await message.reply("Watermark added successfully! Uploading video...")
        
        # Upload the watermarked video
        await message.reply_video(output_file, caption="Here's your watermarked video!")
    except Exception as e:
        await message.reply(f"Error while adding watermark: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    app.run()
