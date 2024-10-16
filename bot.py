import os
import math
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BOT_TOKEN, API_ID, API_HASH  # Import from config.py

# Initialize the bot with your token, API ID, and API Hash
app = Client("my_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Directory to store incoming files temporarily
TEMP_DIR = 'temp_files'
os.makedirs(TEMP_DIR, exist_ok=True)


def merge_video_audio(video_path, audio_path, output_path):
    """Merges video with new audio, replacing the existing audio."""
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
    subprocess.run(command, check=True)

def progress_bar(current, total, length=10):
    """Generates a progress bar with the given length."""
    progress = math.floor(current / total * length)
    return f"{'⬡' * progress}{'⬠' * (length - progress)} {current * 100 // total}%"


async def download_file_with_progress(client, message: Message, destination):
    """Downloads a file and sends progress to the user."""
    total_size = message.document.file_size if message.document else message.video.file_size
    downloaded_size = 0

    async with client.download_media(message, file_name=destination, progress=lambda current, total: send_progress(message.chat.id, current, total)) as f:
        while downloaded_size < total_size:
            downloaded_size += len(await f.read(1024 * 1024))  # Read in chunks of 1MB

async def send_progress(chat_id, current, total):
    """Send progress updates to the user."""
    await app.send_message(chat_id, progress_bar(current, total))


async def upload_video_with_progress(client, chat_id, video_path):
    """Uploads the merged video with a progress indicator."""
    total_size = os.path.getsize(video_path)

    async def on_upload_progress(current, total):
        await app.send_message(chat_id, progress_bar(current, total))

    await client.send_video(chat_id, video_path, progress=on_upload_progress)

# Store the state of the chat for incoming files
user_files = {}

@app.on_message(filters.command('start'))
async def send_welcome(client, message):
    await message.reply("Welcome! Send me a video or document-type video, followed by an audio file to replace the original audio.")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    chat_id = message.chat.id

    # Handle both video and document video uploads
    if message.video:
        video_file = message.video
        extension = ".mp4"
    elif message.document.mime_type.startswith('video/'):
        video_file = message.document
        extension = os.path.splitext(video_file.file_name)[1]
    else:
        await message.reply("Please send a valid video file.")
        return

    video_path = os.path.join(TEMP_DIR, video_file.file_id + extension)

    # Download the video file with progress
    await message.reply("Downloading video...")
    await download_file_with_progress(client, message, video_path)

    user_files[chat_id] = {'video': video_path}
    await message.reply("Video received! Now, send the audio file.")

@app.on_message(filters.audio | filters.voice)
async def handle_audio(client, message: Message):
    chat_id = message.chat.id

    # Check if the user already sent a video
    if chat_id not in user_files or 'video' not in user_files[chat_id]:
        await message.reply("Please send a video first.")
        return

    # Handle audio and voice files
    audio_file = message.audio if message.audio else message.voice
    audio_extension = os.path.splitext(audio_file.file_name)[1] or ".mp3"
    audio_path = os.path.join(TEMP_DIR, audio_file.file_id + audio_extension)

    # Download the audio file with progress
    await message.reply("Downloading audio...")
    await download_file_with_progress(client, message, audio_path)

    # Save paths in user_files for merging after filename input
    user_files[chat_id]['audio'] = audio_path
    await message.reply("Audio received! Now, reply with the new filename (without extension).")

@app.on_message(filters.text & filters.user(user_files.keys()))
async def handle_filename(client, message: Message):
    chat_id = message.chat.id
    new_filename = message.text.strip()

    if not new_filename:
        await message.reply("Invalid filename. Please send a valid name.")
        return

    # Create the full output path with the new filename
    output_path = os.path.join(TEMP_DIR, f"{new_filename}.mp4")

    try:
        # Merge the video with the new audio
        await message.reply("Merging audio and video...")
        merge_video_audio(user_files[chat_id]['video'], user_files[chat_id]['audio'], output_path)

        # Upload the merged video with progress
        await message.reply("Uploading merged video...")
        await upload_video_with_progress(client, chat_id, output_path)

        # Cleanup temporary files
        os.remove(user_files[chat_id]['video'])
        os.remove(user_files[chat_id]['audio'])
        os.remove(output_path)
        del user_files[chat_id]

    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
