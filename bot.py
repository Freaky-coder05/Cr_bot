import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import ffmpeg

from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store the current mode of each user
user_modes = {}
user_files = {}

# /mode command to select operation mode
@app.on_message(filters.command("mode"))
async def select_mode(client, message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Video + Audio Merge")
    
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
        f"Video + Audio Merge {'✅' if current_mode == 'Video + Audio Merge' else ''}", 
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
    user_modes[user_id] = selected_mode.replace("_", " ").title()
    
    # Update the buttons to reflect the current mode
    await select_mode(client, callback_query.message)

# Automatic operation based on selected mode when a video or audio file is sent
@app.on_message(filters.video | filters.document | filters.audio & filters.incoming)
async def handle_media(client, message: Message):
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id, "Remove Audio")
    
    if current_mode == "Remove Audio":
        await merge_video(client, message)
    elif current_mode == "Trim Video":
        await trim_video(client, message)
    elif current_mode == "Video + Audio Merge":
        await merge_video_audio(client, message)

# Function to merge video and audio
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

# Video + Audio Merge function
async def merge_video_audio(client, message):
    user_id = message.from_user.id

    # Store the video and audio files for merging
    if message.video:
        user_files[user_id] = {"video": await message.download()}
        await message.reply("Video downloaded. Now send the audio file to merge.")
    elif message.audio:
        if user_id in user_files and "video" in user_files[user_id]:
            video_file = user_files[user_id]["video"]
            audio_file = await message.download()
            output_file = f"merged_{os.path.basename(video_file)}"
            
            await message.reply("Merging video and audio...")
            try:
                ffmpeg.input(video_file).input(audio_file).output(output_file).run(overwrite_output=True)
                await message.reply_video(output_file)
            except Exception as e:
                await message.reply(f"Error: {e}")
            finally:
                os.remove(video_file)
                os.remove(audio_file)
                os.remove(output_file)
                del user_files[user_id]  # Clear user files after merging

# Start command with instructions
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Hello! I'm an Audio Remover & Video Trimmer Bot.\n\n"
        "Use /mode to select your operation:\n"
        "- **Remove Audio**: Removes audio from a video.\n"
        "- **Trim Video**: Trims the video between specific start and end times (default: 10 to 20 seconds).\n"
        "- **Video + Audio Merge**: Merges a video file with an audio file.\n\n"
        "Once you've selected a mode, send a video or audio file to start!"
    )

app.run()
