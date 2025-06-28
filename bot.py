from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, request
from pymongo import MongoClient
from datetime import datetime
import threading
import random, string, io, asyncio
from flask_cors import CORS
from flask_asyncio import patch_routes

# ====================
# CONFIGURATION
# ====================
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M"
MONGO_URI = "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
BASE_URL = "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app"  # ⚠️ এখানে তোমার Koyeb URL বসাও, শেষ স্লাশ ছাড়া

# ====================
# INITIALIZE
# ====================
# বট ক্লায়েন্ট, যা শুধুমাত্র কমান্ড হ্যান্ডেল করবে
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফ্লাস্ক অ্যাপ ইনিশিয়ালাইজ করা
flask_app = Flask(__name__)
CORS(flask_app) # CORS সক্ষম করা, যদি ফ্রন্টএন্ড ভিন্ন ডোমেইনে থাকে

# স্ট্রিমিং এর জন্য পৃথক Pyrogram ক্লায়েন্ট
stream_client = Client("stream_client", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# মঙ্গোডিবি ক্লায়েন্ট
mongo = MongoClient(MONGO_URI)
db = mongo["streambot"]
links = db.links

# ====================
# HELPER: Generate ID
# ====================
def gen_id(length=10):
    """একটি র্যান্ডম আলফানিউমেরিক আইডি তৈরি করে।"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ====================
# BOT: /upload
# ====================
@bot.on_message(filters.command("upload") & filters.reply)
async def upload_file(c, m: Message):
    """
    ইউজার যখন একটি ফাইল রিপ্লাই করে /upload কমান্ড দেয়, তখন সেই ফাইলের
    জন্য একটি স্ট্রিম এবং ডাউনলোড লিঙ্ক তৈরি করে।
    """
    media = m.reply_to_message.document or m.reply_to_message.video
    if not media:
        return await m.reply("❌ Reply to a video/document file.")

    link_id = gen_id()
    links.insert_one({
        "link_id": link_id,
        "file_id": media.file_id,
        "file_name": media.file_name if media.file_name else "video", # ফাইলের নাম সেভ করা
        "created": datetime.utcnow()
    })

    url = f"{BASE_URL}/watch/{link_id}"
    await m.reply(f"🎬 Stream: {url}\n📥 Download: {url}?download=true")

# ====================
# WATCH PAGE
# ====================
@flask_app.route("/watch/<link_id>")
async def watch_page(link_id):
    """
    ইউজারের জন্য ভিডিও দেখার HTML পেজ রেন্ডার করে।
    যদি ?download=true থাকে, তাহলে ফাইল ডাউনলোডের জন্য হ্যান্ডেল করে।
    """
    data = links.find_one({"link_id": link_id})
    if not data:
        return "<h3 style='color:red'>Invalid or expired link</h3>", 404

    # যদি ইউজার ডাউনলোড লিঙ্ক চায়
    if request.args.get("download") == "true":
        return await serve_file(link_id, as_download=True)

    stream_url = f"{BASE_URL}/stream/{link_id}"
    download_url = f"{BASE_URL}/watch/{link_id}?download=true"
    file_name = data.get("file_name", "Streamed File")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎥 Stream - {file_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #000; color: #fff; font-family: sans-serif; text-align: center; padding: 10px; }}
            video {{ width: 95%; max-width: 800px; border-radius: 10px; }}
            .btn {{ margin: 10px; padding: 12px 25px; border-radius: 5px; background: orange; color: #000; text-decoration: none; display: inline-block; }}
        </style>
    </head>
    <body>
        <h2>🎬 Movie Stream: {file_name}</h2>
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
# SERVE FILE (STREAM / DOWNLOAD)
# ====================
@flask_app.route("/stream/<link_id>")
async def serve_file(link_id, as_download=False):
    """
    টেলিগ্রাম থেকে ফাইল স্ট্রিম বা ডাউনলোডের জন্য সার্ভ করে।
    `as_download` প্যারামিটার অনুযায়ী হেডার সেট করে।
    """
    data = links.find_one({"link_id": link_id})
    if not data:
        return "❌ Invalid Link", 404

    file_id = data["file_id"]
    file_name = data.get("file_name", "file") # ডিফল্ট ফাইল নাম

    async def generate_file_chunks():
        try:
            async for chunk in stream_client.stream_media(file_id):
                yield chunk
        except Exception as e:
            print(f"Error during file serving: {e}")
            # এখানে আরও ভালো এরর হ্যান্ডলিং যোগ করতে পারেন, যেমন লগিং

    # কন্টেন্ট-ডিসপোজিশন এবং mimetype সেট করুন
    if as_download:
        headers = {"Content-Disposition": f"attachment; filename=\"{file_name}\""}
        mimetype = "application/octet-stream" # বাইনারি ফাইল হিসেবে ডাউনলোড করতে
    else:
        headers = {"Content-Disposition": f"inline; filename=\"{file_name}\""}
        mimetype = "video/mp4" # ভিডিও স্ট্রিম করতে

    return Response(generate_file_chunks(), mimetype=mimetype, headers=headers)

# ====================
# START EVERYTHING
# ====================
async def start_bots():
    """Pyrogram ক্লায়েন্টগুলো শুরু করে।"""
    await bot.start()
    await stream_client.start()
    print("Pyrogram clients started.")

async def stop_bots():
    """Pyrogram ক্লায়েন্টগুলো বন্ধ করে।"""
    await bot.stop()
    await stream_client.stop()
    print("Pyrogram clients stopped.")

if __name__ == "__main__":
    # অ্যাপ্লিকেশন স্টার্টআপে Pyrogram ক্লায়েন্ট শুরু করুন
    @flask_app.before_serving
    async def startup_event():
        await start_bots()

    # অ্যাপ্লিকেশন শাটডাউনে Pyrogram ক্লায়েন্ট বন্ধ করুন
    @flask_app.teardown_appcontext
    async def shutdown_event(exception=None):
        await stop_bots()

    # Flask-Asyncio ব্যবহার করে অ্যাপটিকে অ্যাসিঙ্ক্রোনাস মোডে চালান
    patch_routes(flask_app)
    flask_app.run(host="0.0.0.0", port=8080)
