import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot with Pyrogram
app = Client("video_editor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user video file details for merging
video_dict = {}

# Function to trim video using FFmpeg
async def trim_video(input_file, start_time, end_time, output_file):
    cmd = f"ffmpeg -i {input_file} -ss {start_time} -to {end_time} -c copy {output_file}"
    subprocess.call(cmd, shell=True)

# Function to merge two videos using FFmpeg
async def merge_videos(input_file1, input_file2, output_file):
    cmd = f"ffmpeg -i {input_file1} -i {input_file2} -filter_complex '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]' -map '[outv]' -map '[outa]' {output_file}"
    subprocess.call(cmd, shell=True)

# Start message
@app.on_message(filters.command("start"))
async def start_message(client, message):
    await message.reply_text("Welcome to the Video Editor Bot! Send me a video or document file to start editing.")

# Handler for receiving video or document
@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    # Send downloading status message
    status_message = await message.reply_text("Downloading your file...")

    # Download the video
    video_path = await message.download()

    # Update status message after download is complete
    await status_message.edit_text("File downloaded successfully!")

    # Send reply with inline buttons for "Trim Video" and "Merge Video"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Trim Video", callback_data=f"trim|{message.message_id}")],
        [InlineKeyboardButton("Merge Video", callback_data=f"merge|{message.message_id}")]
    ])
    await message.reply_text("Select an option:", reply_markup=buttons)

# Callback query handler for the trim and merge actions
@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    data = callback_query.data.split("|")
    action = data[0]
    message_id = int(data[1])

    # Download the video associated with the message
    message = await callback_query.message.chat.get_messages(message_ids=message_id)
    video_path = await message.download()

    if action == "trim":
        # Ask the user for start and end times (in HH:MM:SS format)
        await callback_query.message.reply_text("Send the start and end times in HH:MM:SS format (e.g., 00:00:10-00:00:30).")

        @app.on_message(filters.text)
        async def get_trim_times(client, trim_message):
            try:
                start_time, end_time = trim_message.text.split("-")
                output_file = "trimmed_" + os.path.basename(video_path)
                status_message = await callback_query.message.reply_text("Trimming the video...")

                # Trim video
                await trim_video(video_path, start_time, end_time, output_file)

                # Update status message after trimming is complete
                await status_message.edit_text("Uploading trimmed video...")
                
                # Send the trimmed video
                await callback_query.message.reply_video(video=output_file, caption="Here is your trimmed video.")
                
                os.remove(output_file)  # Clean up the file after sending
            except Exception as e:
                await callback_query.message.reply_text(f"Error: {e}")
    
    elif action == "merge":
        user_id = callback_query.from_user.id
        if user_id in video_dict:
            # Merge the stored video with the new one
            video_path_2 = video_dict.pop(user_id)
            output_file = "merged_" + os.path.basename(video_path)
            status_message = await callback_query.message.reply_text("Merging videos...")

            # Merge videos
            await merge_videos(video_path, video_path_2, output_file)

            # Update status message after merging
            await status_message.edit_text("Uploading merged video...")

            # Send the merged video
            await callback_query.message.reply_video(video=output_file, caption="Here is your merged video.")
            os.remove(output_file)  # Clean up
        else:
            # Store the first video and ask for the second
            video_dict[user_id] = video_path
            await callback_query.message.reply_text("Send another video to merge with this one.")

# Run the bot
app.run()
