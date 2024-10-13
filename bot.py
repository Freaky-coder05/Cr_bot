import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN
import re

# Create your bot using your token from config
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to hold user watermark settings
user_watermarks = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hi, I am a watermark adder bot ☘️")

# Valid predefined positions and their corresponding x:y coordinates
POSITIONS = {
    "top-left": "10:10",
    "top-right": "main_w-overlay_w-10:10",
    "bottom-left": "10:main_h-overlay_h-10",
    "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
}

async def get_video_duration(video_path):
    """Get the total duration of the video using FFmpeg."""
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error retrieving video duration: {e}")
        return None

def generate_progress_bar(progress, total_bars=20, symbol="⬢"):
    """Generate a progress bar with the given symbol."""
    filled_length = int(total_bars * progress / 100)
    empty_length = total_bars - filled_length
    return symbol * filled_length + " " * empty_length


                                    float(current_time_parts[2]))          # seconds

                    # Calculate progress percentage
                    progress = (current_time / total_duration) * 100

                    # Generate visual progress bar using symbols
                    progress_bar = generate_progress_bar(progress)

                    await message.edit(f"Adding watermark... {progress:.2f}%\n{progress_bar}")

            if process.returncode is not None:
                break

async def add_watermark(video_path, user_id, message):
    # Fetch user-specific watermark settings or use defaults
    watermark_text = user_watermarks.get(user_id, {}).get('text', 'Anime_Warrior_Tamil')  # Default watermark text
    position = user_watermarks.get(user_id, {}).get('position', "top-left")  # Default position
    position_xy = POSITIONS.get(position, "10:10")
    width = user_watermarks.get(user_id, {}).get('width', 15)  # Default width in pixels
    opacity = user_watermarks.get(user_id, {}).get('opacity', 0.5)  # Default opacity

    output_path = f"watermarked_{os.path.basename(video_path)}"

    # Get total duration of the video for progress calculation
    total_duration = await get_video_duration(video_path)
    if total_duration is None:
        await message.edit("❌ Failed to get video duration.")
        return None

    try:
        # Get original video bitrate to maintain output size
        original_bitrate = await get_video_bitrate(video_path)

        # Run FFmpeg command to add text watermark and limit output bitrate
        command = [
            'ffmpeg', '-hwaccel', 'auto', '-i', video_path,
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize={width}:x={position_xy.split(':')[0]}:y={position_xy.split(':')[1]}:alpha={opacity}",
            '-c:v', 'libx264', '-b:v', original_bitrate, '-preset', 'fast',
            '-c:a', 'copy', output_path
        ]

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Track progress using stderr output
        while True:
            stderr_line = await process.stderr.readline()
            if stderr_line:
                stderr_line = stderr_line.decode('utf-8').strip()

                # Parse the current time from FFmpeg output
                time_match = re.search(r"time=(\d+:\d+:\d+\.\d+)", stderr_line)
                if time_match:
                    current_time_str = time_match.group(1)
                    current_time_parts = current_time_str.split(":")
                    current_time = (float(current_time_parts[0]) * 3600 +  # hours
                                    float(current_time_parts[1]) * 60 +    # minutes
                                    float(current_time_parts[2]))          # seconds

                    # Calculate progress percentage
                    progress = (current_time / total_duration) * 100

                    # Generate visual progress bar using symbols
                    progress_bar = generate_progress_bar(progress)

                    await message.edit(f"Adding watermark... {progress:.2f}%\n{progress_bar}")

            if process.returncode is not None:
                break

        await process.wait()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr_line}")

        return output_path

    except Exception as e:
        print(f"Error adding watermark: {e}")
        return None

async def get_video_bitrate(video_path):
    try:
        # Run FFmpeg to get video file information
        command = [
            'ffmpeg', '-i', video_path, '-f', 'null', '-'
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        # Capture output
        stdout, stderr = await process.communicate()
        
        # Convert stderr to string for parsing
        stderr = stderr.decode('utf-8')
        
        # Look for bitrate in FFmpeg output (in kb/s)
        bitrate_match = re.search(r'bitrate: (\d+) kb/s', stderr)
        if bitrate_match:
            bitrate_kbps = bitrate_match.group(1)
            # Convert kbps to bps for FFmpeg command
            return f"{bitrate_kbps}k"
        else:
            return None

    except Exception as e:
        print(f"Error getting video bitrate: {e}")
        return None

# Command to edit watermark settings
@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message):
    user_id = message.from_user.id

    # Create inline buttons for adjusting watermark position, size, and transparency
    buttons = [
        [
            InlineKeyboardButton("Top-Left", callback_data="pos_top_left"),
            InlineKeyboardButton("Top-Right", callback_data="pos_top_right")
        ],
        [
            InlineKeyboardButton("Bottom-Left", callback_data="set_width"),
            InlineKeyboardButton("Bottom-Right", callback_data="set_opacity")
        ],
        [InlineKeyboardButton("Center", callback_data="pos_center")]
    ]

    await message.reply_text("Select watermark position:", reply_markup=InlineKeyboardMarkup(buttons))

# Callback for editing watermark settings
@app.on_callback_query(filters.regex("^pos_"))
async def change_watermark_position(client, callback_query):
    position = callback_query.data.split("_")[1].replace("-", "_")
    user_id = callback_query.from_user.id

    if user_id in user_watermarks:
        user_watermarks[user_id]['position'] = position
    else:
        user_watermarks[user_id] = {'position': position}

    await callback_query.answer(f"Watermark position updated to {position.replace('_', ' ').title()} ✅")

@app.on_callback_query(filters.regex("set_width|set_opacity"))
async def on_callback_query(client, callback_query):
    setting = callback_query.data

    if setting == "set_width":
        width_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("50 px", callback_data="width_50"),
             InlineKeyboardButton("100 px", callback_data="width_100")],
            [InlineKeyboardButton("150 px", callback_data="width_150"),
             InlineKeyboardButton("200 px", callback_data="width_200")]
        ])
        await callback_query.message.edit_text("Choose watermark width:", reply_markup=width_keyboard)

    elif setting == "set_opacity":
        opacity_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.2", callback_data="opacity_0.2"),
             InlineKeyboardButton("0.5", callback_data="opacity_0.5")],
            [InlineKeyboardButton("0.8", callback_data="opacity_0.8"),
             InlineKeyboardButton("1.0", callback_data="opacity_1.0")]
        ])
        await callback_query.message.edit_text("Choose watermark opacity:", reply_markup=opacity_keyboard)

# Handle watermark position, width, and opacity changes
@app.on_callback_query(filters.regex("width_|opacity_"))
async def adjust_watermark_settings(client, callback_query):
    user_id = callback_query.from_user.id
    setting = callback_query.data

    if "width_" in setting:
        width = int(setting.split("_")[1])
        user_watermarks[user_id]['width'] = width
        await callback_query.message.edit_text(f"Watermark width set to {width} px")
    elif "opacity_" in setting:
        opacity = float(setting.split("_")[1])
        user_watermarks[user_id]['opacity'] = opacity
        await callback_query.message.edit_text(f"Watermark opacity set to {opacity}")

# Handling video or document uploads to add watermark
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    download_message = await message.reply("Downloading video...")
    video_path = await message.download()
    
    watermarked_video_path = await add_watermark(video_path, message.from_user.id, download_message)

    if watermarked_video_path is None:
        await download_message.edit("❌ Failed to add watermark. Please try again.")
    else:
        await download_message.edit("Uploading watermarked video...")
        await message.reply_video(watermarked_video_path)

        os.remove(video_path)
        os.remove(watermarked_video_path)

app.run()
