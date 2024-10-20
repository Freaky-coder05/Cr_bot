import os
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN
import math
import logging

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Enable logging to troubleshoot
logging.basicConfig(level=logging.INFO)

# Global variable for storing watermark image path
WATERMARK_IMAGE = None

# Dictionary to store the conversation state for each user
user_conversations = {}

# Set watermark image by replying to an image
@app.on_message(filters.command("set_image") & filters.reply)
async def set_watermark_image(client, message):
    logging.info("Command received: /set_image")

    # Check if the replied message contains a photo
    if message.reply_to_message and message.reply_to_message.photo:
        logging.info(f"Received image: {message.reply_to_message.photo}")
        
        # Download the watermark image
        try:
            watermark_img_path = await client.download_media(
                message.reply_to_message.photo.file_id, file_name="watermark.png"
            )
            logging.info(f"Watermark image downloaded to: {watermark_img_path}")
            
            global WATERMARK_IMAGE
            WATERMARK_IMAGE = watermark_img_path
            
            await message.reply_text("Watermark image set successfully.")
        except Exception as e:
            logging.error(f"Error downloading image: {e}")
            await message.reply_text("Failed to set watermark image.")
    else:
        logging.warning("No photo found in the replied message.")
        await message.reply_text("Please reply to a valid image with the /set_image command.")

async def progress_bar(current, total, message):
    percent = current * 100 / total
    filled = math.floor(percent / 10)
    bar = "█" * filled + "-" * (10 - filled)
    await message.edit_text(f"Progress: [{bar}] {percent:.2f}%")

# Start message
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "Welcome to the Watermark Bot!\nSend me a video file to add a watermark.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Help", callback_data="help")]]
        ),
    )

# Handle video files for watermarking
@app.on_message(filters.video)
async def add_watermark(client, message):
    video = message.video

    # Ensure watermark image exists
    if not os.path.exists(WATERMARK_IMAGE):
        await message.reply_text("No watermark image set. Please set one using /set_image.")
        return
    
    # Ask for watermark position, transparency, and size
    await message.reply_text(
        "Please enter the watermark position, size, and transparency.\n"
        "Format: `x_offset:y_offset:scale:transparency`\n"
        "Example: `10:10:0.5:0.7`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Default", callback_data="default_settings")]])
    )
    
    # Store the user's chat ID and the video file ID in the conversation state
    user_conversations[message.chat.id] = {
        "state": "awaiting_input",
        "video_file_id": message.video.file_id  # Store the video file ID
    }

# Handle user input for watermark settings
@app.on_message(filters.text & filters.incoming)
async def handle_user_input(client, message):
    user_data = user_conversations.get(message.chat.id)

    if user_data and user_data.get("state") == "awaiting_input":
        try:
            # Process user input
            x_offset, y_offset, scale, transparency = map(float, message.text.split(":"))
            
            # Reset the conversation state
            user_conversations[message.chat.id]["state"] = None
            
            # Retrieve the stored video file ID
            video_file_id = user_data.get("video_file_id")
            
            # Proceed with the watermarking process
            await message.reply_text(f"Watermark settings received: {x_offset}, {y_offset}, {scale}, {transparency}.")
            
            # Continue with the video processing
            await process_video(client, message, video_file_id, x_offset, y_offset, scale, transparency)

        except ValueError:
            await message.reply_text("Invalid input format. Please try again.")

async def process_video(client, message, video_file_id, x_offset, y_offset, scale, transparency):
    # Download the video
    download_msg = await message.reply_text("Downloading video...")
    video_path = await client.download_media(video_file_id, progress=progress_bar, progress_args=(message,))

    # Prepare output path
    output_video = f"watermarked_{video_file_id}.mp4"

    # Add watermark using FFmpeg with transparency, size, and position
    try:
        watermark_msg = await message.reply_text("Adding watermark...")
        
        # Run FFmpeg command and track progress
        process = (
            ffmpeg
            .input(video_path)  # First input: the video
            .input(WATERMARK_IMAGE)  # Second input: the watermark image
            .filter_complex(f"[1]format=rgba,colorchannelmixer=aa={transparency}[wm];[0][wm]overlay={x_offset}:{y_offset}")
            .output(output_video, vf=f"scale=iw*{scale}:ih*{scale}", preset="veryfast", threads=4)
            .global_args('-progress', 'pipe:1', '-nostats')  # Get progress via pipe
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        
        total_duration = 100  # Placeholder for actual video duration
        current_duration = 0
        
        while process.poll() is None:
            output = process.stdout.readline().decode('utf-8')
            
            if "out_time_ms" in output:
                time_ms = int(output.split('=')[1].strip())
                current_duration = time_ms / 1_000_000  # Convert to seconds
                
                # Calculate progress percentage
                progress_percentage = (current_duration / total_duration) * 100
                time_left = total_duration - current_duration
                
                # Update progress
                await watermark_msg.edit_text(
                    f"Encoding in Progress...\n"
                    f"Time Left: {int(time_left // 60)}m, {int(time_left % 60)}s\n"
                    f"Progress: {int(progress_percentage)}%\n"
                    f"[{'█' * int(progress_percentage // 5)}{' ' * (20 - int(progress_percentage // 5))}]"
                )
                
        # Wait for the process to complete
        await process.communicate()

        # Send the watermarked video back
        await client.send_video(
            message.chat.id,
            output_video,
            caption="Here's your watermarked video!",
            progress=progress_bar,
            progress_args=(message,)
        )
        
        # Progress 100%, upload the video
        await watermark_msg.edit_text(f"Watermarking complete. Uploading...")

    except Exception as e:
        await message.reply_text(f"Error adding watermark: {e}")
    finally:
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_video):
            os.remove(output_video)

    await download_msg.delete()

# Inline keyboard for help
@app.on_callback_query(filters.regex("help"))
async def help_message(client, callback_query):
    await callback_query.message.edit_text(
        "Send me a video file, and I'll add a watermark to it. You can customize the watermark position, size, transparency, etc."
    )

# Default settings for the watermark
@app.on_callback_query(filters.regex("default_settings"))
async def default_watermark_settings(client, callback_query):
    # Default position, scale, transparency
    x_offset, y_offset, scale, transparency = 10, 10, 1.0, 1.0

    await callback_query.message.reply_text(f"Using default settings: {x_offset}:{y_offset}:{scale}:{transparency}")

app.run()
