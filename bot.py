import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Load configuration
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, WATERMARK_PATH

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper function to add watermark
def add_watermark(video_path: str, output_path: str, watermark_path: str, position: str, transparency: float, size: str):
    scale = "1"
    if size == "small":
        scale = "0.25"
    elif size == "medium":
        scale = "0.5"
    elif size == "large":
        scale = "1"

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex", f"[1][0]scale={scale}*iw:{scale}*ih[wm];[0][wm]overlay={position}",
        "-c:a", "copy",
        output_path
    ]
    
    # Adding transparency
    if transparency < 1.0:
        cmd.insert(5, "-vf")
        cmd.insert(6, f"format=rgba, colorchannelmixer=0:0:0:{transparency}")

    subprocess.run(cmd)

# Helper function to remove watermark (For demonstration)
def remove_watermark(video_path: str, output_path: str):
    # Note: Real removal is complex and requires advanced techniques. This is a placeholder.
    os.rename(video_path, output_path)  # Simulate by renaming

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("Welcome to the Watermark Bot! Use /add_watermark or /remove_watermark or send an image to set as a watermark.")

@app.on_message(filters.command("add_watermark"))
async def add_watermark_command(client, message: Message):
    await message.reply("Please send a video file to add the watermark.")

@app.on_message(filters.command("remove_watermark"))
async def remove_watermark_command(client, message: Message):
    await message.reply("Please send a video file to remove the watermark.")

@app.on_message(filters.photo)
async def set_watermark(client, message: Message):
    # Save the watermark image
    watermark_path = f"downloads/watermark_{message.photo.file_id}.png"
    await message.download(watermark_path)
    
    # Update the watermark path in the configuration or globally
    global WATERMARK_PATH
    WATERMARK_PATH = watermark_path

    await message.reply("Watermark added successfully ✅")

@app.on_message(filters.video)
async def handle_video(client, message: Message):
    # Assuming the user sent a video after the /add_watermark command
    video_path = f"downloads/{message.video.file_id}.mp4"
    output_path = f"downloads/output_{message.video.file_id}.mp4"
    position = "10:10"  # Example position (x:y)
    transparency = 0.5  # Example transparency
    size = "medium"  # Example size

    await message.download(video_path)
    await message.reply("Processing video...")

    # Add watermark
    add_watermark(video_path, output_path, WATERMARK_PATH, position, transparency, size)

    await message.reply_video(output_path, caption="Here is your watermarked video!")
    os.remove(video_path)
    os.remove(output_path)

@app.on_message(filters.video & filters.command("remove_watermark"))
async def handle_remove_video(client, message: Message):
    # Handle removing watermark
    video_path = f"downloads/{message.video.file_id}.mp4"
    output_path = f"downloads/output_{message.video.file_id}.mp4"

    await message.download(video_path)
    await message.reply("Removing watermark...")

    # Simulate watermark removal
    remove_watermark(video_path, output_path)

    await message.reply_video(output_path, caption="Here is your video without the watermark!")
    os.remove(video_path)
    os.remove(output_path)

if __name__ == "__main__":
    app.run()
