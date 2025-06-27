from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import threading
import random, string, os

# ========= CONFIG =========
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"  # without trailing slash

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_bot = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
links = db.links

# ========= UTIL =========
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ========= BOT =========
@bot.on_message(filters.document | filters.video)
async def handle_media(c, m: Message):
    media = m.document or m.video
    if not media:
        return

    link_id = gen_id()
    expiry = datetime.now(timezone.utc) + timedelta(days=3650)  # 10 years

    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "expiry": expiry,
        "created": datetime.now(timezone.utc)
    })

    watch_link = f"{BASE_URL}/watch/{link_id}"
    download_link = f"{BASE_URL}/stream/{link_id}"

    await m.reply(
        f"✅ Watch or Download your video:\n\n"
        f"▶️ Watch: {watch_link}\n"
        f"⬇️ Download: {download_link}"
    )

# ========= WEB: WATCH PAGE =========
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.now(timezone.utc) > data["expiry"]:
        return "<h2>❌ Invalid or expired link</h2>", 404

    stream_url = f"/stream/{link_id}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Movie Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #000; color: white; font-family: Arial; text-align: center; }}
            .btn {{ padding: 10px 20px; margin: 5px; background: orange; color: black; border: none; border-radius: 5px; }}
            iframe, video {{ width: 90%; max-width: 800px; margin-top: 20px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <h2>🎬 Movie Stream</h2>
        <video controls>
            <source src="{stream_url}" type="video/mp4">
            Your browser does not support HTML5 video.
        </video>
        <br><br>
        <a class="btn" href="{stream_url}" download>⬇️ Download</a>
        <a class="btn" href="vlc://{BASE_URL}{stream_url}">VLC Player</a>
        <a class="btn" href="intent:{BASE_URL}{stream_url}#Intent;package=com.mxtech.videoplayer.ad;end;">MX Player</a>
        <a class="btn" href="intent:{BASE_URL}{stream_url}#Intent;package=com.playit.videoplayer;end;">Play It</a>
    </body>
    </html>
    """
    return html

# ========= WEB: STREAM ROUTE =========
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.now(timezone.utc) > data["expiry"]:
        return "❌ Expired link", 410

    file_id = data["file_id"]
    temp_path = f"temp_{link_id}.mp4"

    if not os.path.exists(temp_path):
        flask_bot.download_media(file_id, file_name=temp_path)

    def generate():
        with open(temp_path, "rb") as f:
            while chunk := f.read(4096):
                yield chunk

    return Response(generate(), mimetype="video/mp4")

# ========= RUN =========
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
