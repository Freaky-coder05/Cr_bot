import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN
import ffmpeg

bot = Client("video_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store videos for merging
video_merger_dict = {}
bot_data = {}

# Start message
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Welcome to the Video Merger Bot. Send a video or document and choose to merge it.")

# When a video or document is sent, reply with the Merge button
@bot.on_message(filters.video | filters.document)
async def video_handler(client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is waiting for the second video for merging
    if user_id in video_merger_dict and video_merger_dict[user_id]["awaiting_second_video"]:
        await merge_video_process(client, message, user_id)
    else:
        # Show Merge button if this is the first video
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Merge Video", callback_data="merge_video")]
            ]
        )
        # Store the original video message for later use (in case of merging)
        bot_data[user_id] = {"video_message": message}
        await message.reply("Choose an action for this video:", reply_markup=buttons)

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

# Merge Process (Without Re-encoding)
async def merge_video_process(client, message, user_id):
    try:
        first_video_path = video_merger_dict[user_id]["first_video"]

        # Status message for downloading second video
        download_message = await message.reply("Downloading the second video...")
        second_video_path = await message.download()
        await download_message.edit("Second video downloaded. Merging the videos...")

        # Create a temporary text file to store the file paths for FFmpeg concat
        concat_list_path = f"{user_id}_concat.txt"
        with open(concat_list_path, "w") as file:
            file.write(f"file '{first_video_path}'\n")
            file.write(f"file '{second_video_path}'\n")

        output_file = f"merged_{os.path.basename(first_video_path)}"

        # Use FFmpeg concat demuxer to merge videos without re-encoding
        ffmpeg.input(concat_list_path, format="concat", safe=0).output(output_file, c='copy').run()

        # Status message for uploading
        await message.reply_video(output_file, caption="Here is your merged video.")

        # Clean up
        os.remove(first_video_path)
        os.remove(second_video_path)
        os.remove(output_file)
        os.remove(concat_list_path)

        # Clear the user from the dictionary
        del video_merger_dict[user_id]

    except Exception as e:
        await message.reply(f"Error merging videos: {e}")
        del video_merger_dict[user_id]

if __name__ == "__main__":
    bot.run()
