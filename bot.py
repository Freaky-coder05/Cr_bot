import os
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot
app = Client(
    "audio_video_sync_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Path to save the files
DOWNLOAD_PATH = "downloads/"

# Function to run FFmpeg command
async def run_ffmpeg(input_video, input_audio, output_file):
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_video,
        "-i", input_audio,
        "-c:v", "copy",  # Copy video codec
        "-c:a", "aac",   # Encode audio to AAC
        "-strict", "experimental",
        "-map", "0:v:0",  # Map video from the first input
        "-map", "1:a:0",  # Map audio from the second input
        "-shortest",  # End output as soon as one of the inputs ends
        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {stderr.decode()}")

    return output_file

# Handler to start the bot and send a welcome message
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    welcome_text = (
        "Hello! 👋\n\n"
        "I am a Video-Audio Synchronizer Bot. You can use me to synchronize audio and video files.\n\n"
        "Here's how to use me:\n"
        "1. Send a video file or reply to a video message with the `/sync` command.\n"
        "2. I'll ask you to send the corresponding audio file.\n"
        "3. I'll sync them together and send you the result!\n\n"
        "Let's get started!"
    )
    await message.reply(welcome_text)

# Function to display the download progress
async def progress(current, total, message, action):
    progress_percentage = int(current * 100 / total)
    progress_message = f"{action}: {progress_percentage}%"
    await message.edit_text(progress_message)

# Handler to download and synchronize video and audio
@app.on_message(filters.command("sync") & filters.reply)
async def sync_video_audio(client: Client, message: Message):
    reply_message = message.reply_to_message

    if not (reply_message.video or reply_message.document):
        await message.reply("Please reply to a video file or document containing a video.")
        return

    status_message = await message.reply("Downloading video...")

    # Download the video with progress
    video_file = await reply_message.download(DOWNLOAD_PATH, progress=progress, progress_args=(status_message, "Downloading video"))

    # Update status after download
    await status_message.edit_text("Video downloaded. Now, please send the audio file.")

    # Wait for the audio file to be sent
    @app.on_message(filters.document | filters.audio)
    async def handle_audio(client: Client, audio_message: Message):
        status_message = await audio_message.reply("Downloading audio...")

        # Download the audio with progress
        audio_file = await audio_message.download(DOWNLOAD_PATH, progress=progress, progress_args=(status_message, "Downloading audio"))

        # Generate the output file name
        output_file = os.path.join(DOWNLOAD_PATH, f"synced_{os.path.basename(video_file)}")

        try:
            # Run FFmpeg to sync video and audio
            await status_message.edit_text("Synchronizing video and audio...")
            await run_ffmpeg(video_file, audio_file, output_file)

            await status_message.edit_text("Uploading synchronized video...")

            # Send the synchronized file with progress
            await client.send_document(
                message.chat.id, 
                output_file, 
                caption="Here is your synchronized video.", 
                progress=progress, 
                progress_args=(status_message, "Uploading synchronized video")
            )

        except Exception as e:
            await status_message.edit_text(f"Error: {e}")

        finally:
            # Cleanup downloaded and output files
            os.remove(video_file)
            os.remove(audio_file)
            os.remove(output_file)

# Run the bot
if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)
    app.run()
