
import re
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_ID = 24435985
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7722665729:AAHDh8TAiv4uv9nfgwoBWZHexD1VEaCdx7Y"

BASE = "https://animepahe.si"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE
})

app = Client(
    "animepahe_bs4_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= USER DATA =================
user_data = {}

# ================= HELPERS =================
def extract_anime_id(url: str):
    m = re.search(r"/anime/([a-f0-9\-]+)", url)
    return m.group(1) if m else None


def scrape_episode_list(anime_id: str):
    """
    Scrape episode list from AnimePahe play page using BS4
    """
    url = f"{BASE}/anime/{anime_id}"
    r = session.get(url, timeout=20)

    if r.status_code != 200:
        raise RuntimeError("Failed to load anime page")

    soup = BeautifulSoup(r.text, "html.parser")

    episodes = []
    for a in soup.select("a[href^='/play/']"):
        href = a.get("href")
        text = a.get_text(strip=True)

        # Example: /play/<anime_id>/<session>
        m = re.search(r"/play/.+?/([a-f0-9]+)", href)
        if not m:
            continue

        session_id = m.group(1)

        # Try to extract episode number
        ep_match = re.search(r"Episode\s*(\d+)", text, re.I)
        ep_no = ep_match.group(1) if ep_match else "?"

        episodes.append((ep_no, session_id))

    if not episodes:
        raise RuntimeError("No episodes found (page structure changed)")

    # Remove duplicates & sort
    episodes = list(dict.fromkeys(episodes))
    return episodes


# ================= COMMANDS =================
@app.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    await msg.reply_text(
        "📺 Send AnimePahe series URL\n\n"
        "Example:\nhttps://animepahe.si/anime/xxxxxxxx"
    )


@app.on_message(filters.text & ~filters.command())
async def receive_series_url(_, msg):
    anime_id = extract_anime_id(msg.text.strip())
    if not anime_id:
        return await msg.reply_text("❌ Invalid AnimePahe series URL")

    try:
        episodes = scrape_episode_list(anime_id)
    except Exception as e:
        return await msg.reply_text(f"❌ {e}")

    user_data[msg.chat.id] = anime_id

    buttons = [
        [InlineKeyboardButton(f"Episode {ep}", callback_data=f"ep_{ep}_{sid}")]
        for ep, sid in episodes
    ]

    await msg.reply_text(
        "🎬 Select Episode:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= CALLBACK =================
@app.on_callback_query(filters.regex("^ep_"))
async def episode_callback(_, cq):
    cq.answer()
    _, ep_no, session_id = cq.data.split("_")
    anime_id = user_data.get(cq.message.chat.id)

    if not anime_id:
        return await cq.message.reply_text("❌ Session expired. Send series URL again.")

    episode_url = f"{BASE}/play/{anime_id}/{session_id}"

    await cq.message.reply_text(
        f"✅ Episode {ep_no} URL:\n\n{episode_url}"
    )


# ================= RUN =================
app.run()
