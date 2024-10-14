import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import API_ID, API_HASH, BOT_TOKEN, WORKING_DIR, WATERMARK_PATH

app = Client("watermark_adder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.video | filters.document)
async def handle_media(client, message: Message):
    # Start downloading the file
    file_path = await client.download_media(message)
    
    # Prepare output file path
    output_vid = os.path.join(WORKING_DIR, f"watermarked_{os.path.basename(file_path)}")
    
    # Watermarking
    await add_watermark(file_path, output_vid, WATERMARK_PATH)

    # Upload the watermarked video
    await client.send_video(message.chat.id, output_vid)

    # Clean up
    os.remove(file_path)
    os.remove(output_vid)

async def add_watermark(input_vid, output_vid, watermark_path):
    size = 20  # default size percentage
    position = '10:10'  # default position
    mode = 'ultrafast'  # default encoding mode

    # Create the FFmpeg command
    file_genertor_command = [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet", "-i", input_vid,
        "-i", watermark_path,
        "-filter_complex", f"[1][0]scale2ref=w='iw*{size}/100':h='ow/mdar'[wm][vid];[vid][wm]overlay={position}",
        "-c:v", "copy", "-preset", mode, "-crf", "0", "-c:a", "copy", output_vid
    ]
    
    # Run the command
    subprocess.run(file_genertor_command)

@app.on_message(filters.command("edit_watermark"))
async def edit_watermark(client, message: Message):
    keyboard = [
        [
            InlineKeyboardButton("Change Size", callback_data="change_size"),
            InlineKeyboardButton("Change Position", callback_data="change_position"),
        ],
        [InlineKeyboardButton("Change Width", callback_data="change_width")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply("Select an option to edit the watermark:", reply_markup=reply_markup)

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    if callback_query.data == "change_size":
        # Logic to change size (e.g., ask for a new size)
        await callback_query.answer("Send the new size percentage (1-100).")
    elif callback_query.data == "change_position":
        # Logic to change position (e.g., predefined positions)
        await callback_query.answer("Send the new position (e.g., '10:10').")
    elif callback_query.data == "change_width":
        # Logic to change width (e.g., ask for new width)
        await callback_query.answer("Send the new width in pixels.")

if __name__ == "__main__":
    if not os.path.exists(WORKING_DIR):
        os.makedirs(WORKING_DIR)
    app.run()
