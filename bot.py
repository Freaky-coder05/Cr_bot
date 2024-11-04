import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import ffmpeg

from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store the current mode of each user
user_modes = {}

# /mode command to select operation mode
@app.on_message(filters.command("mode"))
async def select_mode(client, message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    # Create buttons with the current mode indicated by ✅
    remove_audio_button = InlineKeyboardButton(
        f"Remove Audio {'✅' if current_mode == 'Remove Audio' else ''}", 
        callback_data="remove_audio"
    )
    trim_video_button = InlineKeyboardButton(
        f"Trim Video {'✅' if current_mode == 'Trim Video' else ''}", 
        callback_data="trim_video"
    )
    
    await message.reply(
        "Choose an operation mode:",
        reply_markup=InlineKeyboardMarkup([[remove_audio_button, trim_video_button]])
    )

# Handle button clicks for mode selection
@app.on_callback_query()
async def mode_callback(client, callback_query):
    user_id = callback_query.from_user.id
    selected_mode = callback_query.data
    
    # Set the user mode based on button click
    if selected_mode == "remove_audio":
        user_modes[user_id] = "Remove Audio"
    elif selected_mode == "trim_video":
        user_modes[user_id] = "Trim Video"
    
    # Update the buttons to reflect the current mode
    remove_audio_button = InlineKeyboardButton(
        f"Remove Audio {'✅' if user_modes[user_id] == 'Remove Audio' else ''}", 
        callback_data="remove_audio"
    )
    trim_video_button = InlineKeyboardButton(
        f"Trim Video {'✅' if user_modes[user_id] == 'Trim Video' else ''}", 
        callback_data="trim_video"
    )
    
    await callback_query.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[remove_audio_button, trim_video_button]])
    )

# Automatic operation based on selected mode when a video is sent
@app.on_message(filters.video | filters.document & filters.incoming)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    if current_mode == "Remove Audio":
        await remove_audio(client, message)
    elif current_mode == "Trim Video":
        await trim_video(client, message)

# Remove audio function
async def remove_audio(client, message):
    msg = await message.reply("Downloading video...")
    video_file = await message.download()
    
    output_file = f"no_audio_{os.path.basename(video_file)}"
    
    await msg.edit("Removing audio...")
    try:
        ffmpeg.input(video_file).output(output_file, acodec="none").run(overwrite_output=True)
        await msg.edit("Uploading video without audio...")
        await message.reply_video(output_file)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(output_file)

# Trim video function with default start and end time
async def trim_video(client, message):
    start_time = "00:00:10"
    end_time = "00:00:20"
    
    msg = await message.reply("Downloading video...")
    video_file = await message.download()
    
    output_file = f"trimmed_{os.path.basename(video_file)}"
    
    await msg.edit("Trimming video...")
    try:
        ffmpeg.input(video_file, ss=start_time, to=end_time).output(output_file).run(overwrite_output=True)
        await msg.edit("Uploading trimmed video...")
        await message.reply_video(output_file)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(output_file)

# Start command with instructions
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Hello! I'm an Audio Remover & Video Trimmer Bot.\n\n"
        "Use /mode to select your operation:\n"
        "- **Remove Audio**: Removes audio from a video.\n"
        "- **Trim Video**: Trims the video between specific start and end times (default: 10 to 20 seconds).\n\n"
        "Once you've selected a mode, send a video to start!"
    )

app.run()
