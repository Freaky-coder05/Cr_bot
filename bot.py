import os
import json
import time
import requests
import subprocess
from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN, ARIA2_RPC_URL, ARIA2_SECRET, DOWNLOAD_PATH

# Start Aria2 as a background process
subprocess.Popen(["aria2c", "--enable-rpc", "--rpc-listen-all=true", "--rpc-allow-origin-all", "--rpc-secret=" + ARIA2_SECRET])

# Initialize the bot
bot = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to add torrent/magnet link to Aria2
def add_torrent_to_aria2(torrent_link):
    payload = {
        "jsonrpc": "2.0",
        "id": "qwer",
        "method": "aria2.addUri",
        "params": [f"token:{ARIA2_SECRET}", [torrent_link]]
    }
    response = requests.post(ARIA2_RPC_URL, json=payload)
    if response.ok:
        result = response.json()
        return result.get("result")
    return None

# Function to check download status
def get_download_status(gid):
    payload = {
        "jsonrpc": "2.0",
        "id": "qwer",
        "method": "aria2.tellStatus",
        "params": [f"token:{ARIA2_SECRET}", gid]
    }
    response = requests.post(ARIA2_RPC_URL, json=payload)
    if response.ok:
        return response.json().get("result")
    return None

# Command handler for /start
@bot.on_message(filters.command("start"))
async def start(bot, message):
    await message.reply_text("Send me a **torrent link** or **magnet link**, and I will download it for you!")

# Handler for torrent/magnet links
@bot.on_message(filters.text & filters.private)
async def handle_torrent(bot, message):
    link = message.text
    if not link.startswith("magnet:?xt=") and not link.endswith(".torrent"):
        await message.reply_text("❌ Invalid link. Please send a valid **magnet** or **torrent URL**.")
        return
    
    msg = await message.reply_text("⏳ Adding to download queue...")

    # Add to Aria2
    gid = add_torrent_to_aria2(link)
    if not gid:
        await msg.edit_text("❌ Failed to add torrent.")
        return

    await msg.edit_text("✅ Torrent added! Downloading...")

    # Monitor the download status
    while True:
        status = get_download_status(gid)
        if not status:
            await msg.edit_text("❌ Download failed or was removed.")
            return
        
        progress = int(status.get("completedLength", "0")) / int(status.get("totalLength", "1")) * 100
        await msg.edit_text(f"📥 Downloading... {progress:.2f}%")

        if status["status"] == "complete":
            break
        time.sleep(5)

    # Get downloaded file path
    file_path = status["files"][0]["path"]
    file_name = os.path.basename(file_path)

    await msg.edit_text("✅ Download complete! Uploading...")

    # Send file to user
    await message.reply_document(file_path, caption=f"Here is your file: `{file_name}`")

    # Cleanup
    os.remove(file_path)

bot.run()
