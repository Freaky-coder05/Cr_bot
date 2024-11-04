from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import os
import subprocess

from config import API_ID, API_HASH, BOT_TOKEN  # Ensure you have your API ID, API HASH, and BOT TOKEN in config.py


app = Client("video_audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# Global variable to store user mode selection
user_modes = {}

# Function to remove audio from a video
def remove_audio(input_file, output_file):
    command = f"ffmpeg -i {input_file} -an {output_file}"
    subprocess.run(command, shell=True)

# Function to trim video
def trim_video(input_file, start_time, end_time, output_file):
    command = f"ffmpeg -i {input_file} -ss {start_time} -to {end_time} -c copy {output_file}"
    subprocess.run(command, shell=True)

# Command to set mode
@app.on_message(filters.command("mode"))
async def set_mode(client, message: Message):
    user_id = message.from_user.id

    # Inline keyboard with modes
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Audio Remover" + (" ✅" if user_modes.get(user_id) == "Audio Remover" else ""), callback_data="set_audio_remover")],
        [InlineKeyboardButton("Video Trimmer" + (" ✅" if user_modes.get(user_id) == "Video Trimmer" else ""), callback_data="set_video_trimmer")]
    ])
    await message.reply_text("Select an operation mode:", reply_markup=keyboard)

# Callback query to set the operation mode
@app.on_callback_query(filters.regex(r"set_"))
async def mode_selection(client, callback_query):
    user_id = callback_query.from_user.id
    mode = callback_query.data.split("_")[1]

    # Initialize new_mode with the current mode or an empty string
    new_mode = user_modes.get(user_id, "")

    # Determine the new mode based on the button clicked
    if mode == "audio_remover":
        new_mode = "Audio Remover"
    elif mode == "video_trimmer":
        new_mode = "Video Trimmer"

    # Only proceed if the selected mode is different from the current mode
    if user_modes.get(user_id) != new_mode:
        user_modes[user_id] = new_mode

        # Update the mode selection buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Audio Remover" + (" ✅" if user_modes.get(user_id) == "Audio Remover" else ""), callback_data="set_audio_remover")],
            [InlineKeyboardButton("Video Trimmer" + (" ✅" if user_modes.get(user_id) == "Video Trimmer" else ""), callback_data="set_video_trimmer")]
        ])
        
        # Edit the message only if there is a change
        await callback_query.message.edit_text("Select an operation mode:", reply_markup=keyboard)
    else:
        # If mode has not changed, show a small alert without editing the message
        await callback_query.answer("This mode is already selected.", show_alert=False)


# Handle video files based on the selected mode
@app.on_message(filters.video & filters.private)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    mode = user_modes.get(user_id, None)

    if not mode:
        await message.reply_text("Please set a mode first using /mode.")
        return

    video = message.video
    input_file = await client.download_media(video)

    if mode == "Audio Remover":
        output_file = "no_audio_" + os.path.basename(input_file)
        await message.reply_text("Removing audio from video...")
        remove_audio(input_file, output_file)
        await message.reply_text("Uploading video without audio...")
        await message.reply_video(output_file)

    elif mode == "Video Trimmer":
        await message.reply_text(
            "Please provide the start and end time in seconds in this format:\n\n`/set_time start end`\n\nFor example: `/set_time 10 50`"
        )
        # Store file temporarily for trimming after getting time
        user_modes[user_id] = {"mode": "Video Trimmer", "file": input_file}

    # Clean up
    if mode == "Audio Remover":
        os.remove(input_file)
        os.remove(output_file)

# Set trimming start and end times
@app.on_message(filters.command("set_time"))
async def set_time(client, message: Message):
    user_id = message.from_user.id
    if isinstance(user_modes.get(user_id), dict) and user_modes[user_id].get("mode") == "Video Trimmer":
        try:
            _, start_time, end_time = message.text.split()
            input_file = user_modes[user_id]["file"]
            output_file = "trimmed_" + os.path.basename(input_file)
            await message.reply_text(f"Trimming video from {start_time}s to {end_time}s...")
            trim_video(input_file, start_time, end_time, output_file)
            await message.reply_text("Uploading trimmed video...")
            await message.reply_video(output_file)

            # Clean up
            os.remove(input_file)
            os.remove(output_file)
            user_modes[user_id] = "Video Trimmer"  # Reset mode to indicate trimming is done
        except ValueError:
            await message.reply_text("Invalid format. Please provide times like this: `/set_time start end`")
    else:
        await message.reply_text("Please send a video file and set the mode to Video Trimmer.")

if __name__ == "__main__":
    app.run()
