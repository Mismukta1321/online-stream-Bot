import os
import asyncio
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, request
from pymongo import MongoClient
from datetime import datetime
import random
import string
import logging

# লগিং কনফিগারেশন
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# কনফিগারেশন (এনভায়রনমেন্ট ভেরিয়েবল ব্যবহার করুন)
API_ID = int(os.getenv("API_ID", 22697010))
API_HASH = os.getenv("API_HASH", "fd88d7339b0371eb2a9501d523f3e2a7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/streambot?retryWrites=true&w=majority&appName=Cluster")
BASE_URL = os.getenv("BASE_URL", "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app")

# ফ্লাস্ক অ্যাপ ইনিশিয়ালাইজ
app = Flask(__name__)

# MongoDB কানেকশন
mongo = MongoClient(MONGO_URI)
db = mongo["streambot"]
links = db["links"]

def generate_id(length=10):
    """ইউনিক ID জেনারেটর"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Pyrogram বট ক্লায়েন্ট
bot = Client(
    "my_stream_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
    workers=2
)

@bot.on_message(filters.command("upload") & filters.reply)
async def handle_upload(client, message: Message):
    """ফাইল আপলোড হ্যান্ডলার"""
    try:
        media = message.reply_to_message.document or message.reply_to_message.video
        if not media:
            await message.reply("❌ শুধুমাত্র ভিডিও/ডকুমেন্ট ফাইল সাপোর্টেড")
            return

        link_id = generate_id()
        file_name = media.file_name or "video_stream_" + link_id[:5]

        links.insert_one({
            "link_id": link_id,
            "file_id": media.file_id,
            "file_name": file_name,
            "mime_type": media.mime_type,
            "file_size": media.file_size,
            "created_at": datetime.utcnow()
        })

        await message.reply(
            f"🎬 **ফাইল আপলোড সফল!**\n\n"
            f"📁 নাম: {file_name}\n"
            f"🔗 স্ট্রিম লিংক: {BASE_URL}/watch/{link_id}\n"
            f"⬇️ ডাউনলোড: {BASE_URL}/watch/{link_id}?download=1"
        )
    except Exception as e:
        logger.error(f"আপলোড এরর: {str(e)}")
        await message.reply("❌ ফাইল আপলোডে সমস্যা হয়েছে, পরে আবার চেষ্টা করুন")

def create_stream_response(file_id):
    """স্ট্রিমিং রেস্পন্স জেনারেটর"""
    async def generate():
        stream_client = Client(
            "stream_client",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True,
            no_updates=True
        )
        async with stream_client:
            async for chunk in stream_client.stream_media(file_id):
                yield chunk
    return generate

@app.route("/stream/<link_id>")
async def stream_file(link_id):
    """ভিডিও স্ট্রিমিং এন্ডপয়েন্ট"""
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "লিংক খুঁজে পাওয়া যায়নি", 404

        headers = {
            "Content-Type": data.get("mime_type", "video/mp4"),
            "Content-Disposition": f'inline; filename="{data["file_name"]}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }

        range_header = request.headers.get('Range')
        
        return Response(
            create_stream_response(data["file_id"])(),
            status=206 if range_header else 200,
            headers=headers,
            direct_passthrough=True
        )
    except Exception as e:
        logger.error(f"স্ট্রিমিং এরর: {str(e)}")
        return "ভিডিও স্ট্রিম করতে সমস্যা হচ্ছে", 500

@app.route("/watch/<link_id>")
def watch_page(link_id):
    """ভিডিও প্লেয়ার পেজ"""
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "<h1 style='color:red;text-align:center'>লিংকটি ভ্যালিড নয়</h1>", 404

        return f"""
        <!DOCTYPE html>
        <html lang="bn">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{data['file_name']} - স্ট্রিমিং</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: #f5f5f5;
                    color: #333;
                }}
                .container {{
                    max-width: 800px;
                    margin: 20px auto;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    margin-top: 0;
                }}
                video {{
                    width: 100%;
                    background: #000;
                    border-radius: 4px;
                    margin: 15px 0;
                }}
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #3498db;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-right: 10px;
                }}
                .btn:hover {{
                    background: #2980b9;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{data['file_name']}</h1>
                <video controls autoplay playsinline>
                    <source src="/stream/{link_id}" type="video/mp4">
                    আপনার ব্রাউজার HTML5 ভিডিও সাপোর্ট করে না।
                </video>
                <div>
                    <a href="/watch/{link_id}?download=1" class="btn">ডাউনলোড করুন</a>
                    <a href="{BASE_URL}/stream/{link_id}" class="btn" target="_blank">স্ট্রিম লিংক</a>
                </div>
            </div>
            <script>
                // ভিডিও এরর হ্যান্ডলিং
                const video = document.querySelector('video');
                video.addEventListener('error', function() {{
                    console.log('ভিডিও লোড হতে সমস্যা হচ্ছে, পুনরায় চেষ্টা করা হচ্ছে...');
                    setTimeout(() => {{
                        video.src = '/stream/{link_id}?t=' + new Date().getTime();
                        video.load();
                    }}, 3000);
                }});
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"ওয়াচ পেজ এরর: {str(e)}")
        return "<h1 style='color:red;text-align:center'>সার্ভার এরর</h1>", 500

@app.route("/watch/<link_id>", methods=['GET'])
def download_file(link_id):
    """ফাইল ডাউনলোড এন্ডপয়েন্ট"""
    if 'download' in request.args:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "ফাইল খুঁজে পাওয়া যায়নি", 404

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{data["file_name"]}"',
            "Content-Length": str(data.get("file_size", ""))
        }

        return Response(
            create_stream_response(data["file_id"])(),
            headers=headers,
            direct_passthrough=True
        )
    return watch_page(link_id)

def run_flask():
    """ফ্লাস্ক সার্ভার চালান"""
    app.run(host="0.0.0.0", port=8080, threaded=True)

def run_bot():
    """বট চালান"""
    bot.run()

if __name__ == "__main__":
    # ফ্লাস্ক সার্ভার আলাদা থ্রেডে চালু করুন
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # প্রধান থ্রেডে বট চালান
    run_bot()
