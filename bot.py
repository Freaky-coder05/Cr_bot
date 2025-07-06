from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN

import asyncio 
import pyrogram.utils

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

SOURCE_CHANNEL_ID=-1002160455430
DESTINATION_CHANNEL_ID=-1002851677744

app = Client("button_copy_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("copy") & filters.private)
async def copy_post_with_buttons(client: Client, message: Message):
    try:
        msg_id = int(message.text.split(" ", 1)[1])  # Usage: /copy 123
        src_msg = await client.get_messages(SOURCE_CHANNEL_ID, msg_id)

        # Download media (e.g. photo)
        media_file = await client.download_media(src_msg) if src_msg.media else None

        # Extract inline buttons
        buttons = []
        if src_msg.reply_markup:
            for row in src_msg.reply_markup.inline_keyboard:
                button_row = []
                for button in row:
                    if button.url:
                        button_row.append(InlineKeyboardButton(text=button.text, url=button.url))
                if button_row:
                    buttons.append(button_row)

        # Send re-created post to destination channel
        if media_file:
            await client.send_photo(
                chat_id=DESTINATION_CHANNEL_ID,
                photo=media_file,
                caption=src_msg.caption,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
            )
        else:
            await client.send_message(
                chat_id=DESTINATION_CHANNEL_ID,
                text=src_msg.text or src_msg.caption or "No content",
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
            )

        await message.reply_text("✅ Post copied with original buttons.")
    
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
