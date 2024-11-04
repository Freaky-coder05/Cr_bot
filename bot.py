import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ForceReply
import ffmpeg

from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store user-specific data like mode and files
user_modes = {}
user_files = {}

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
    merge_video_audio_button = InlineKeyboardButton(
        f"Merge Video+Audio {'✅' if current_mode == 'Merge Video+Audio' else ''}", 
        callback_data="merge_video_audio"
    )
    
    await message.reply(
        "Choose an operation mode:",
        reply_markup=InlineKeyboardMarkup([[remove_audio_button, trim_video_button, merge_video_audio_button]])
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
    elif selected_mode == "merge_video_audio":
        user_modes[user_id] = "Merge Video+Audio"
    
    # Update the buttons to reflect the current mode
    remove_audio_button = InlineKeyboardButton(
        f"Remove Audio {'✅' if user_modes[user_id] == 'Remove Audio' else ''}", 
        callback_data="remove_audio"
    )
    trim_video_button = InlineKeyboardButton(
        f"Trim Video {'✅' if user_modes[user_id] == 'Trim Video' else ''}", 
        callback_data="trim_video"
    )
    merge_video_audio_button = InlineKeyboardButton(
        f"Merge Video+Audio {'✅' if user_modes[user_id] == 'Merge Video+Audio' else ''}", 
        callback_data="merge_video_audio"
    )
    
    new_markup = InlineKeyboardMarkup([[remove_audio_button, trim_video_button, merge_video_audio_button]])
    if callback_query.message.reply_markup != new_markup:
        await callback_query.message.edit_reply_markup(reply_markup=new_markup)
    else:
        await callback_query.answer("No changes made.")

# Handle incoming video or document files
@app.on_message(filters.video | filters.document & filters.incoming)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    # Download video and store path in user_files
    msg = await message.reply("Downloading video...")
    video_file = await message.download()
    user_files[user_id] = {"video": video_file, "message": message}
    
    # Process based on current mode
    if current_mode == "Remove Audio":
        await remove_audio(client, message)
    elif current_mode == "Trim Video":
        await trim_video(client, message)
    elif current_mode == "Merge Video+Audio":
        await message.reply("Now send an audio file to merge with the video.")

# Handle incoming audio files
@app.on_message(filters.audio | filters.voice)
async def handle_audio(client, message: Message):
    user_id = message.from_user.id
    
    if "video" in user_files.get(user_id, {}):
        msg = await message.reply("Downloading audio...")
        audio_file = await message.download()
        user_files[user_id]["audio"] = audio_file
        
        # Prompt user for the new name
        await message.reply("Please enter a new name for the merged video:", reply_markup=ForceReply())
    else:
        await message.reply("Please upload a video first, then send the audio to merge.")

# Handle the reply with the new name for the merged file
@app.on_message(filters.reply & filters.text)
async def handle_name_reply(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_files and "video" in user_files[user_id] and "audio" in user_files[user_id]:
        new_name = message.text
        await merge_video_audio(client, user_files[user_id]["message"], new_name)
    else:
        await message.reply("Please upload both video and audio files before setting a name.")

# Function to merge video and audio
async def merge_video_audio(client, message, new_name):
    user_id = message.from_user.id
    video_path = user_files[user_id]["video"]
    audio_path = user_files[user_id]["audio"]
    output_path = f"{new_name}.mp4"
    
    msg = await message.reply("Merging video and audio...")
    try:
        command = [
            'ffmpeg', '-y',  # Overwrite without asking
            '-i', video_path,  # Input video
            '-i', audio_path,  # Input audio
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'aac',  # Encode audio to AAC
            '-map', '0:v:0',  # Use first video stream from the input
            '-map', '1:a:0',  # Use audio from the new audio file
            output_path  # Output file
        ]
        
        # Execute the FFmpeg command
        await message.reply("Merging audio into video...")
        process = await asyncio.create_subprocess_exec(*command)
        await process.communicate()

        await msg.edit("Uploading merged video...")
        await message.reply_video(output_path)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)

# Function to remove audio from video
async def remove_audio(client, message):
    video_file = user_files[message.from_user.id]["video"]
    output_file = f"no_audio_{os.path.basename(video_file)}"
    
    msg = await message.reply("Removing audio...")
    try:
        ffmpeg.input(video_file).output(output_file, **{'an': None}).run(overwrite_output=True)
        await msg.edit("Uploading video without audio...")
        await message.reply_video(output_file)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(output_file)

# Function to trim video with default start and end times
async def trim_video(client, message):
    start_time = "00:00:10"
    end_time = "00:00:20"
    video_file = user_files[message.from_user.id]["video"]
    output_file = f"trimmed_{os.path.basename(video_file)}"
    
    msg = await message.reply("Trimming video...")
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
        "- **Trim Video**: Trims the video between specific start and end times (default: 10 to 20 seconds).\n"
        "- **Merge Video+Audio**: Merges a video with a new audio file.\n\n"
        "Once you've selected a mode, send a video to start!"
    )

app.run()
