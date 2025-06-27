from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, render_template_string, request
from pymongo import MongoClient
from datetime import datetime
import threading
import random, string, io, asyncio, os

# ====================
# CONFIGURATION
# ====================
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
BASE_URL = "unlikely-atlanta-nahidbrow-2c574cde.koyeb.app/"  # ⚠️ এখানে তোমার Koyeb URL বসাও

# ====================
# INITIALIZE
# ====================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
flask_client = Client("flask", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = MongoClient(MONGO_URI)
db = mongo["streambot"]
links = db.links

# ====================
# HELPER: Generate ID
# ====================
def gen_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ====================
# BOT: /upload
# ====================
@bot.on_message(filters.command("upload") & filters.reply)
async def upload_file(c, m: Message):
    media = m.reply_to_message.document or m.reply_to_message.video
    if not media:
        return await m.reply("❌ Reply to a video/document file.")

    link_id = gen_id()
    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "created": datetime.utcnow()
    })

    url = f"{BASE_URL}/watch/{link_id}"
    await m.reply(f"🎬 Stream: {url}\n📥 Download: {url}?download=true")

# ====================
# WATCH PAGE
# ====================
@flask_app.route("/watch/<link_id>")
def watch_page(link_id):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h3 style='color:red'>Invalid or expired link</h3>", 404

    download_mode = request.args.get("download") == "true"
    if download_mode:
        return stream_file(link_id, as_download=True)

    stream_url = f"/stream/{link_id}"
    download_url = f"/watch/{link_id}?download=true"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎥 Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #000; color: #fff; font-family: sans-serif; text-align: center; padding: 10px; }}
            video {{ width: 95%; max-width: 800px; border-radius: 10px; }}
            .btn {{ margin: 10px; padding: 12px 25px; border-radius: 5px; background: orange; color: #000; text-decoration: none; display: inline-block; }}
        </style>
    </head>
    <body>
        <h2>🎬 Movie Stream</h2>
        <video controls>
            <source src="{stream_url}" type="video/mp4">
            Your browser does not support the video tag.
        </video><br/>

        <a class="btn" href="{stream_url}">🟢 MX Player</a>
        <a class="btn" href="{stream_url}">🟠 VLC</a>
        <a class="btn" href="{stream_url}">🟡 Play It</a>
        <a class="btn" href="{download_url}">⬇️ Download</a>

        <p style='margin-top:20px;'>Powered by MovieZone BD</p>
    </body>
    </html>
    """
    return html

# ====================
# STREAM FILE
# ====================
@flask_app.route("/stream/<link_id>")
def stream_file(link_id, as_download=False):
    data = links.find_one({"link_id": link_id})
    if not data:
        return "❌ Invalid Link", 404

    file_id = data["file_id"]
    file_io = io.BytesIO()

    async def download():
        await flask_client.start()
        await flask_client.download_media(file_id, file_name=file_io)
        await flask_client.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(download())
    loop.close()

    file_io.seek(0)
    return Response(
        file_io,
        mimetype="video/mp4",
        headers={"Content-Disposition": "attachment" if as_download else "inline"}
    )

# ====================
# START EVERYTHING
# ====================
def start_flask():
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    flask_client.start()
    threading.Thread(target=start_flask).start()
    bot.run()
