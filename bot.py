from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string, send_file
from pymongo import MongoClient
from datetime import datetime
import threading
import random, string, os

# ==============================
# 🔐 CONFIGURATION
# ==============================
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"

# ==============================
# ⚙️ INITIALIZATION
# ==============================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_bot = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
links = db.links

# ==============================
# 🔗 HELPER: generate random ID
# ==============================
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ==============================
# 🤖 BOT: Auto-generate link when file is sent
# ==============================
@bot.on_message(filters.video | filters.document)
async def auto_generate_link(c, m: Message):
    media = m.video or m.document
    if not media:
        return

    link_id = gen_id()
    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "created": datetime.utcnow()
    })

    watch_url = f"{BASE_URL}/watch/{link_id}"
    direct_url = f"{BASE_URL}/stream/{link_id}"

    await m.reply(
        f"✅ **Stream & Download Ready!**\n\n"
        f"▶️ Watch: [Click Here]({watch_url})\n"
        f"⬇️ Download: [Click Here]({direct_url})",
        disable_web_page_preview=True
    )

# ==============================
# 🌐 HTML Stream Page with Multiple Players & Ads
# ==============================
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h2 style='color:red'>❌ Invalid Link</h2>", 404

    stream_url = f"/stream/{link_id}"

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <title>{{ title }}</title>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>
        body { background: #000; color: #eee; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }
        .container { max-width: 900px; margin: auto; padding: 20px; text-align: center; }
        h1 { margin-bottom: 20px; }
        .player { margin-bottom: 30px; border-radius: 12px; overflow: hidden; box-shadow: 0 0 15px #0ff; }
        video, iframe { width: 100%; height: 400px; background: #000; border: none; }
        .ads { background: #111; padding: 15px; margin: 30px 0; border-radius: 12px; }
        .ads h3 { margin-top: 0; }
        .ads img { max-width: 100%; border-radius: 8px; }
        .btn-download {
          display: inline-block;
          padding: 12px 25px;
          margin-top: 10px;
          background: #00f0ff;
          color: #000;
          text-decoration: none;
          border-radius: 8px;
          font-weight: bold;
          font-size: 1.1rem;
        }
        @media (max-width: 600px) {
          video, iframe { height: 250px; }
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>{{ title }}</h1>

        <!-- Player 1: HTML5 Video -->
        <div class="player">
          <video controls autoplay>
            <source src="{{ stream_url }}" type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>

        <!-- Player 2: VLC Plugin fallback (if browser supports) -->
        <!-- (Optional, many modern browsers don't support this plugin) -->
        <!--
        <div class="player">
          <embed type="application/x-vlc-plugin" pluginspage="http://www.videolan.org" width="100%" height="400" id="vlc" />
        </div>
        -->

        <!-- Player 3: Iframe with direct video URL (for external players or apps) -->
        <div class="player">
          <iframe src="{{ stream_url }}" allowfullscreen></iframe>
        </div>

        <!-- Download Button -->
        <a href="{{ stream_url }}" class="btn-download" download>⬇️ Download Video</a>

        <!-- Advertisement Section -->
        <div class="ads">
          <h3>🎉 Support Us</h3>
          <p>আপনি চাইলে এখানে গুগল এডসেন্স বা অন্য কোনো বিজ্ঞাপন কোড বসাতে পারেন।</p>

          <!-- Example Ad Banner -->
          <a href="https://your-sponsor-site.com" target="_blank" rel="noopener">
            <img src="https://via.placeholder.com/728x90.png?text=Your+Ad+Here" alt="Sponsor Ad Banner" />
          </a>

          <!-- Example iframe ad (comment/uncomment as needed) -->
          <!-- <iframe src="https://your-ad-network.com/adframe" width="728" height="90" style="border:none;"></iframe> -->
        </div>
      </div>
    </body>
    </html>
    '''
    return render_template_string(
        html,
        title="🎬 Movie Stream",
        stream_url=stream_url
    )

# ==============================
# 🔊 STREAM VIDEO FILE
# ==============================
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "❌ Invalid Link", 404

    file_id = data["file_id"]
    temp_path = f"/tmp/stream_{link_id}.mp4"

    if not os.path.exists(temp_path):
        flask_bot.download_media(file_id, file_name=temp_path)

    return send_file(
        temp_path,
        mimetype='video/mp4',
        conditional=True,
        as_attachment=False
    )

# ==============================
# 🚀 START APP
# ==============================
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
