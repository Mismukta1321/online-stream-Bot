from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime
import threading
import random, string, os

# 🔐 তোমার config
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"

# 🔧 initialize
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_bot = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
links = db.links

# 🔗 random ID generator
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ✅ অটো রেসপন্স: ভিডিও/ডকুমেন্ট দিলেই stream link তৈরি
@bot.on_message(filters.video | filters.document)
async def auto_save(c, m: Message):
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

# 🌐 ওয়াচ পেজ (ভিডিও প্লেয়ারসহ)
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h2 style='color:red'>❌ Invalid Link</h2>", 404

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>{{ title }}</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { background: #000; color: white; text-align: center; margin: 0; font-family: sans-serif; }
        .container { padding: 20px; }
        video { width: 95%; max-width: 800px; border-radius: 12px; margin-top: 20px; }
        .btn { display: inline-block; margin-top: 20px; background: #00f0ff; color: black; padding: 10px 20px; text-decoration: none; border-radius: 8px; }
      </style>
    </head>
    <body>
      <div class="container">
        <h2>{{ title }}</h2>
        <video controls autoplay>
          <source src="{{ stream_url }}" type="video/mp4">
          Your browser does not support the video tag.
        </video>
        <br>
        <a class="btn" href="{{ stream_url }}">⬇️ Direct Download</a>
      </div>
    </body>
    </html>
    '''
    return render_template_string(
        html,
        title="🎬 Movie Stream",
        stream_url=f"/stream/{link_id}"
    )

# 🔊 ভিডিও স্ট্রিম
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "❌ Invalid Link", 404

    file_id = data["file_id"]
    temp_path = f"temp_{link_id}.mp4"

    # ✅ ফাইল নাম দিয়ে ডাউনলোড
    flask_bot.download_media(file_id, file_name=temp_path)

    def generate():
        with open(temp_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="video/mp4")

# 🚀 একসাথে bot + flask চালাও
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
