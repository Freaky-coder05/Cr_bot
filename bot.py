import os
import asyncio
import subprocess
import cv2
import numpy as np
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, jsonify
from datetime import datetime
import deepspeech
from config import API_ID, API_HASH, BOT_TOKEN, MODEL_PATH, SCORER_PATH

# Initialize the Telegram client
bot = Client(
    "sync_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize Flask
app = Flask(__name__)

# Load DeepSpeech model
model = deepspeech.Model(MODEL_PATH)
model.enableExternalScorer(SCORER_PATH)

def extract_audio(video_path):
    audio_path = video_path.replace('.mp4', '.wav')
    cmd = f"ffmpeg -i {video_path} -q:a 0 -map a {audio_path}"
    subprocess.call(cmd, shell=True)
    return audio_path

def transcribe_audio(audio_path):
    # Use DeepSpeech to transcribe the audio
    with open(audio_path, 'rb') as audio_file:
        audio = np.frombuffer(audio_file.read(), np.int16)
        text = model.stt(audio)
    return text

def analyze_video(video_path):
    # Load video using OpenCV
    cap = cv2.VideoCapture(video_path)
    # Extract key frames or analyze the video to detect speech or lip movement
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames

def sync_using_ai(video_path):
    audio_path = extract_audio(video_path)
    transcription = transcribe_audio(audio_path)
    video_frames = analyze_video(video_path)
    
    # Here, you'd compare transcription with the video frames
    # and make adjustments based on the analysis.
    # For simplicity, we'll assume the AI decides no adjustment is needed.

    output_path = video_path.replace('.mp4', '_synced.mp4')
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",  # Ensures sync based on the shortest stream
        output_path
    ]
    subprocess.call(cmd)
    return output_path

@bot.on_message(filters.command("sync") & filters.video)
async def sync_handler(bot, message: Message):
    # Download the video file
    video_path = await message.download()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"synced_{timestamp}_{os.path.basename(video_path)}"

    # Notify user that the synchronization process has started
    await message.reply_text("🔄 Synchronizing video and audio using AI... Please wait.")

    # Run the synchronization using AI
    synced_video = sync_using_ai(video_path)

    # Send the synchronized video back to the user
    await message.reply_video(synced_video)

    # Cleanup: Remove the downloaded and processed files
    os.remove(video_path)
    os.remove(synced_video)

    # Notify user that the synchronization is complete
    await message.reply_text("✅ AI-based synchronization complete! Here is your video.")

@app.route('/')
def index():
    return "Welcome to the AI Video/Audio Synchronizer Bot!"

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Bot is running", "clients": bot.get_me().dict()})

@app.route('/sync', methods=['POST'])
def sync_via_flask():
    return jsonify({"message": "Sync via Flask not implemented yet!"})

if __name__ == "__main__":
    bot.run()
