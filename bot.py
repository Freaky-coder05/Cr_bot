from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

DESTINATION_CHANNEL_ID = -1002851677744  # Replace with destination channel ID

app = Client("button_forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.forwarded)
async def forward_button_post(client: Client, message: Message):
    if message.reply_markup:
        try:
            await message.copy(DESTINATION_CHANNEL_ID)
            print(f"Forwarded message with buttons: {message.message_id}")
        except Exception as e:
            print(f"Failed to forward message {message.message_id}: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
