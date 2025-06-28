import os
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, request
from pymongo import MongoClient
from datetime import datetime
import random
import string
import asyncio
from flask_cors import CORS

# ====================
# CONFIGURATION (এনভায়রনমেন্ট ভেরিয়েবল ব্যবহার করা ভালো প্র্যাকটিস)
# ====================
API_ID = int(os.getenv("API_ID", 22697010))
API_HASH = os.getenv("API_HASH", "fd88d7339b0371eb2a9501d523f3e2a7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
BASE_URL = os.getenv("BASE_URL", "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app")

# ====================
# INITIALIZATION
# ====================
# Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজ
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# স্ট্রিমিং এর জন্য আলাদা ক্লায়েন্ট
stream_client = Client(
    "stream_client",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Flask অ্যাপ ইনিশিয়ালাইজ
app = Flask(__name__)
CORS(app)  # CORS এনাবল

# MongoDB ক্লায়েন্ট
mongo = MongoClient(MONGO_URI)
db = mongo["streambot"]
links = db["links"]

# ====================
# HELPER FUNCTIONS
# ====================
def generate_id(length=10):
    """র্যান্ডম আলফানিউমেরিক ID জেনারেট করে"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ====================
# BOT COMMANDS
# ====================
@bot.on_message(filters.command("upload") & filters.reply)
async def handle_upload(client, message: Message):
    """
    ফাইল আপলোড এবং স্ট্রিমিং লিঙ্ক জেনারেট করে
    """
    if not message.reply_to_message:
        return await message.reply("❌ Please reply to a file with this command")

    media = (
        message.reply_to_message.document or 
        message.reply_to_message.video or 
        message.reply_to_message.audio
    )
    
    if not media:
        return await message.reply("❌ Unsupported file type")

    # ডেটাবেসে লিঙ্ক সেভ করুন
    link_id = generate_id()
    file_name = getattr(media, "file_name", None) or "file"
    
    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "file_name": file_name,
        "mime_type": media.mime_type,
        "created_at": datetime.utcnow()
    })

    # ইউজারকে লিঙ্ক পাঠান
    url = f"{BASE_URL}/watch/{link_id}"
    await message.reply(
        f"**✅ File uploaded successfully!**\n\n"
        f"📁 File: {file_name}\n"
        f"🔗 Stream URL: {url}\n"
        f"⬇️ Download URL: {url}?download=true"
    )

# ====================
# FLASK ROUTES
# ====================
@app.route("/watch/<link_id>")
async def watch_page(link_id):
    """ভিডিও স্ট্রিমিং পেজ রেন্ডার করে"""
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h1 style='color:red;text-align:center'>404 - Link Not Found</h1>", 404

    stream_url = f"{BASE_URL}/stream/{link_id}"
    download_url = f"{BASE_URL}/watch/{link_id}?download=true"
    file_name = data["file_name"]

    # HTML টেমপ্লেট
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Streaming: {file_name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f0f2f5;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #4a4a4a;
                text-align: center;
            }}
            video {{
                width: 100%;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                margin: 5px;
                background: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                text-align: center;
            }}
            .btn-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 {file_name}</h1>
            
            <video controls autoplay>
                <source src="{stream_url}" type="video/mp4">
                Your browser does not support HTML5 video.
            </video>
            
            <div class="btn-container">
                <a href="{stream_url}" class="btn">🎥 Stream</a>
                <a href="{download_url}" class="btn" style="background:#2196F3;">⬇️ Download</a>
                <a href="intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;end" 
                   class="btn" style="background:#FF5722;">MX Player</a>
                <a href="vlc://{stream_url}" 
                   class="btn" style="background:#673AB7;">VLC</a>
            </div>
            
            <div class="footer">
                <p>Streaming powered by MovieZone BD</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/stream/<link_id>")
async def stream_file(link_id):
    """ফাইল স্ট্রিমিং হ্যান্ডলার"""
    return await serve_file(link_id, as_download=False)

async def serve_file(link_id, as_download=False):
    """প্রকৃত ফাইল সার্ভিং লজিক"""
    data = links.find_one({"link_id": link_id})
    if not data:
        return "File not found", 404

    headers = {}
    file_name = data["file_name"]
    mime_type = data.get("mime_type", "video/mp4")

    if as_download:
        headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'

    async def generate():
        async for chunk in stream_client.stream_media(data["file_id"]):
            yield chunk

    return Response(
        generate(),
        mimetype=mime_type,
        headers=headers
    )

# ====================
# STARTUP AND SHUTDOWN
# ====================
async def run_bots():
    """Pyrogram ক্লায়েন্ট শুরু করে"""
    await bot.start()
    await stream_client.start()
    print("Bot and stream client started successfully")

async def stop_bots():
    """Pyrogram ক্লায়েন্ট বন্ধ করে"""
    await bot.stop()
    await stream_client.stop()
    print("Bot and stream client stopped")

def run_flask():
    """Flask অ্যাপ চালায়"""
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Koyeb এ ডিপ্লয় করার জন্য এই সেটআপ
    loop = asyncio.get_event_loop()
    
    try:
        # Pyrogram ক্লায়েন্ট শুরু করুন
        loop.run_until_complete(run_bots())
        
        # Flask অ্যাপ চালান
        from threading import Thread
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # বট চলমান রাখুন
        loop.run_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        loop.run_until_complete(stop_bots())
        loop.close()
