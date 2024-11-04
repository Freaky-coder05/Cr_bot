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
        await merge_video(client, message)
    elif current_mode == "Trim Video":
        await trim_video(client, message)

async def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    # FFmpeg command to replace existing audio with new audio
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
    
    # Run the command
    subprocess.run(command)

async def merge_video(client: Client, message: Message):
    # Download video file
    video_path = await client.download_media(message)
    await message.reply("Video received! Now send an audio file to merge.")

    # Wait for the audio file
    audio_message = await client.listen(message.chat.id)

    if audio_message.audio or audio_message.document:
        audio_path = await client.download_media(audio_message)

        # Ask for a new file name
        await message.reply("Please send the new file name (without extension) for the merged file.")
        
        # Listen for the new file name
        name_message = await client.listen(message.chat.id)
        new_file_name = name_message.text.strip()  # Get the file name from the user's message

        # Create output file path
        output_path = f"{new_file_name}.mp4"  # Set output file with .mp4 extension

        await message.reply("Merging video and audio...")

        # Merge video and audio
        await merge_video_audio(video_path, audio_path, output_path)

        await message.reply_document(output_path)

        # Clean up files
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)

    else:
        await message.reply("Please send a valid audio file.")

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
