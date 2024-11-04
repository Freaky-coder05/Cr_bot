from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg
import os

# Bot API setup
app = Client("video_audio_merger_bot", api_id="YOUR_API_ID", api_hash="YOUR_API_HASH", bot_token="YOUR_BOT_TOKEN")

# Initialize user settings
user_settings = {}

# Command to toggle mode
@app.on_message(filters.command("mode"))
async def mode_command(client, message):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {
            "upload_as_document": False,
            "metadata": True,
            "mode": {
                "video_audio_merger": False,
                "remove_stream": False,
                "rename": False
            }
        }
    
    buttons = [
        [
            InlineKeyboardButton(
                "Video + Audio Merger" + (" ✅" if user_settings[user_id]["mode"]["video_audio_merger"] else ""),
                callback_data="toggle_video_audio_merger"
            ),
            InlineKeyboardButton(
                "Remove Stream" + (" ✅" if user_settings[user_id]["mode"]["remove_stream"] else ""),
                callback_data="toggle_remove_stream"
            )
        ]
    ]
    await message.reply_text(
        "Select Mode:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback for toggling modes
@app.on_callback_query()
async def toggle_mode(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_settings:
        await callback_query.answer("User settings not found.")
        return

    if callback_query.data == "toggle_video_audio_merger":
        user_settings[user_id]["mode"]["video_audio_merger"] = not user_settings[user_id]["mode"]["video_audio_merger"]
    elif callback_query.data == "toggle_remove_stream":
        user_settings[user_id]["mode"]["remove_stream"] = not user_settings[user_id]["mode"]["remove_stream"]
    
    # Update the inline keyboard with the new status
    buttons = [
        [
            InlineKeyboardButton(
                "Video + Audio Merger" + (" ✅" if user_settings[user_id]["mode"]["video_audio_merger"] else ""),
                callback_data="toggle_video_audio_merger"
            ),
            InlineKeyboardButton(
                "Remove Stream" + (" ✅" if user_settings[user_id]["mode"]["remove_stream"] else ""),
                callback_data="toggle_remove_stream"
            )
        ]
    ]
    await callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))

# Video + Audio Merger function
@app.on_message(filters.command("merge_video_audio"))
async def merge_video_audio(client, message):
    user_id = message.from_user.id
    if not user_settings.get(user_id, {}).get("mode", {}).get("video_audio_merger"):
        await message.reply_text("Video + Audio Merger mode is not enabled.")
        return
    
    await message.reply_text("Please send the video file to merge.")
    # Download and merge implementation follows

# Stream Remover function
@app.on_message(filters.command("remove_stream"))
async def remove_stream(client, message):
    user_id = message.from_user.id
    if not user_settings.get(user_id, {}).get("mode", {}).get("remove_stream"):
        await message.reply_text("Remove Stream mode is not enabled.")
        return
    
    await message.reply_text("Please send the video file to remove streams.")
    # Stream removal implementation follows

# Run the bot
app.run()
