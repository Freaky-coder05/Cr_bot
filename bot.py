import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
import config

# Initialize the bot
bot = Client(
    "crunchyroll_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Helper function to calculate and send progress
def progress(current, total, message: Message, action: str):
    percent = (current / total) * 100
    message_text = f"{action}... {percent:.1f}% completed"
    message.edit(message_text)

# Command handler for /start
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello! Use /rip <Crunchyroll URL> <username> <password> to download a video in 240p.")

# Command handler for /rip
@bot.on_message(filters.command("rip"))
async def rip_video(client, message):
    args = message.command[1:]
    
    if len(args) < 3:
        await message.reply("Please provide the Crunchyroll URL, username, and password!")
        return

    url, username, password = args[0], args[1], args[2]
    await handle_download(message, url, username, password)

# Function to handle video downloading and uploading
async def handle_download(message: Message, url: str, username: str, password: str):
    await message.reply("Preparing to download video in 240p...")

    output_file = "output_240p.mp4"
    command = [
        "N_m3u8DL-RE", url, 
        "--save-dir", ".", 
        "--save-name", "output_240p",
        "--auto-select",
        "--user", username,
        "--password", password,
        "--max-quality", "240p"  # Setting to download in 240p
    ]
    
    try:
        # Run the command and track progress
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        while True:
            line = process.stdout.readline()
            if not line:
                break

            # Parse progress from the tool output
            line = line.decode("utf-8").strip()
            if "Progress" in line:
                progress_info = line.split()
                progress_percent = progress_info[1].strip("%")
                await message.edit(f"Download Progress: {progress_percent}%")

        process.wait()
        
        if os.path.exists(output_file):
            await message.reply("Uploading video...")
            video_message = await message.reply_video(
                output_file,
                progress=progress,
                progress_args=("Uploading", message)
            )
            os.remove(output_file)
        else:
            await message.reply("Video download failed, please try again.")
        
    except subprocess.CalledProcessError as e:
        await message.reply(f"Failed to download the video. Error: {str(e)}")
    except Exception as e:
        await message.reply(f"An unexpected error occurred: {str(e)}")

# Run the bot
bot.run()
