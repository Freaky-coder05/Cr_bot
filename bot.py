import os
import ffmpeg
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, WATERMARK_PATH, WATERMARK_SIZE, WATERMARK_TRANSPARENCY, WATERMARK_POSITION

bot = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize a global variable for the watermark image path
current_watermark = WATERMARK_PATH

# Start message
START_MSG = "Welcome to the Advanced Watermark Bot! Send me a video, and I'll add a watermark.\n\nYou can also send an image to set it as the watermark."

@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply(START_MSG)

# Function to add watermark
async def add_watermark(input_file, output_file, watermark_file):
    try:
        stream = ffmpeg.input(input_file)
        watermark = ffmpeg.input(watermark_file)

        # Positioning, size, and transparency of the watermark
        if WATERMARK_POSITION == "top-right":
            position = "(main_w-overlay_w-10):10"
        elif WATERMARK_POSITION == "bottom-right":
            position = "(main_w-overlay_w-10):(main_h-overlay_h-10)"
        else:
            position = "10:10"

        stream = ffmpeg.overlay(
            stream,
            watermark,
            x=position,
            y=position,
            eval='init',
            opacity=WATERMARK_TRANSPARENCY,
            shortest=1
        ).output(output_file).global_args('-y')

        ffmpeg.run(stream)
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False
    return True

# Command to handle video files and add watermark
@bot.on_message(filters.video | filters.document)
async def watermark_handler(_, message):
    download_msg = await message.reply("Downloading video...")

    # Download video file
    video_path = await message.download()

    # Define output file path
    output_file = "watermarked_" + os.path.basename(video_path)

    await download_msg.edit("Adding watermark...")

    # Add watermark using FFmpeg
    success = await add_watermark(video_path, output_file, current_watermark)

    if success:
        await download_msg.edit("Uploading watermarked video...")
        await message.reply_video(video=output_file)

        # Clean up
        os.remove(video_path)
        os.remove(output_file)
    else:
        await download_msg.edit("Failed to add watermark.")

# Command to handle image files and set them as watermark
@bot.on_message(filters.photo)
async def set_watermark(_, message):
    global current_watermark

    # Download the new watermark image
    watermark_path = await message.download()

    # Set it as the current watermark
    current_watermark = watermark_path

    await message.reply("Watermark image set successfully ✅")

# Run the bot
bot.run()
