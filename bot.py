import os
import ffmpeg
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from pyrogram.errors import MessageNotModified
from config import API_ID, API_HASH, BOT_TOKEN

bot = Client("video_audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}  # Dictionary to store video and user data

# Function to show progress for downloads/uploads
async def progress_bar(current, total, message, status):
    try:
        percent = current * 100 / total
        progress_message = f"{status}: {percent:.1f}%\n{current / 1024 / 1024:.1f}MB of {total / 1024 / 1024:.1f}MB"
        await message.edit(progress_message)
    except MessageNotModified:
        pass

# Start message
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello! I am a Video+Audio Merger bot. Send me a video first, and then send the audio file you want to merge with it!")

# Function to handle video file uploads
@bot.on_message(filters.video | filters.document)
async def handle_video(client, message):
    if message.video or (message.document and message.document.mime_type.startswith("video/")):
        video_progress = await message.reply("Downloading video...")

        # Download the video file
        video_file = await message.download(progress=lambda current, total: asyncio.run(progress_bar(current, total, video_progress, "Downloading video")))

        # Store the video file path and user ID for this user
        user_data[message.from_user.id] = {"video": video_file}
        await message.reply("Video received! Now, please send the audio file you want to merge with the video.")
    else:
        await message.reply("Please send a valid video file.")

# Function to handle audio file uploads and merge them with the video
@bot.on_message(filters.audio | filters.document)
async def handle_audio(client, message):
    user_id = message.from_user.id

    # Check if the user has already uploaded a video
    if user_id not in user_data or "video" not in user_data[user_id]:
        await message.reply("Please upload a video first before sending the audio.")
        return

    # Check if the document is an audio file
    if message.document and not message.document.mime_type.startswith("audio/"):
        await message.reply("Please send a valid audio file.")
        return

    audio_progress = await message.reply("Downloading audio...")

    # Download the audio file
    audio_file = await message.download(progress=lambda current, total: asyncio.run(progress_bar(current, total, audio_progress, "Downloading audio")))

    # Ask the user for a new name for the output file
    await message.reply("Please provide a new name for the merged video (without the extension).", reply_markup=ForceReply())

    # Wait for the user's response with the new name
    @bot.on_message(filters.text & filters.chat(message.chat.id))
    async def ask_for_name(client, new_name_message):
        new_name = new_name_message.text.strip()
        if not new_name:
            await new_name_message.reply("No name provided. Merging process aborted.")
            return

        # Ensure we have the video path
        video_info = user_data.get(user_id)
        if video_info is None or "video" not in video_info:
            await new_name_message.reply("No video found for merging.")
            return

        video_file = video_info["video"]  # Get the video file path

        # Set the output file name with the new name provided by the user
        output_file = f"{new_name}.mp4"

        try:
            await new_name_message.reply("Merging video and audio...")

            # Merge video with the new audio
            ffmpeg.input(video_file).input(audio_file).output(output_file, codec="copy", shortest=None, map="0:v:0", map="1:a:0").run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

            await new_name_message.reply(f"Merging complete. The file has been renamed to {new_name}. Uploading the file...")

            # Upload the merged file with a progress bar
            upload_progress = await new_name_message.reply("Uploading file...")
            await client.send_document(
                chat_id=new_name_message.chat.id,
                document=output_file,
                progress=lambda current, total: asyncio.run(progress_bar(current, total, upload_progress, "Uploading file"))
            )

        except ffmpeg.Error as e:
            error_message = e.stderr.decode()  # Capture the error output
            await new_name_message.reply(f"An error occurred during merging:\n{error_message}")

        except Exception as e:
            await new_name_message.reply(f"An unexpected error occurred: {str(e)}")

        finally:
            # Clean up
            os.remove(video_file)
            os.remove(audio_file)
            if os.path.exists(output_file):
                os.remove(output_file)

    # Prevent multiple handlers for the same user
    await asyncio.sleep(30)  # Wait 30 seconds before allowing another input to avoid conflicts

if __name__ == "__main__":
    bot.run()
