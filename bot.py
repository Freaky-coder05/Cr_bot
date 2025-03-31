import os
import asyncio
import whisper
import noisereduce as nr
import numpy as np
import soundfile as sf
from pyrogram import Client, filters
from pyrogram.types import Message
from googletrans import Translator
from TTS.api import TTS
from pydub import AudioSegment
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

bot = Client("TamilDubBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load Whisper Model for STT
whisper_model = whisper.load_model("small")  # Choose from tiny, small, medium, large

# Load Coqui TTS with a Tamil cloned voice
tts_model = TTS("tts_models/multilingual/multi-dataset/your_clone_voice_model")

translator = Translator()

async def extract_audio(video_path):
    """Extract audio from a video file."""
    audio_path = video_path.replace(".mp4", ".wav")
    os.system(f'ffmpeg -i "{video_path}" -q:a 0 -map a "{audio_path}"')
    return audio_path

async def add_dubbed_audio(video_path, dubbed_audio_path, output_path):
    """Merge dubbed Tamil audio with the original video."""
    os.system(f'ffmpeg -i "{video_path}" -i "{dubbed_audio_path}" -c:v copy -c:a aac "{output_path}"')
    return output_path

async def reduce_noise(audio_path):
    """Reduce background noise in the audio."""
    data, rate = sf.read(audio_path)
    reduced_noise = nr.reduce_noise(y=data, sr=rate)
    cleaned_audio_path = audio_path.replace(".wav", "_clean.wav")
    sf.write(cleaned_audio_path, reduced_noise, rate)
    return cleaned_audio_path

@bot.on_message(filters.voice | filters.audio | filters.video)
async def process_media(client, message: Message):
    msg = await message.reply_text("🔄 Processing media...")

    # Download file
    file_path = await message.download()

    # If it's a video, extract audio
    if message.video:
        file_path = await extract_audio(file_path)

    # Reduce noise in audio
    cleaned_audio = await reduce_noise(file_path)

    # Convert to WAV if needed
    audio = AudioSegment.from_file(cleaned_audio)
    wav_path = cleaned_audio.replace(cleaned_audio.split('.')[-1], "wav")
    audio.export(wav_path, format="wav")

    # Transcribe audio
    result = whisper_model.transcribe(wav_path)
    transcript = result["text"]
    
    await msg.edit_text(f"🎙️ Detected Speech: `{transcript}`")

    # Translate to Tamil
    translated_text = translator.translate(transcript, src="auto", dest="ta").text

    await msg.edit_text(f"📝 Tamil Translation: `{translated_text}`")

    # Generate Tamil voice with cloned voice
    dubbed_audio_path = wav_path.replace(".wav", "_tamil.wav")
    tts_model.tts_to_file(text=translated_text, file_path=dubbed_audio_path)

    # If it's a video, merge back
    if message.video:
        output_video_path = file_path.replace(".mp4", "_tamil.mp4")
        await add_dubbed_audio(message.video.file_name, dubbed_audio_path, output_video_path)
        await message.reply_video(video=output_video_path, caption="🎬 Tamil Dubbed Video")
        os.remove(output_video_path)
    else:
        await message.reply_audio(audio=dubbed_audio_path, caption="🔊 Tamil Dubbed Audio")

    # Cleanup
    os.remove(file_path)
    os.remove(cleaned_audio)
    os.remove(wav_path)
    os.remove(dubbed_audio_path)

    await msg.delete()

# Run the bot
bot.run()
