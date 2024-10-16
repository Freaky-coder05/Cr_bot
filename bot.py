import telebot
import subprocess
import os
import math
from config import BOT_TOKEN  # Import BOT_TOKEN from config.py

# Initialize the bot with your token
bot = telebot.TeleBot(BOT_TOKEN)

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

def download_file_with_progress(file_path, destination, chat_id):
    """Downloads a file and sends progress to the user."""
    downloaded_size = 0
    total_size = bot.get_file(file_path).file_size

    with open(destination, 'wb') as f:
        for chunk in bot.download_file(file_path, as_chunk=True):
            f.write(chunk)
            downloaded_size += len(chunk)
            bot.send_message(chat_id, progress_bar(downloaded_size, total_size))

def upload_video_with_progress(chat_id, video_path):
    """Uploads the merged video with a progress indicator."""
    total_size = os.path.getsize(video_path)
    uploaded_size = 0

    def on_upload_progress(sent_bytes, total_bytes):
        nonlocal uploaded_size
        uploaded_size = sent_bytes
        bot.send_message(chat_id, progress_bar(uploaded_size, total_size))

    with open(video_path, 'rb') as video:
        bot.send_video(chat_id, video, progress_callback=on_upload_progress)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me a video or document-type video, followed by an audio file to replace the original audio.")

# Store the state of the chat for incoming files
user_files = {}

@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    chat_id = message.chat.id

    # Handle both video and document video uploads
    if message.content_type == 'video':
        video_file = bot.get_file(message.video.file_id)
        extension = ".mp4"
    elif message.document.mime_type.startswith('video/'):
        video_file = bot.get_file(message.document.file_id)
        extension = os.path.splitext(message.document.file_name)[1]
    else:
        bot.reply_to(message, "Please send a valid video file.")
        return

    video_path = os.path.join(TEMP_DIR, video_file.file_id + extension)

    # Download the video file with progress
    bot.reply_to(message, "Downloading video...")
    download_file_with_progress(video_file.file_path, video_path, chat_id)

    user_files[chat_id] = {'video': video_path}
    bot.reply_to(message, "Video received! Now, send the audio file.")

@bot.message_handler(content_types=['audio', 'voice'])
def handle_audio(message):
    chat_id = message.chat.id

    # Check if the user already sent a video
    if chat_id not in user_files or 'video' not in user_files[chat_id]:
        bot.reply_to(message, "Please send a video first.")
        return

    # Handle audio and voice files
    audio_file = bot.get_file(message.audio.file_id if message.content_type == 'audio' else message.voice.file_id)
    audio_extension = os.path.splitext(audio_file.file_path)[1] or ".mp3"
    audio_path = os.path.join(TEMP_DIR, audio_file.file_id + audio_extension)

    # Download the audio file with progress
    bot.reply_to(message, "Downloading audio...")
    download_file_with_progress(audio_file.file_path, audio_path, chat_id)

    # Save paths in user_files for merging after filename input
    user_files[chat_id]['audio'] = audio_path
    bot.reply_to(message, "Audio received! Now, reply with the new filename (without extension).")

@bot.message_handler(func=lambda message: message.chat.id in user_files and 'audio' in user_files[message.chat.id])
def handle_filename(message):
    chat_id = message.chat.id
    new_filename = message.text.strip()

    if not new_filename:
        bot.reply_to(message, "Invalid filename. Please send a valid name.")
        return

    # Create the full output path with the new filename
    output_path = os.path.join(TEMP_DIR, f"{new_filename}.mp4")

    try:
        # Merge the video with the new audio
        bot.reply_to(message, "Merging audio and video...")
        merge_video_audio(user_files[chat_id]['video'], user_files[chat_id]['audio'], output_path)

        # Upload the merged video with progress
        bot.reply_to(message, "Uploading merged video...")
        upload_video_with_progress(chat_id, output_path)

        # Cleanup temporary files
        os.remove(user_files[chat_id]['video'])
        os.remove(user_files[chat_id]['audio'])
        os.remove(output_path)
        del user_files[chat_id]

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.run()
