import os
import subprocess
import glob
from pyrogram import Client, filters
from pyrogram.types import Message
import re

# ---------------- CONFIG ----------------
API_ID = int(os.environ.get("API_ID", 24435985))
API_HASH = os.environ.get("API_HASH", "0fec896446625478537e43906a4829f8")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7758738938:AAGwhb8vXtHw9INX8SzCr82PKYtjQJHE-3c")


bot = Client("urlbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


import aiohttp

async def get_short_link(user, link):
    api_key = "d5df2a373f3d68a2d3c86848dd6aab838e5309a0"
    base_site = "linkshortify.com"

    api_url = f"https://{base_site}/api?api={api_key}&url={link}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            data = await resp.json()

    if data.get("status") == "success":
        return data["shortenedUrl"]

    return None
    
@bot.on_message(filters.private & filters.text)
async def auto_shortener(bot, message):
    text = message.text

    # Regex for detecting URLs
    url_pattern = r'(https?://[^\s]+)'
    found = re.findall(url_pattern, text)

    if not found:
        return  # No link, ignore message

    url = found[0]  # Only first URL is shortened

   

    user_id = message.from_user.id
    

    
    short_link = await get_short_link(user_id, url)

    if short_link:
        await message.reply(
            f"<b>⭕ Here is your short link:\n\n🖇️ {short_link}</b>"
        )
    else:
        await message.reply("❌ Unable to shorten the link.")


bot.run()
