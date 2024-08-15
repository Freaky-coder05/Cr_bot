import os
import asyncio
import subprocess
from flask import Flask, request, jsonify
from pyrogram import Client, filters
from pyrogram.types import Message
from transformers import pipeline
from config import API_ID, API_HASH, BOT_TOKEN, SAVE_DIR, FFMPEG_PATH, MODEL_NAME

# Initialize Flask app
app_flask = Flask(__name__)

# Initialize your AI model for error handling
error_classifier = pipeline("zero-shot-classification", model=MODEL_NAME)

# Initialize Pyrogram client
app_telegram = Client("video_audio_sync_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Ensure the directory exists
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Function to process video and audio files using FFmpeg
async def sync_video_audio(video_path, audio_path, output_path):
    command = [
        FFMPEG_PATH,
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest', 
        output_path
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    # Check for errors using AI-based classification
    error_labels = ["error", "failure", "delay", "mismatch"]
    error_result = error_classifier(stderr.decode(), error_labels)

    if process.returncode != 0 or error_result['labels'][0] in error_labels:
        raise Exception(f"FFmpeg error: {stderr.decode()}")

    return output_path

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    start_message = (
        "👋 Welcome to the Video+Audio Synchronizer Bot!\n\n"
        "You can use this bot to synchronize video and audio files easily.\n"
        "Just send the command:\n"
        "`/sync <video_path> <audio_path>`\n\n"
        "If you need help or encounter any issues, feel free to reach out."
    )
    await message.reply(start_message)

@app.on_message(filters.command("sync"))
async def sync_handler(client: Client, message: Message):
    if len(message.command) < 3:
        await message.reply("Please send the command with both video and audio file paths.\nUsage: /sync <video_path> <audio_path>")
        return
    
    video_path = message.command[1]
    audio_path = message.command[2]
    
    # Generate output file path
    output_path = os.path.join(SAVE_DIR, f"output_{os.path.basename(video_path)}")

    try:
        # Call the FFmpeg process
        await message.reply("Synchronizing video and audio. Please wait...")
        output_file = await sync_video_audio(video_path, audio_path, output_path)
        await message.reply_document(output_file, caption="Here is your synchronized video.")
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")

@app_flask.route('/sync', methods=['POST'])
def sync_via_web():
    try:
        video_path = request.json.get('video_path')
        audio_path = request.json.get('audio_path')

        if not video_path or not audio_path:
            return jsonify({"error": "Please provide both video_path and audio_path in the request"}), 400
        
        output_path = os.path.join(SAVE_DIR, f"output_{os.path.basename(video_path)}")

        # Run the FFmpeg command asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        output_file = loop.run_until_complete(sync_video_audio(video_path, audio_path, output_path))

        return jsonify({"message": "Synchronization complete", "output_file": output_file}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
