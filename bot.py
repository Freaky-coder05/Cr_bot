from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
import asyncio 
import pyrogram.utils

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

SOURCE_CHANNEL_ID=-1002160455430
DESTINATION_CHANNEL_ID=-1002851677744

app = Client("channel_copier_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start command to initiate copy
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    await message.reply_text("Send /copy to start copying messages from source channel.")

# /copy command to begin copying all messages
@app.on_message(filters.command("copy") & filters.private)
async def copy_channel_messages(client: Client, message: Message):
    await message.reply_text("Starting to copy messages...")

    source_id = SOURCE_CHANNEL_ID   # e.g., -1001234567890
    dest_id = DESTINATION_CHANNEL_ID  # e.g., -1009876543210

    # Start from message ID 1 (Telegram messages start from 1)
    current_msg_id = 1
    copied_count = 0

    while True:
        try:
            msg = await client.get_messages(source_id, current_msg_id)
            if not msg:
                break  # No more messages
            await asyncio.sleep(5)
            await msg.copy(dest_id)
            copied_count += 1
            print(f"Copied message {current_msg_id}")
        except Exception as e:
            print(f"Error at message {current_msg_id}: {e}")
        current_msg_id += 1

    await message.reply_text(f"Finished copying {copied_count} messages.")

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
