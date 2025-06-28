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

# কনফিগারেশন
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
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
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
        file_name = media.file_name or "video_stream"

        links.insert_one({
            "link_id": link_id,
            "file_id": media.file_id,
            "file_name": file_name,
            "mime_type": media.mime_type,
            "created_at": datetime.utcnow()
        })

        stream_url = f"{BASE_URL}/stream/{link_id}"
        await message.reply(
            f"📁 ফাইল: {file_name}\n"
            f"🔗 স্ট্রিম লিংক: {BASE_URL}/watch/{link_id}\n"
            f"⬇️ ডাউনলোড: {BASE_URL}/watch/{link_id}?download=true"
        )
    except Exception as e:
        logger.error(f"আপলোড এরর: {str(e)}")
        await message.reply("❌ ফাইল আপলোডে সমস্যা হয়েছে")

@app.route("/watch/<link_id>")
def watch_page(link_id):
    """ভিডিও প্লেয়ার পেজ"""
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "<h1 style='color:red;text-align:center'>লিংক খুঁজে পাওয়া যায়নি</h1>", 404

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{data['file_name']}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                video {{ width: 100%; border-radius: 4px; outline: none; }}
                .btn {{ display: inline-block; padding: 8px 16px; background: #1877f2; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>{data['file_name']}</h2>
                <video controls autoplay playsinline>
                    <source src="/stream/{link_id}" type="video/mp4">
                    আপনার ব্রাউজার ভিডিও সাপোর্ট করে না।
                </video>
                <a href="/watch/{link_id}?download=true" class="btn">ডাউনলোড করুন</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"ওয়াচ পেজ এরর: {str(e)}")
        return "<h1 style='color:red;text-align:center'>সার্ভার এরর</h1>", 500

def run_streaming(link_id, file_id):
    """স্ট্রিমিং জেনারেটর ফাংশন"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
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
    
    return loop.run_until_complete(generate())

@app.route("/stream/<link_id>")
def stream_file(link_id):
    """ভিডিও স্ট্রিমিং এন্ডপয়েন্ট"""
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "ফাইল খুঁজে পাওয়া যায়নি", 404

        headers = {
            "Content-Type": data.get("mime_type", "video/mp4"),
            "Content-Disposition": f'inline; filename="{data["file_name"]}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }

        return Response(
            run_streaming(link_id, data["file_id"]),
            headers=headers,
            direct_passthrough=True
        )
    except Exception as e:
        logger.error(f"স্ট্রিমিং এরর: {str(e)}")
        return "স্ট্রিমিং এরর", 500

@app.route("/watch/<link_id>", methods=["GET"])
def download_file(link_id):
    """ফাইল ডাউনলোড এন্ডপয়েন্ট"""
    if request.args.get("download"):
        data = links.find_one({"link_id": link_id})
        if not data:
            return "ফাইল খুঁজে পাওয়া যায়নি", 404

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{data["file_name"]}"'
        }

        return Response(
            run_streaming(link_id, data["file_id"]),
            headers=headers,
            direct_passthrough=True
        )
    return watch_page(link_id)

def run_flask():
    """ফ্লাস্ক সার্ভার রান করুন"""
    app.run(host="0.0.0.0", port=8080, threaded=True)

def run_bot():
    """বট রান করুন"""
    bot.run()

if __name__ == "__main__":
    # আলাদা থ্রেডে ফ্লাস্ক চালান
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # মেইন থ্রেডে বট চালান
    run_bot()
