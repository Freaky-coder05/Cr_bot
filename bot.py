import os
import torch
import cv2
import numpy as np
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from torchvision import transforms
from AnimeGANv2.model import Generator  # Import AnimeGANv2 model

# Initialize Pyrogram bot
bot = Client("ghibli_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load the AnimeGANv2 Ghibli model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = Generator()
model.load_state_dict(torch.load("AnimeGANv2/checkpoints/ghibli.pt", map_location=device))
model.to(device).eval()

# Function to apply Ghibli filter
def apply_ghibli_filter(image_path):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)

    transform = transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])
    
    input_tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        output_tensor = model(input_tensor)
    
    output_tensor = output_tensor.squeeze().cpu().numpy().transpose(1, 2, 0)
    output_tensor = ((output_tensor + 1) * 127.5).astype(np.uint8)
    output_img = Image.fromarray(output_tensor)

    ghibli_path = image_path.replace(".jpg", "_ghibli.jpg")
    output_img.save(ghibli_path)
    return ghibli_path

@bot.on_message(filters.photo)
async def convert_to_ghibli(client: Client, message: Message):
    processing_msg = await message.reply_text("🎨 Converting your image to Ghibli style...")

    photo_path = await message.download()
    ghibli_image_path = apply_ghibli_filter(photo_path)

    await message.reply_photo(ghibli_image_path, caption="✨ Here is your Ghibli-style image!")

    os.remove(photo_path)
    os.remove(ghibli_image_path)

    await processing_msg.delete()

print("Ghibli Image Converter Bot is running...")
bot.run()
