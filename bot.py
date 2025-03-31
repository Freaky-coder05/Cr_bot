import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
from config import *

bot = Client("ghibli_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to apply a simple Ghibli-style filter (placeholder)
def apply_ghibli_filter(image_path):
    img = Image.open(image_path).convert("RGB")
    
    # Simulating a Ghibli-style effect (Placeholder)
    img = img.convert("L").convert("RGB")  # Converts to grayscale and back to RGB
    img = img.point(lambda p: p * 0.8)  # Slightly reduces brightness

    ghibli_path = image_path.replace(".jpg", "_ghibli.jpg")
    img.save(ghibli_path)
    return ghibli_path

# Image processing
@bot.on_message(filters.photo)
async def convert_to_ghibli(client: Client, message: Message):
    processing_msg = await message.reply_text("🎨 Converting image to Ghibli-style...")

    # Download the image
    photo_path = await message.download()
    
    # Apply the filter
    ghibli_image_path = apply_ghibli_filter(photo_path)

    # Send the converted image
    await message.reply_photo(ghibli_image_path, caption="✨ Here is your Ghibli-style image!")

    # Cleanup
    os.remove(photo_path)
    os.remove(ghibli_image_path)

    await processing_msg.delete()

# Start bot
print("Ghibli Image Converter Bot is running...")
bot.run()
