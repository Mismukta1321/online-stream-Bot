from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import random
import string
import io

# ==============================
# 🔐 CONFIGURATION
# ==============================
API_ID = 22697010  # তোমার API_ID
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"  # তোমার API_HASH
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"  # তোমার BOT_TOKEN
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"  # তোমার MongoDB URI
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"  # তোমার ডোমেইন, https:// সহ

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
# 🤖 BOT HANDLER: যেকোনো ফাইল আসলে অটোমেটিক লিংক তৈরি করবে
# ==============================
@bot.on_message(filters.private & (filters.document | filters.video))
async def auto_upload(c, m: Message):
    media = m.document or m.video
    if not media:
        return

    link_id = gen_id()
    expiry = datetime.utcnow() + timedelta(days=3650)  # 10 বছর; তুমি চাইলে কমাতে পারো

    # ডাটাবেজে সেভ করো
    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "expiry": expiry,
        "file_name": media.file_name if hasattr(media, "file_name") else "file"
    })

    stream_link = f"{BASE_URL}/watch/{link_id}"

    await m.reply(
        f"✅ Stream & Download link created!\n\n"
        f"▶️ Watch/Play: {stream_link}\n"
        f"⬇️ Download: {stream_link}\n\n"
        f"⏰ Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

# ==============================
# 🌐 FLASK: Watch page with updated player buttons & ads space
# ==============================
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h2 style='color:red; text-align:center;'>❌ Invalid Link</h2>", 404
    if datetime.utcnow() > data["expiry"]:
        return "<h2 style='color:orange; text-align:center;'>⚠️ This link has expired</h2>", 410

    stream_url = f"/stream/{link_id}"
    full_watch_url = f"{BASE_URL}/watch/{link_id}"
    expiry_str = data["expiry"].strftime("%Y-%m-%d %H:%M UTC")

    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{{ title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      background: #000;
      color: #fff;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      text-align: center;
      margin: 0;
      padding: 10px;
    }
    .container {
      max-width: 900px;
      margin: auto;
    }
    video {
      width: 100%;
      max-width: 850px;
      border-radius: 12px;
      border: 2px solid #444;
      margin: 15px 0;
      background: black;
    }
    .buttons {
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 15px;
      margin-bottom: 20px;
    }
    .btn {
      background: #f90;
      color: black;
      border: none;
      padding: 12px 25px;
      font-weight: bold;
      border-radius: 8px;
      cursor: pointer;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.3s ease;
    }
    .btn:hover {
      background: #e07b00;
    }
    .btn svg {
      width: 20px;
      height: 20px;
      fill: black;
    }
    .footer {
      margin-top: 40px;
      font-size: 0.9rem;
      color: #888;
    }
    .ads {
      margin-top: 30px;
      background: #111;
      padding: 10px;
      border-radius: 8px;
      color: #ccc;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>{{ title }}</h1>
    
    <video controls controlsList="nodownload" preload="metadata">
      <source src="{{ stream_url }}" type="video/mp4" />
      Your browser does not support the video tag.
    </video>
    
    <div class="buttons">
      <a href="mxplayer://{{ stream_url }}" class="btn" target="_blank" rel="noopener noreferrer" title="Open in MX Player">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 22v-20l18 10-18 10z"/>
        </svg>
        MX Player
      </a>

      <a href="vlc://{{ stream_url }}" class="btn" target="_blank" rel="noopener noreferrer" title="Open in VLC Player">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2l6 18h-12l6-18z"/>
        </svg>
        VLC Player
      </a>
      
      <a href="{{ stream_url }}" class="btn" target="_blank" rel="noopener noreferrer" title="Play in Browser">
        ▶️ Play it
      </a>

      <a href="{{ stream_url }}" download class="btn" title="Download Video">
        ⬇️ Download
      </a>
      
      <a href="https://t.me/share/url?url={{ full_watch_url }}&text=Watch this video" target="_blank" class="btn" title="Share Link">
        📤 Share Now
      </a>
    </div>

    <div class="ads">
      <!-- এখানে গুগল বা অন্য কোনো এড কোড বসাতে পারবে -->
      <p>🔥 Your Ad Here! Replace this with your AdSense or other ads code.</p>
    </div>

    <p>⏰ This link will expire on: {{ expiry }}</p>

    <div class="footer">
      <small>© YourSiteName | Powered by YourBot</small>
    </div>
  </div>
</body>
</html>
    '''

    return render_template_string(
        html,
        title="🎬 Movie Stream",
        stream_url=stream_url,
        expiry=expiry_str,
        full_watch_url=full_watch_url
    )

# ==============================
# 🔊 STREAM FILE route: ভিডিও ডাউনলোড ও স্ট্রিম করার জন্য
# ==============================
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.utcnow() > data["expiry"]:
        return "⚠️ Link expired or invalid", 410

    file_id = data["file_id"]
    file_io = io.BytesIO()
    flask_bot.download_media(file_id, file_io)
    file_io.seek(0)
    return Response(file_io, mimetype="video/mp4")

# ==============================
# 🚀 START EVERYTHING
# ==============================
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
