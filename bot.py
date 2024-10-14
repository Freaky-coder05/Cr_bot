import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, WATERMARK_PATH, WORKING_DIR

# Initialize the bot
bot = Client(
    "watermark_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Start message
START_MESSAGE = "Hello! Send me a video and I'll add a watermark to it. You can also specify watermark size and position."

# Available positions for the watermark
positions = {
    "Top-Left": "10:10",
    "Top-Right": "main_w-overlay_w-10:10",
    "Bottom-Left": "10:main_h-overlay_h-10",
    "Bottom-Right": "main_w-overlay_w-10:main_h-overlay_h-10"
}

# Dictionary to hold user session data
user_sessions = {}

# Function to create a simple watermark image
def create_watermark_image():
    width, height = 400, 100
    watermark = Image.new("RGBA", (width, height), (255, 255, 255, 0))

    # Load a font (default font is used here; adjust if necessary)
    font = ImageFont.load_default()
    draw = ImageDraw.Draw(watermark)

    # Draw the text on the image
    text = "Sample Watermark"

    # Calculate the bounding box of the text
    bbox = draw.textbbox((0, 0), text, font=font)
    textwidth = bbox[2] - bbox[0]
    textheight = bbox[3] - bbox[1]

    # Position the text
    x = (width - textwidth) / 2
    y = (height - textheight) / 2

    # Draw text with white color and an alpha of 128 (50% opacity)
    draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)

    # Save the watermark image
    watermark.save(WATERMARK_PATH)

# Check if the watermark image exists, and create it if it doesn't
if not os.path.exists(WATERMARK_PATH):
    create_watermark_image()

# Handle the /start command
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(START_MESSAGE)

# Handle video uploads
@bot.on_message(filters.video | filters.document)
async def add_watermark(client, message):
    video = message.video or message.document

    # Prompt for watermark size and position
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Size 50%", callback_data="size_50"), InlineKeyboardButton("Size 75%", callback_data="size_75")],
        [InlineKeyboardButton("Top-Left", callback_data="position_top_left"), InlineKeyboardButton("Top-Right", callback_data="position_top_right")],
        [InlineKeyboardButton("Bottom-Left", callback_data="position_bottom_left"), InlineKeyboardButton("Bottom-Right", callback_data="position_bottom_right")]
    ])

    # Send response
    await message.reply_text("Select watermark size and position:", reply_markup=keyboard)

    # Store file info for later use
    file_path = await message.download(f"{WORKING_DIR}/{video.file_name}")
    print(f"File downloaded: {file_path}")  # Debugging statement
    user_sessions[message.from_user.id] = {"file_path": file_path}  # Store for further use

# Handle button presses for size and position
@bot.on_callback_query()
async def handle_query(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Retrieve file path from the user session
    file_info = user_sessions.get(user_id)

    if file_info is None:
        await callback_query.answer("No video found, please send a video first.")
        return

    file_path = file_info["file_path"]
    print(f"User {user_id} selected size/position with file path: {file_path}")  # Debugging statement

    # Determine watermark size and position
    if data.startswith("size_"):
        size = int(data.split("_")[1])
        user_sessions[user_id]["size"] = size
        await callback_query.answer("Size selected!")
    elif data.startswith("position_"):
        pos_key = data.split("_")[1] + "_" + data.split("_")[2]
        position = positions.get(pos_key.replace('_', '-'))
        user_sessions[user_id]["position"] = position
        await callback_query.answer("Position selected!")

    # Start watermarking once both size and position are selected
    if "size" in user_sessions[user_id] and "position" in user_sessions[user_id]:
        await callback_query.answer("Watermarking video...")
        await process_watermark(user_id, file_path, user_sessions[user_id]["size"], user_sessions[user_id]["position"], callback_query.message)

# Process video with watermark using FFmpeg
async def process_watermark(user_id, input_video, size, position, message):
    output_vid = f"{WORKING_DIR}/watermarked_{user_id}.mp4"
    watermark_path = WATERMARK_PATH  # Path to your watermark image

    file_genertor_command = [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet", "-progress", WORKING_DIR, "-i", input_video, "-i", watermark_path,
        "-filter_complex", f"[1][0]scale2ref=w='iw*{size}/100':h='ow/mdar'[wm][vid];[vid][wm]overlay={position}",
        "-c:v", "copy", "-preset", "fast", "-crf", "0", "-c:a", "copy", output_vid
    ]

    print(f"Executing command: {' '.join(file_genertor_command)}")  # Debugging statement

    # Run the FFmpeg command
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    await process.communicate()

    if os.path.exists(output_vid):
        # Send the watermarked video to the user
        await message.reply_video(output_vid, caption="Here is your watermarked video!")

        # Clean up
        os.remove(input_video)
        os.remove(output_vid)
    else:
        await message.reply_text("An error occurred while processing the video. Please try again.")

    # Remove user session after processing
    user_sessions.pop(user_id, None)

# Start the bot
bot.run()
