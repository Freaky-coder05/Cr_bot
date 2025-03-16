import os

API_ID = os.getenv("API_ID", "21740783")
API_HASH = os.getenv("API_HASH", "a5dc7fec8302615f5b441ec5e238cd46")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7116266807:AAGUjObnk3_UGeGbYqZCMpnBPziHs4g2_Us")
ADMINS = [6299192020]
# Directory to save and process files
SAVE_DIR = './downloads'

ARIA2_RPC_URL = os.getenv("ARIA2_RPC_URL", "http://localhost:8080/jsonrpc")  # Aria2 RPC URL
ARIA2_SECRET = os.getenv("ARIA2_SECRET", "YOUR_ARIA2_SECRET")  # Set your secret if needed
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")  # Folder to store downloads


# Default watermark settings (can be changed by sending a new image)
WATERMARK_PATH = "default_watermark.png"  # Default watermark image path
WATERMARK_SIZE = 0.1  # Adjust size as percentage of video width (default is 10%)
WATERMARK_TRANSPARENCY = 0.5  # Transparency level (0: fully transparent, 1: fully opaque)
WATERMARK_POSITION = "top-left"  # You can choose "top-right", "bottom-right", etc.



# Directory for storing temporary video files
WORKING_DIR = "downloads"  # Directory for saving downloaded and processed files

# AI model settings
MODEL_NAME = "facebook/bart-large-mnli"

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")  # Default location of FFmpeg

# config.py

# Crunchyroll Premium Credentials
CRUNCHYROLL_USER = 'http://segunblaksley@live.com'
CRUNCHYROLL_PASS = '123456789'
