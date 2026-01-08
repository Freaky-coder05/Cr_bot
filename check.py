# ===================== IMPORTS =====================
import os
import glob
import time
import math
import asyncio
import sqlite3
import subprocess
import random
import string
import shutil
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import ffmpeg, tempfile
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

executor = ThreadPoolExecutor(max_workers=4)

# ===================== CONFIG =====================
API_ID = 24435985
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7662286847:AAGxeoaNdaxab-y2lwy1jEP8hpGEZNjpqdg"

OWNER_ID = 6299192020  # Only this ID can use /login
BOT_USERNAME = "Awt_cr_bot"
DUMP_CHANNEL = -1002299104635 

LINKSHORTIFY_API_KEY = "d5df2a373f3d68a2d3c86848dd6aab838e5309a0"
LINKSHORTIFY_API_URL = "https://linkshortify.com/api"

MULTI_DL_PATH = "/root/Ac"
VIDEOS_PATH = os.path.join(MULTI_DL_PATH, "videos")
os.makedirs(VIDEOS_PATH, exist_ok=True)

app = Client("crunchy_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

USER_AUTH_DATA = {}

# ===================== DATABASE =====================
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS tokens (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS verify (user_id INTEGER, token TEXT)")
cur.execute("INSERT OR IGNORE INTO admins VALUES (?)", (OWNER_ID,))
db.commit()

# ===================== HELPERS =====================
def is_admin(uid: int) -> bool:
    cur.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,))
    return bool(cur.fetchone())

def get_tokens(uid: int) -> int:
    cur.execute("SELECT count FROM tokens WHERE user_id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

def add_token(uid: int, n: int = 1):
    cur.execute("INSERT OR IGNORE INTO tokens VALUES (?,0)", (uid,))
    cur.execute("UPDATE tokens SET count = count + ? WHERE user_id=?", (n, uid))
    db.commit()

def use_token(uid: int):
    cur.execute("UPDATE tokens SET count = count - 1 WHERE user_id=? AND count>0", (uid,))
    db.commit()

def get_video_details(file_loc):
    metadata = extractMetadata(createParser(file_loc))
    if metadata:
        return {
            "title": metadata.get("title") if metadata.has("title") else "Untitled",
            "duration": metadata.get("duration").seconds if metadata.has("duration") else 0
        }
    return {"title": "Untitled", "duration": 0}

def take_screenshot(file_path, timestamp, output_image):
    try:
        (ffmpeg.input(file_path, ss=timestamp).output(output_image, vframes=1).run(overwrite_output=True, quiet=True))
    except: pass
    return output_image

def humanbytes(size):
    if not size: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0: return f"{size:.2f} {unit}"
        size /= 1024.0

async def progress_for_pyrogram(current, total, ud_type, message, start):
    diff = time.time() - start
    if diff <= 0: return
    if round(diff % 5) == 0 or current == total:
        pct = current * 100 / total
        bar = "█" * int(pct / 5) + "▒" * (20 - int(pct / 5))
        try: await message.edit(f"<blockquote>{ud_type}</blockquote>\n\n{bar}\n{pct:.2f}%")
        except: pass

# ===================== QUEUE WORKER =====================
QUEUE = deque()
QUEUE_LOCK = asyncio.Lock()
RUNNING = False

async def process_queue():
    global RUNNING
    async with QUEUE_LOCK:
        if RUNNING or not QUEUE:
            RUNNING = False
            return
        RUNNING = True

    message, args = QUEUE.popleft()
    await message.reply_text("⏳ **MDNX:** Downloading...")
    
    cmd = ["npx", "ts-node", "-T", "index.ts", "--service", "crunchy", "--srz", args[0], "-e", args[1], "--dubLang", args[2], "--dlsubs", args[3], "--defaultAudio", args[4], "--defaultSub", args[5], "--forceMuxer", "mkvmerge", "-q", args[6]]
    subprocess.run(cmd, cwd=MULTI_DL_PATH)

    files = glob.glob(f"{VIDEOS_PATH}/**/*.mkv", recursive=True) + glob.glob(f"{VIDEOS_PATH}/**/*.mp4", recursive=True)
    if files:
        f = max(files, key=os.path.getmtime)
        await upload_file(message, f)
        if os.path.exists(f): os.remove(f)
    else:
        await message.reply_text("❌ Download failed.")

    RUNNING = False
    if QUEUE: await process_queue()

async def upload_file(message, path):
    start = time.time()
    status = await message.reply_text("<blockquote>📤 Uploading...</blockquote>")
    try:
        details = get_video_details(path)
        base_name=os.path.basename(path)
        thumb_path = tempfile.mktemp(suffix=".jpg")
        await asyncio.get_running_loop().run_in_executor(executor, take_screenshot, path, 5, thumb_path)
        caption = (
            f"📥 **New File Uploaded**\n\n"
            f"**File:** `{base_name}`\n"
            f"**Duration:** {time_fmt(details['duration']*1000)}\n\n"
            f"👤 **User:** {message.from_user.mention}\n"
            f"🆔 **ID:** `{message.from_user.id}`"
        )
      
        sent_msg = await app.send_video(
            chat_id=message.from_user.id,
            video=path,
            thumb=thumb_path if os.path.exists(thumb_path) else None,
            duration=details['duration'],
            caption=caption,
            progress=progress_for_pyrogram,
            progress_args=("📤 Uploading", status, start)
        )
        await sent_msg.copy(DUMP_CHANNEL)
        if os.path.exists(thumb_path): os.remove(thumb_path)
    except Exception as e:
        await message.reply_text(f"❌ Upload Error: {e}")
    await status.delete()

# ===================== OWNER ONLY LOGIN (ALTERED) =====================
@app.on_message(filters.command("login") & filters.private & filters.user(OWNER_ID))
async def login_start(_, m: Message):
    USER_AUTH_DATA[m.from_user.id] = {"step": "email"}
    await m.reply_text("📧 **Owner Auth:** Send Crunchyroll Email:")

@app.on_message(filters.private & filters.user(OWNER_ID) & ~filters.command(["start", "dl", "login", "addadmin", "removeadmin", "cleardir"]))
async def login_handler(_, m: Message):
    uid = m.from_user.id
    if uid not in USER_AUTH_DATA: return

    state = USER_AUTH_DATA[uid]
    if state["step"] == "email":
        state["email"] = m.text
        state["step"] = "password"
        await m.reply_text("🔑 Send Password:")
    elif state["step"] == "password":
        msg = await m.reply_text("🔄 Authenticating...")
        cmd = ["npx", "ts-node", "-T", "index.ts", "--service", "crunchy", "--auth"]
        input_data = f"{state['email']}\n{m.text}\n"
        try:
            res = subprocess.run(cmd, cwd=MULTI_DL_PATH, input=input_data, capture_output=True, text=True, timeout=60)
            await msg.edit("✅ Login successful!" if res.returncode == 0 else f"❌ Failed: {res.stderr[:200]}")
        except Exception as e: await msg.edit(f"❌ Error: {e}")
        del USER_AUTH_DATA[uid]

# ===================== OWNER COMMANDS (ADMIN MGMT) =====================
@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def addadmin(_, m):
    if len(m.command) > 1:
        target = int(m.command[1])
        cur.execute("INSERT OR IGNORE INTO admins VALUES (?)", (target,))
        db.commit()
        await m.reply_text(f"✅ `{target}` is now an Admin.")

@app.on_message(filters.command("removeadmin") & filters.user(OWNER_ID))
async def removeadmin(_, m):
    if len(m.command) > 1:
        target = int(m.command[1])
        if target == OWNER_ID: return await m.reply_text("❌ Cannot remove owner.")
        cur.execute("DELETE FROM admins WHERE user_id=?", (target,))
        db.commit()
        await m.reply_text(f"❌ `{target}` removed from Admins.")

@app.on_message(filters.command("cleardir") & filters.user(OWNER_ID))
async def cleardir(_, m):
    shutil.rmtree(VIDEOS_PATH); os.makedirs(VIDEOS_PATH)
    await m.reply_text("🧹 Directory Cleaned.")

# ===================== USER COMMANDS =====================
@app.on_message(filters.command("start"))
async def start_handler(_, m):
    if len(m.command) > 1 and m.command[1].startswith("verify"):
        _, uid, token = m.command[1].split("-", 2)
        cur.execute("SELECT 1 FROM verify WHERE user_id=? AND token=?", (int(uid), token))
        if cur.fetchone():
            cur.execute("DELETE FROM verify WHERE user_id=?", (int(uid),))
            add_token(int(uid), 1); await m.reply_text("✅ +1 Token Added!")
    await m.reply_text("Bot Active. Use /add_token for downloads.")

@app.on_message(filters.command("add_token"))
async def add_token_cmd(_, m):
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    cur.execute("INSERT INTO verify VALUES (?,?)", (m.from_user.id, token))
    db.commit()
    long_url = f"https://t.me/{BOT_USERNAME}?start=verify-{m.from_user.id}-{token}"
    short = requests.get(LINKSHORTIFY_API_URL, params={"api": LINKSHORTIFY_API_KEY, "url": long_url, "format": "text"}).text
    await m.reply_text("🎟 Verify to earn a token:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Verify", url=short)]]))

@app.on_message(filters.command(["dl", "cr_dl"]))
async def download(_, m):
    args = m.text.split()
    if len(args) < 8: return await m.reply_text("Usage: `/dl ID EP DUB SUBS A_DEF S_DEF RES`")
    if not is_admin(m.from_user.id) and get_tokens(m.from_user.id) <= 0:
        return await m.reply_text("🎟 Token required. Use /add_token")
    QUEUE.append((m, args[1:8]))
    if not is_admin(m.from_user.id): use_token(m.from_user.id)
    await m.reply_text(f"📥 Queued. Position: {len(QUEUE)}")
    if not RUNNING: asyncio.create_task(process_queue())

@app.on_message(filters.command("mytokens"))
async def mytokens(_, m): await m.reply_text(f"🎟 Tokens: {get_tokens(m.from_user.id)}")

@app.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply_text("<b>Help:</b>\n/add_token - Get tokens\n/dl - Download\n/mytokens - Check balance")

if __name__ == "__main__":
    app.run()
