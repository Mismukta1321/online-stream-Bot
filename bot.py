from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import threading
import os, random, string, asyncio
import io

# -------------------- Configuration --------------------
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
DB_NAME = "streambot"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"

# -------------------- Initialize --------------------
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
flask_bot = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
links = db.links

# -------------------- Helper --------------------
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# -------------------- Upload Command --------------------
@bot.on_message(filters.command("upload") & filters.reply)
async def upload_file(c, m: Message):
    media = m.reply_to_message.document or m.reply_to_message.video
    if not media:
        return await m.reply("❌ Reply to a video or document file.")

    link_id = gen_id()
    expiry = datetime.now(timezone.utc) + timedelta(days=3650)

    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "expiry": expiry,
        "created": datetime.now(timezone.utc)
    })

    stream_link = f"{BASE_URL}/watch/{link_id}"
    await m.reply(
        f"✅ **Watch:** {stream_link}\n"
        f"📥 **Download:** {BASE_URL}/stream/{link_id}\n"
        f"♾️ Valid for lifetime"
    )

# -------------------- Watch Page --------------------
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h3>❌ Invalid or deleted link.</h3>", 404
    if datetime.now(timezone.utc) > data["expiry"]:
        return "<h3>⚠️ This link has expired.</h3>", 410

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎬 Movie Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #000; color: white; text-align: center; font-family: sans-serif; }}
            video {{ width: 90%; max-width: 800px; margin-top: 20px; border-radius: 10px; }}
            .btns a {{ display: inline-block; margin: 8px; background: #f90; padding: 10px 20px; border-radius: 5px; color: black; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🎬 Now Streaming</h1>
        <video controls>
            <source src="/stream/{link_id}" type="video/mp4">
        </video>
        <div class="btns">
            <a href="/stream/{link_id}" download>⬇️ Download</a>
            <a href="intent://stream/{link_id}#Intent;package=com.mxtech.videoplayer.ad;scheme=https;end">MX Player</a>
            <a href="intent://stream/{link_id}#Intent;package=org.videolan.vlc;scheme=https;end">VLC</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

# -------------------- Stream (Fixed: with BytesIO) --------------------
@flask_app.route("/stream/<link_id>")
def stream_file(link_id):
    data = links.find_one({"link_id": link_id})
    if not data or datetime.now(timezone.utc) > data["expiry"]:
        return "❌ Link expired", 410

    file_id = data["file_id"]
    file_stream = io.BytesIO()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(flask_bot.download_media(file_id, file_name=file_stream))
        file_stream.seek(0)
    except Exception as e:
        return f"❌ Download error: {str(e)}", 500
    finally:
        loop.close()

    return Response(file_stream, mimetype="video/mp4")

# -------------------- Start Everything --------------------
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_bot.start()
    threading.Thread(target=run_flask).start()
    bot.run()
