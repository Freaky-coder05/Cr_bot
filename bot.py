import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
from config import API_ID, API_HASH, BOT_TOKEN

# API Key for DeepAI or any other AI service (Replace with your API key)
DEEP_AI_API_KEY = "2b19e75b-498d-45b1-aba8-b503c0625201"

# Initialize the bot
bot = Client("ghibli_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to convert image using DeepAI API
def convert_to_ghibli(image_path):
    url = "https://api.deepai.org/api/deepdream"  # Change API endpoint if needed
    with open(image_path, "rb") as img:
        response = requests.post(url, files={"image": img}, headers={"api-key": DEEP_AI_API_KEY})
    
    if response.status_code == 200:
        return response.json().get("output_url")
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
        await message.reply_text("❌ Failed to convert image. Try again later.")

    # Cleanup
    os.remove(photo_path)
    await processing_msg.delete()

print("Ghibli Image Converter Bot is running...")
bot.run()
