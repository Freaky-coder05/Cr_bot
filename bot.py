import os
import requests
import aiohttp
import asyncio
import aria2p
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize Bot
bot = Client("URLLeechBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Aria2 RPC
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=8030, secret=""))

async def download_file(url, file_name, message):
    """ Download Direct Links with Progress """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await message.reply_text("Failed to download file. Invalid URL.")
                return None
            
            total_size = int(resp.headers.get("content-length", 0))
            downloaded_size = 0
            chunk_size = 1024 * 1024  # 1MB
            
            with open(file_name, "wb") as file:
                async for chunk in resp.content.iter_any(chunk_size):
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    progress = (downloaded_size / total_size) * 100
                    await message.edit(f"Downloading: {progress:.2f}%")
    
    return file_name

async def aria2_download(url, message):
    """ Download Mirror & Torrent Files via Aria2 """
    try:
        download = aria2.add_uris([url])
        while not download.is_complete:
            await asyncio.sleep(2)
            progress = download.progress
            await message.edit(f"Downloading (Aria2): {progress:.2f}%")
        
        return download.files[0].path  # Return downloaded file path
    except Exception as e:
        await message.reply_text(f"Aria2 Download Failed: {e}")
        return None

@bot.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text("Hello! Send me a direct URL, mirror link, or torrent (magnet link/file) to leech.")

@bot.on_message(filters.text & filters.private)
async def leech_file(_, message: Message):
    url = message.text.strip()
    msg = await message.reply_text("Processing...")

    if url.startswith(("http", "https")):
        if any(ext in url for ext in [".torrent", "magnet:"]):
            file_path = await aria2_download(url, msg)
        else:
            file_name = url.split("/")[-1]
            file_path = await download_file(url, file_name, msg)
    else:
        await msg.edit("Invalid URL or unsupported format.")
        return

    if file_path:
        await msg.edit("Uploading file to Telegram...")
        await message.reply_document(file_path)
        os.remove(file_path)
        await msg.delete()
    else:
        await msg.edit("Download failed.")

bot.run()
