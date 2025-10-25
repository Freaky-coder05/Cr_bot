import os
import subprocess
import glob
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------- CONFIG ----------------
API_ID = int(os.environ.get("API_ID",  24435985))  # replace or use env vars
API_HASH = os.environ.get("API_HASH", "0fec896446625478537e43906a4829f8")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7758738938:AAGwhb8vXtHw9INX8SzCr82PKYtjQJHE-3c")

CLI_PATH = "./build/animepahe-cli-beta"
DOWNLOAD_DIR = "/content/animepahe-cli"

# ----------------------------------------

bot = Client("animepahe_cli_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Ensure download folder exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🎬 **AnimePahe CLI Bot** is ready!\n\n"
        "Use this format:\n"
        "`/anime <anime_link> <episodes>`\n\n"
        "Example:\n"
        "`/anime https://animepahe.si/anime/c042ba75-c528-d9d6-1985-64be9734788f 1-3`"
    )

@bot.on_message(filters.command("anime"))
async def anime(_, msg: Message):
    try:
        cmd_args = msg.text.replace("/anime", "").strip()
        if not cmd_args:
            await msg.reply_text("❌ Please provide arguments.\nExample:\n`/anime -l <link> -e 1-3`")
            return

        # Build the full command
        cmd = f'"{CLI_PATH}" {cmd_args}'
        await msg.reply_text(f"⚙️ Running command:\n`{command}`")
        await msg.reply_text(f"🔁 Starting download for episodes `{episodes}`...\n📺 {link}")

        
        # Run the download command
        process = subprocess.run(
            cmd, shell=True, cwd=DOWNLOAD_DIR, capture_output=True, text=True
        )

        # Show errors if any
        if process.returncode != 0:
            await msg.reply_text(f"⚠️ Download failed:\n```\n{process.stderr}\n```")
            return

        # Find downloaded files
        files = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "**/*.mp4"), recursive=True))
        
        

        if not files:
            await msg.reply_text("⚠️ No video files found after download.")
            return

        await msg.reply_text(f"✅ Download complete! Uploading {len(files)} file(s)...")

        for file in files:
            filename = os.path.basename(file)
            await msg.reply_document(file, caption=f"🎥 {filename}")
            os.remove(file)

        await msg.reply_text("🎉 All episodes uploaded successfully!")

    except Exception as e:
        await msg.reply_text(f"❌ Error: `{e}`")

bot.run()
