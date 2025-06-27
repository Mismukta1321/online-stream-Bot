from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import random, string, io

# ==============================
# 🔐 CONFIGURATION
# ==============================
API_ID = 22697010  # Replace with your API ID
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://yourdomain.com"  # example: https://moviezone.stream

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
# 🤖 BOT COMMAND: /upload
# ==============================
@bot.on_message(filters.command("upload") & filters.reply)
async def upload_file(c, m: Message):
    media = m.reply_to_message.document or m.reply_to_message.video
    if not media:
        return await m.reply("❌ Reply to a video/document file.")

    link_id = gen_id()
    expiry = datetime.utcnow() + timedelta(days=7)

    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "expiry": expiry
    })

    stream_link = f"{BASE_URL}/watch/{link_id}"
    await m.reply(
        f"✅ Your stream link:\n{stream_link}\n\n"
        f"🕒 Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )

# ==============================
# 🌐 FLASK: Stream Page with HTML Template
# ==============================
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h2 style='color:red'>❌ Invalid Link</h2>", 404
    if datetime.utcnow() > data["expiry"]:
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
        .expired { color: red; font-size: 20px; margin-top: 40px; }
        .btn { background: #f90; color: black; padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>{{ title }}</h1>
        <video controls>
          <source src="{{ stream_url }}" type="video/mp4">
          Your browser does not support the video tag.
        </video>

        <div class="ads">
          <p>🔗 Watch in App or Support Us:</p>
          <a href="https://youradlink.com" target="_blank" class="btn">Open in App</a>
          <iframe src="https://youadserver.com/ad.html" height="100"></iframe>
        </div>

        <p>⏰ This link will expire on: {{ expiry }}</p>
      </div>
    </body>
    </html>
    '''
    return render_template_string(
        html,
        title="🎬 Movie Stream",
        stream_url=f"/stream/{link_id}",
        expiry=data["expiry"].strftime("%Y-%m-%d %H:%M UTC")
    )

# ==============================
# 🔊 STREAM FILE route
# ==============================
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.utcnow() > data["expiry"]:
        return "⚠️ Link expired", 410

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
