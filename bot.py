import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ForceReply
import ffmpeg

from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store the current mode and file paths for each user
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
        f"Video+Audio Merger {'✅' if current_mode == 'Video+Audio Merger' else ''}", 
        callback_data="merge_video_audio"
    )
    
    await message.reply(
        "Choose an operation mode in this Button 🔘:",
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
        user_modes[user_id] = "Video+Audio Merger"
    
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
        f"Video+Audio Merger {'✅' if user_modes[user_id] == 'Video+Audio Merger' else ''}", 
        callback_data="merge_video_audio"
    )
    
    await callback_query.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([[remove_audio_button, trim_video_button, merge_video_audio_button]])
    )

# Handle video files for merging or other operations
@app.on_message(filters.video | filters.document & filters.incoming)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    if current_mode == "Remove Audio":
        await ask_for_name(client, message, "remove_audio")
    elif current_mode == "Trim Video":
        await ask_for_name(client, message, "trim_video")
    elif current_mode == "Video+Audio Merger":
        msg = await message.reply("Downloading your video file")
        video_file_path = await message.download()
        user_files[user_id] = {"video": video_file_path, "audio": None}
        await message.reply("Video received! Now, please send the audio file to merge.")

# Handle audio files for merging
@app.on_message(filters.audio | filters.document & filters.incoming)
async def handle_audio(client, message: Message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    if current_mode == "Video+Audio Merger":
        await message.reply("Downloading your audio file")
        audio_file_path = await message.download()
        
        if user_id in user_files and user_files[user_id].get("video"):
            user_files[user_id]["audio"] = audio_file_path
            await ask_for_name(client, message, "merge_video_audio")
        else:
            user_files[user_id] = {"video": None, "audio": audio_file_path}
            await message.reply("Audio received! Now, please send the video file to merge.")

# Ask user for new file name with force reply
async def ask_for_name(client, message, operation):
    user_id = message.from_user.id
    user_files[user_id] = {"operation": operation, "message": message}
    await message.reply("Please enter the new name for the output file:", reply_markup=ForceReply(selective=True))

# Handle user response with new name
@app.on_message(filters.reply & filters.text)
async def handle_name_reply(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_files and "operation" in user_files[user_id]:
        operation = user_files[user_id]["operation"]
        new_name = f"{message.text}.mp4"
        
        if operation == "remove_audio":
            await remove_audio(client, user_files[user_id]["message"], new_name)
        elif operation == "trim_video":
            await trim_video(client, user_files[user_id]["message"], new_name)
        elif operation == "merge_video_audio":
            await merge_video_audio(client, user_files[user_id]["message"], new_name)
        
        # Clear user files after operation
        user_files.pop(user_id)

# Remove audio function
async def remove_audio(client, message, output_name):
    msg = await message.reply("Downloading video...")
    video_file = await message.download()
    
    await msg.edit("Removing audio...")
    try:
        ffmpeg.input(video_file).output(output_name, an=None).run(overwrite_output=True)
        await msg.edit("Uploading video without audio...")
        await message.reply_video(output_name)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(output_name)

# Trim video function with default start and end time
async def trim_video(client, message, output_name):
    start_time = "00:00:10"
    end_time = "00:00:20"
    
    msg = await message.reply("Downloading video...")
    video_file = await message.download()
    
    await msg.edit("Trimming video...")
    try:
        ffmpeg.input(video_file, ss=start_time, to=end_time).output(output_name).run(overwrite_output=True)
        await msg.edit("Uploading trimmed video...")
        await message.reply_video(output_name)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(output_name)

# Merge video and audio function
async def merge_video_audio(client, message, output_name):
    user_id = message.from_user.id
    video_file = user_files[user_id]["video"]
    audio_file = user_files[user_id]["audio"]
    
    msg = await message.reply("Merging video with audio...")
    try:
        command = [
            'ffmpeg', '-y',  # Overwrite without asking
            '-i', video_file,  # Input video
            '-i', audio_file,  # Input audio
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-map', '0:v:0',  # Use first video stream from the input
            '-map', '1:a:0',  # Use audio from the new audio file
            output_name  # Output file
        ]
        
        # Run the FFmpeg command
        subprocess.run(command, check=True)
        await msg.edit("Uploading merged video...")
        await message.reply_video(output_name)
    except Exception as e:
        await msg.edit(f"Error: {e}")
    finally:
        os.remove(video_file)
        os.remove(audio_file)
        os.remove(output_name)

# Start command with instructions
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Hello! I'm an Audio Remover, Video Trimmer, & Video+Audio Merger Bot.\n\n"
        "Use /mode to select your operation:\n"
        "- **Remove Audio**: Removes audio from a video.\n"
        "- **Trim Video**: Trims the video between specific start and end times (default: 10 to 20 seconds).\n"
        "- **Video+Audio Merger**: Merges a video with a separate audio file.\n\n"
        "Once you've selected a mode, send the required files to start!"
    )

app.run()
