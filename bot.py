from pyrogram import Client, filters
from pyrogram.types import Message
import os
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("auto_audio_renamer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# To store audio messages temporarily
audio_queue = []

@app.on_message(filters.audio | filters.voice | filters.document)
async def queue_audio(client: Client, message: Message):
    audio_queue.append(message)
    await message.reply_text("✅ Audio received and added to queue.")

@app.on_message(filters.command("start_process"))
async def process_audio(client: Client, message: Message):
    if not audio_queue:
        await message.reply_text("❌ Queue is empty.")
        return

    await message.reply_text("⚙️ Starting renaming process...")

    for idx, audio_msg in enumerate(audio_queue):
        try:
            # Get original file name if available
            orig_name = audio_msg.audio.file_name if audio_msg.audio else f"voice_{idx+1}.ogg"
            base_name = os.path.splitext(orig_name)[0]
            final_name = base_name + ".opus"

            # Download the file
            downloaded_path = await audio_msg.download(file_name=final_name)

            # Get file info
            file_size = os.path.getsize(downloaded_path) / 1024  # in KB
            
            # Upload audio file
            caption = f"🎵 **{final_name}**\n📦 Size: {int(file_size)} KB"
            await client.send_audio(
                chat_id=message.chat.id,
                audio=downloaded_path,
                caption=caption
            )

            os.remove(downloaded_path)  # Clean up

        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")

    audio_queue.clear()
    await message.reply_text("✅ All audios renamed and uploaded.")

app.run()
