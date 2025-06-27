from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import threading
import random, string, tempfile, os

# ==============================
# 🔐 CONFIGURATION
# ==============================
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"  # ⚠️ HTTPS সহ দিতে ভুলবে না

# ==============================
# ⚙️ INITIALIZATION
# ==============================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
flask_bot = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
links = db.links

# ==============================
# 🔗 HELPER: generate random ID
# ==============================
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ==============================
# 🤖 BOT COMMAND: handle all media
# ==============================
@bot.on_message(filters.document | filters.video)
async def upload_file(c, m: Message):
    media = m.document or m.video
    if not media:
        return

    link_id = gen_id()
    expiry = datetime.now(timezone.utc) + timedelta(days=3650)  # 10 বছর

    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "expiry": expiry,
        "created": datetime.now(timezone.utc)
    })

    stream_link = f"{BASE_URL}/watch/{link_id}"
    await m.reply(
        f"🔗 <b>Watch:</b> {stream_link}\n"
        f"⬇️ <b>Direct Download:</b> {BASE_URL}/stream/{link_id}",
        quote=True,
        parse_mode="html"
    )

# ==============================
# 🌐 FLASK: Stream Page with HTML Template
# ==============================
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h2 style='color:red'>❌ Invalid Link</h2>", 404
    if datetime.now(timezone.utc) > data["expiry"]:
        return "<h2 style='color:orange'>⚠️ This link has expired</h2>", 410

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>{{ title }}</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { background: #000; color: white; font-family: sans-serif; text-align: center; margin: 0; }
        .container { padding: 15px; }
        video, iframe { width: 95%; max-width: 800px; margin: 20px 0; border: 2px solid #333; border-radius: 10px; }
        .ads { margin-top: 20px; }
        .btn { background: #f90; color: black; padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; display:inline-block; text-decoration:none; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>{{ title }}</h1>

        <video controls>
          <source src="{{ stream_url }}" type="video/mp4">
          Your browser does not support the video tag.
        </video>

        <div>
          <a class="btn" href="{{ stream_url }}" download>⬇️ Download</a>
          <a class="btn" href="vlc://{{ stream_url }}">📺 Open in VLC</a>
          <a class="btn" href="intent://{{ stream_url }}#Intent;package=com.mxtech.videoplayer.ad;end">📱 MX Player</a>
        </div>

        <div class="ads">
          <p>🔗 Support Us:</p>
          <iframe src="https://youradserver.com/ad.html" height="90"></iframe>
        </div>
      </div>
    </body>
    </html>
    '''
    return render_template_string(
        html,
        title="🎬 Stream Movie",
        stream_url=f"/stream/{link_id}"
    )

# ==============================
# 🔊 STREAM FILE route
# ==============================
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.now(timezone.utc) > data["expiry"]:
        return "⚠️ Link expired", 410

    file_id = data["file_id"]
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        flask_bot.download_media(file_id, tmp.name)
        tmp.seek(0)
        return Response(open(tmp.name, "rb"), mimetype="video/mp4")

# ==============================
# 🚀 START EVERYTHING
# ==============================
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
