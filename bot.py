import os
import requests
from pyrogram import Client, filters, 
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN


PROGRESS_BAR = """\n
<b>📁 Size</b> : {1} | {2}
<b>⏳️ Done</b> : {0}%
<b>🚀 Speed</b> : {3}/s
<b>⏰️ ETA</b> : {4} """

import math, time
from datetime import datetime
from pytz import timezone
from config import Config, Txt 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 5.00) == 0 or current == total:        
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "{0}{1}".format(
            ''.join(["⬢" for i in range(math.floor(percentage / 5))]),
            ''.join(["⬡" for i in range(20 - math.floor(percentage / 5))])
        )            
        tmp = progress + PROGRESS_BAR.format( 
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),            
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",               
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ 𝙲𝙰𝙽𝙲𝙴𝙻 ✖️", callback_data="close")]])                                               
            )
        except:
            pass

def humanbytes(size):    
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'ʙ'


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "ᴅ, ") if days else "") + \
        ((str(hours) + "ʜ, ") if hours else "") + \
        ((str(minutes) + "ᴍ, ") if minutes else "") + \
        ((str(seconds) + "ꜱ, ") if seconds else "") + \
        ((str(milliseconds) + "ᴍꜱ, ") if milliseconds else "")
    return tmp[:-2] 

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)

async def send_log(b, u):
    if Config.LOG_CHANNEL is not None:
        curr = datetime.now(timezone("Asia/Kolkata"))
        date = curr.strftime('%d %B, %Y')
        time = curr.strftime('%I:%M:%S %p')
        await b.send_message(
            Config.LOG_CHANNEL,
            f"**--Nᴇᴡ Uꜱᴇʀ Sᴛᴀʀᴛᴇᴅ Tʜᴇ Bᴏᴛ--**\n\nUꜱᴇʀ: {u.mention}\nIᴅ: `{u.id}`\nUɴ: @{u.username}\n\nDᴀᴛᴇ: {date}\nTɪᴍᴇ: {time}\n\nBy: {b.mention}"
        )


def extract_video_duration(file_path):
    """Extracts the duration of the video."""
    metadata = extractMetadata(createParser(file_path))
    duration = 0
    if metadata and metadata.has("duration"):
        duration = metadata.get("duration").seconds
    return duration

app.on_message(filters.video | filters.document)
async def stream_remove(client, message):
    file_attr = getattr(message, message.media.value)
    filename = file_attr.file_name
    status = await message.reply("📥 Downloading…")

    file_path = await message.download(
        progress=progress_for_pyrogram,
        progress_args=("📥 Downloading…", status, time.time())
    )
    duration = extract_video_duration(file_path)

    await status.edit_text("🔍 Scanning streams…")

    streams = ffmpeg.probe(file_path)["streams"]

    # --- Decide which streams to KEEP ---------------------------
    keep_map = []

    # 1️⃣ first video stream
    first_video_idx = next(i for i, s in enumerate(streams) if s["codec_type"] == "video")
    keep_map.append(first_video_idx)

    # 2️⃣ Tamil audio (or first audio)
    audio_indices = [i for i, s in enumerate(streams) if s["codec_type"] == "audio"]
    tamil_idx = next((i for i in audio_indices
                      if s := streams[i].get("tags", {})
                      if s.get("language", "").lower() == "tam"), audio_indices[0])
    keep_map.append(tamil_idx)

    # 3️⃣ English subtitle if present
    eng_sub_idx = next((i for i, s in enumerate(streams)
                        if s["codec_type"] == "subtitle"
                        and s.get("tags", {}).get("language", "").lower() == "eng"),
                       None)
    if eng_sub_idx is not None:
        keep_map.append(eng_sub_idx)
    # ------------------------------------------------------------

    output_file = f"output_{os.path.basename(file_path)}"

    # Build the -map args: start from scratch, copy only wanted streams
    map_args = []
    for idx in keep_map:
        map_args.extend(["-map", f"0:{idx}"])

    await status.edit_text("⚙️ Running FFmpeg…")

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", file_path,
        *map_args, "-c", "copy",
        output_file
    )
    await proc.communicate()

    # Thumbnail (5-sec mark)
    thumb_path = tempfile.mktemp(suffix="_thumb.jpg")
    await asyncio.get_running_loop().run_in_executor(
        executor, take_screenshot, output_file, 5, thumb_path
    )
    if not os.path.exists(thumb_path):
        thumb_path = None

    caption = (f"Here is your processed file 🗃️🫡\n"
               f"File Name: {filename}")

    await status.edit_text("📤 Uploading…")

    await client.send_document(
        message.chat.id, output_file, caption=caption, thumb=thumb_path,
        progress=progress_for_pyrogram,
        progress_args=("📤 Uploading…", status, time.time())
    )

    # House-keeping
    for p in (file_path, output_file, thumb_path):
        if p and os.path.exists(p):
            os.remove(p)

    await status.edit_text("✅ Done!")

app.run()
