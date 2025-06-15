from pyrogram import Client,filters
import asyncio
import os
from config import API_ID, API_HASH, BOT_TOKEN

app=Client("merger",api_id=API_ID,api_hash=API_HASH,bot_token=BOT_TOKEN)

audio_files=[]
video_files=[]

episode_num=1

app.on_message(filters.video | filters.document|filters.audio)
async def media_hadler (client,message):
    if message.video or message.document:
        video_files.append(message)
    elif message.audio:
        audio_files.append(message)
    else:
        await message.reply_text("Unknown File Format")


app.on_message(filters.command('start_process'))
async def progress_handler(client,message):
    global episode_num
    if len(audio_files)==0 or len(video_files)<3:
        await message.reply_text("Not enough files to start the process")
    audio_man=audio_files.pop(0)
    ms=await message.reply_text("Downloading audio file")
    down_aud= audio_files.download(file_name=f"audio_ep{episode_num}.mp3")

    for i in range (3):
        video_man=video_files.pop(0)
        await ms.edit("Downloading video file")
        down_vid=video_files.download(file_name=f"Anime ep{episode_num} {i+1}.mp4")
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
        os.remove(video_files)
    
    os.remove(audio_files)
    episode_num +=1

app.on_message(filters.command('start'))
async def start_message(client,message):
    await message.reply_text("Hi Friends I am a automatic video+audio merge bot")


app.run()
