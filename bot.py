import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN
import ffmpeg

bot = Client("video_editor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store videos for merging
video_merger_dict = {}
bot_data = {}

# Start message
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Welcome to the Video Editor Bot. You can send a video or document, and choose to trim or merge it.")

# When a video or document is sent, reply with Trim and Merge buttons
@bot.on_message(filters.video | filters.document)
async def video_handler(client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is waiting for the second video for merging
    if user_id in video_merger_dict and video_merger_dict[user_id]["awaiting_second_video"]:
        await merge_video_process(client, message, user_id)
    else:
        # Show action buttons if this is the first video
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Trim Video", callback_data="trim_video")],
                [InlineKeyboardButton("Merge Video", callback_data="merge_video")]
            ]
        )
        # Store the original video message for later use (in case of merging)
        bot_data[user_id] = {"video_message": message}
        await message.reply("Choose an action for this video:", reply_markup=buttons)

# Handle callback for trim video
@bot.on_callback_query(filters.regex("trim_video"))
async def trim_video_callback(client, callback_query):
    await callback_query.message.reply("Please provide the start and end times (in seconds) to trim the video.\nExample: `10 60` to trim from 10s to 60s.")
    bot_data[callback_query.from_user.id]["action"] = "trim"

# Handle callback for merge video
@bot.on_callback_query(filters.regex("merge_video"))
async def merge_video_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    # Retrieve the original message containing the first video
    if user_id in bot_data and "video_message" in bot_data[user_id]:
        first_video_message = bot_data[user_id]["video_message"]
        first_video_path = await first_video_message.download()
        
        # Store the first video and mark waiting for the second video
        video_merger_dict[user_id] = {
            "first_video": first_video_path,
            "awaiting_second_video": True
        }
        await callback_query.message.reply("Please send the second video to merge.")
    else:
        await callback_query.message.reply("Error: Could not find the first video.")

# Optimized Merge Process
async def merge_video_process(client, message, user_id):
    try:
        first_video_path = video_merger_dict[user_id]["first_video"]

        # Status message for downloading second video
        download_message = await message.reply("Downloading the second video...")
        second_video_path = await message.download()
        await download_message.edit("Second video downloaded. Merging the videos...")

        output_file = f"merged_{os.path.basename(first_video_path)}"

        # Re-encode both videos to a format that can be concatenated
        first_encoded = f"encoded_{os.path.basename(first_video_path)}"
        second_encoded = f"encoded_{os.path.basename(second_video_path)}"

        # Convert both videos to a common codec/container (e.g., H.264 in mp4)
        ffmpeg.input(first_video_path).output(first_encoded, vcodec='libx264', acodec='aac', strict='experimental').run()
        ffmpeg.input(second_video_path).output(second_encoded, vcodec='libx264', acodec='aac', strict='experimental').run()

        # Concatenate the two re-encoded videos
        ffmpeg.input(f"concat:{first_encoded}|{second_encoded}", format="concat", v=1, a=1).output(output_file).run()

        # Status message for uploading
        await message.reply_video(output_file, caption="Here is your merged video.")

        # Clean up
        os.remove(first_video_path)
        os.remove(second_video_path)
        os.remove(first_encoded)
        os.remove(second_encoded)
        os.remove(output_file)

        # Clear the user from the dictionary
        del video_merger_dict[user_id]

    except Exception as e:
        await message.reply(f"Error merging videos: {e}")
        del video_merger_dict[user_id]

if __name__ == "__main__":
    bot.run()
