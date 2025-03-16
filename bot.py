import os
import asyncio
import libtorrent as lt
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def download_torrent(magnet_link):
    """Download the torrent file using libtorrent."""
    session = lt.session()
    session.listen_on(6881, 6891)

    params = {
        "save_path": DOWNLOAD_DIR,
        "storage_mode": lt.storage_mode_t.storage_mode_sparse
    }

    # Add torrent from magnet link
    handle = lt.add_magnet_uri(session, magnet_link, params)
    session.start_dht()

    print("Fetching metadata...")
    while not handle.has_metadata():
        await asyncio.sleep(1)

    print("Downloading started!")
    while not handle.is_seed():
        status = handle.status()
        progress = status.progress * 100
        download_speed = status.download_rate / 1024  # Convert to KB/s
        print(f"Progress: {progress:.2f}% | Speed: {download_speed:.2f} KB/s")
        await asyncio.sleep(2)

    print("Download completed!")
    return handle.save_path()


@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Send me a magnet link to start downloading!")


@app.on_message(filters.text & filters.private)
async def handle_magnet(client, message):
    """Handles magnet links."""
    magnet_link = message.text
    if magnet_link.startswith("magnet:?"):
        await message.reply_text("Downloading started... Please wait!")
        
        file_path = await download_torrent(magnet_link)
        files = os.listdir(file_path)

        for file in files:
            full_path = os.path.join(file_path, file)
            await message.reply_document(full_path, caption="✅ Download Complete!")


if __name__ == "__main__":
    print("🚀 Starting Torrent Bot without aria2...")
    app.run()
