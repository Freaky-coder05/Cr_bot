import os
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from pyrogram.enums import ChatAction
from pydub.utils import mediainfo
import humanize

# Temporary list to store audio messages
audio_queue = []

app = Client("audio_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Ensure temp folders exist
os.makedirs("downloads", exist_ok=True)
os.makedirs("compressed", exist_ok=True)

@app.on_message(filters.private & filters.audio)
async def queue_audio(client: Client, message: Message):
    audio_queue.append(message)
    await message.reply_text(f"🎧 Added `{message.audio.file_name}` to queue.\nUse /start_process to compress and receive.")

@app.on_message(filters.command("start_process") & filters.private)
async def process_audio(client: Client, message: Message):
    if not audio_queue:
        return await message.reply("❌ No audio messages in queue.")

    await message.reply("🔁 Starting compression process...")

    for audio_msg in audio_queue:
        try:
            file_name = audio_msg.audio.file_name or f"{audio_msg.audio.file_unique_id}.ogg"
            input_path = f"downloads/{file_name}"
            output_path = f"compressed/{os.path.splitext(file_name)[0]}_compressed.ogg"

            await message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
            await audio_msg.download(file_name=input_path)

            # Compress with ffmpeg
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c:a", "libopus",
                "-b:a", "32k",
                "-y",
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Get metadata
            info = mediainfo(output_path)
            duration = float(info.get("duration", 0))
            size = os.path.getsize(output_path)

            mins = int(duration) // 60
            secs = int(duration) % 60
            caption = f"🎵 **{os.path.basename(output_path)}**\n📦 Size: `{humanize.naturalsize(size)}`\n⏱ Duration: `{mins}:{secs:02d}`"

            await audio_msg.reply_document(output_path, caption=caption)

        except Exception as e:
            await message.reply(f"❌ Error processing: {str(e)}")
        finally:
            # Clean up
            if os.path.exists(input_path): os.remove(input_path)
            if os.path.exists(output_path): os.remove(output_path)

    audio_queue.clear()
    await message.reply("✅ All files compressed and sent.")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply("👋 Send audio files. Use /start_process to compress all to 32kbps Opus and receive them.")

app.run()
