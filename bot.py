from pyrogram import Client,filters
import asyncio
import os
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

app=Client("merger",api_id=API_ID,api_hash=API_HASH,bot_token=BOT_TOKEN)

audio_files=[]
video_files=[]
channel_list = {}
selected_channel = None
episode_num=1

@app.on_message(filters.video | filters.document|filters.audio)
async def media_hadler (client,message):
    if message.video or message.document:
        video_files.append(message)
    elif message.audio:
        audio_files.append(message)
    else:
        await message.reply_text("Unknown File Format")


@app.on_message(filters.command('start_process'))
async def progress_handler(client,message):
    global episode_num
    if len(audio_files)==0 or len(video_files)<3:
        await message.reply_text("Not enough files to start the process")

    while len(audio_files)>0 and len(video_files)>=3 :
        audio_man=audio_files.pop(0)
        ms=await message.reply_text("Downloading audio file")
        down_aud= await audio_man.download(file_name=f"audio_ep{episode_num}.mp3")

        for i in range (3):
            video_man=video_files.pop(0)
            await ms.edit("Downloading video file")
            down_vid = await video_man.download(file_name=f"Anime ep{episode_num} {i+1}.mp4")
            output_file=f"Ep{episode_num}-{['480p','720p','1080p'][i]}.mkv"

            await ms.edit("adding vide+audio...")

            process= await asyncio.create_subprocess_exec( 
            'ffmpeg',
            '-y',
            '-i', down_vid, 
            '-i',  down_aud, 
            '-c:v', 'copy', 
            '-c:a', 'copy', 
            '-map', '0:v:0', 
            '-map', '1:a:0', 
             output_file,
             stdout=asyncio.subprocess.DEVNULL,
             stderr=asyncio.subprocess.DEVNULL)
            await process.communicate()
            await ms.edit("uploading your file")
            await message.reply_video(output_file)
            os.remove(down_vid)
    
        os.remove(down_aud)
        episode_num +=1




@app.on_message(filters.command("add_channel"))
async def add_channel(client, message):
    await message.reply("Please forward a message from the channel you want to add.")



@app.on_message(filters.forwarded)
async def handle_forwarded(client, message):
    global channel_list

    if not message.forward_from_chat:
        await message.reply("This doesn't seem to be from a channel.")
        return

    chat_id = message.forward_from_chat.id

    chat = message.forward_from_chat
    chat_id = chat.id
    title = chat.title or "Unknown Title"
    channel_list[chat_id] = chat.title
    await message.reply(f"✅ Channel '{chat.title}' added!")

@app.on_message(filters.command("view_channels"))
async def view_channels(client, message):
    global channel_list, selected_channel

    if not channel_list:
        await message.reply("No channels added yet.")
        return

    buttons = []
    for cid, name in channel_list.items():
        check = "✅ " if selected_channel == cid else ""
        buttons.append([InlineKeyboardButton(f"{check}{name}", callback_data=f"select_{cid}")])

    buttons.append([InlineKeyboardButton("➕ Add", callback_data="add"), InlineKeyboardButton("🗑️ Delete", callback_data="delete")])
    await message.reply("Select a channel:", reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query()
async def callback_handler(client, callback):
    global selected_channel, channel_list

    data = callback.data

    if data.startswith("select_"):
        cid = int(data.split("_")[1])
        selected_channel = cid
        await callback.message.edit_text("Channel selected!", reply_markup=await get_channel_buttons())
    elif data == "delete":
        if selected_channel and selected_channel in channel_list:
            del channel_list[selected_channel]
            selected_channel = None
            await callback.message.edit_text("Channel deleted.", reply_markup=await get_channel_buttons())
    elif data == "add":
        await callback.message.edit_text("Use /add_channel and forward a channel message to add.")

    await callback.answer()


async def get_channel_buttons():
    global channel_list, selected_channel
    buttons = []
    for cid, name in channel_list.items():
        check = "✅ " if selected_channel == cid else ""
        buttons.append([InlineKeyboardButton(f"{check}{name}", callback_data=f"select_{cid}")])
    buttons.append([InlineKeyboardButton("➕ Add", callback_data="add"), InlineKeyboardButton("🗑️ Delete", callback_data="delete")])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command('start'))
async def start_message(client,message):
    await message.reply_text("Hi Friends I am a automatic video+audio merge bot")


app.run()
