import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Your DeepAI API Key
DEEP_AI_API_KEY = "2b19e75b-498d-45b1-aba8-b503c0625201"

# Initialize the bot
bot = Client("ghibli_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to convert image using DeepAI API
def convert_to_ghibli(image_path):
    url = "https://api.deepai.org/api/toonify"  # Correct API endpoint
    with open(image_path, "rb") as img:
        response = requests.post(url, files={"image": img}, headers={"api-key": DEEP_AI_API_KEY})
    
    try:
        response_data = response.json()
        if response.status_code == 200 and "output_url" in response_data:
            return response_data["output_url"]
        else:
            print(f"API Error: {response_data}")  # Debugging
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@bot.on_message(filters.photo)
async def ghibli_converter(client: Client, message: Message):
    processing_msg = await message.reply_text("🎨 Processing your image into Ghibli style...")

    # Download the image
    photo_path = await message.download()

    # Convert image using AI
    ghibli_image_url = convert_to_ghibli(photo_path)

    if ghibli_image_url:
        await message.reply_photo(ghibli_image_url, caption="✨ Here is your Ghibli-style image!")
    else:
        await message.reply_text("❌ Failed to convert image. DeepAI API might be down or your API key is invalid.")

    # Cleanup
    os.remove(photo_path)
    await processing_msg.delete()

print("Ghibli Image Converter Bot is running...")
bot.run()
