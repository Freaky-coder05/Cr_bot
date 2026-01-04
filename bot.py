import re
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_ID =  24435985
API_HASH = "0fec896446625478537e43906a4829f8"
BOT_TOKEN = "7722665729:AAHDh8TAiv4uv9nfgwoBWZHexD1VEaCdx7Y"

BASE = "https://animepahe.si"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": BASE
})

app = Client(
    "animepahe_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= TEMP USER DATA =================
user_data = {}

# ================= HELPERS =================
def extract_anime_id(url):
    m = re.search(r"/anime/([a-f0-9\-]+)", url)
    return m.group(1) if m else None


def get_episodes(anime_id, page=1):
    url = f"{BASE}/api?m=release&id={anime_id}&sort=episode_asc&page={page}"
    r = session.get(url)
    return r.json()


def get_episode_page(anime_id, session_id):
    url = f"{BASE}/play/{anime_id}/{session_id}"
    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    return soup


# ================= COMMANDS =================
@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "Send AnimePahe series URL\n\nExample:\nhttps://animepahe.si/anime/xxxx"
    )


@app.on_message(filters.text & ~filters.command("link"))
async def receive_url(_, msg):
    anime_id = extract_anime_id(msg.text.strip())
    if not anime_id:
        return await msg.reply_text("❌ Invalid AnimePahe series URL")

    user_data[msg.chat.id] = {
        "anime_id": anime_id,
        "page": 1
    }

    await show_episode_list(msg.chat.id, msg)


# ================= EPISODE LIST =================
async def show_episode_list(chat_id, msg, page=1):
    anime_id = user_data[chat_id]["anime_id"]
    data = get_episodes(anime_id, page)

    buttons = []
    for ep in data["data"]:
        buttons.append([
            InlineKeyboardButton(
                f"Episode {ep['episode']}",
                callback_data=f"ep_{ep['episode']}_{ep['session']}"
            )
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅", callback_data=f"page_{page-1}"))
    if page < data["last_page"]:
        nav.append(InlineKeyboardButton("➡", callback_data=f"page_{page+1}"))
    if nav:
        buttons.append(nav)

    await msg.reply_text(
        f"Select Episode (Page {page}/{data['last_page']})",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= CALLBACKS =================
@app.on_callback_query(filters.regex("^page_"))
async def page_cb(_, cq):
    page = int(cq.data.split("_")[1])
    user_data[cq.message.chat.id]["page"] = page
    await cq.message.delete()
    await show_episode_list(cq.message.chat.id, cq.message, page)


@app.on_callback_query(filters.regex("^ep_"))
async def episode_cb(_, cq):
    _, ep_no, session_id = cq.data.split("_")
    anime_id = user_data[cq.message.chat.id]["anime_id"]

    soup = get_episode_page(anime_id, session_id)

    links = soup.select("#pickDownload a")
    if not links:
        return await cq.message.reply_text("❌ No download links found")

    buttons = []
    for link in links:
        buttons.append([
            InlineKeyboardButton(
                link.text.strip(),
                url=link["href"]
            )
        ])

    await cq.message.reply_text(
        f"Episode {ep_no} Download Links:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= RUN =================
app.run()
