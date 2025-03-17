import os
import time
import aiohttp
import asyncio
import aria2p
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize Bot
bot = Client("URLLeechBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.text & filters.private)
async def dfile(client, message):
    
    link, name = "", ""
    try:
        link = message.text.split()[1]
        name = message.text.split()[2]
    except BaseException:
        pass
    if not link:
        return
    
    s = dt.now()
    xxx = await event.reply("`Downloading...`")
    try:
        dl = await fast_download(xxx, link, name)
    except Exception as er:
        await message.reply_text("an error occurred:",er)

    if dl:
        await message.reply_text("uploading ")
        await message.send_document(dl)
    else:
        await message.reply_text("No file found")

bot.run()
