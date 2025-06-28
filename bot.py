import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, Response, request
from pymongo import MongoClient
from datetime import datetime
import random
import string
import asyncio
from flask_cors import CORS

# Configuration
API_ID = int(os.getenv("API_ID", 22697010))
API_HASH = os.getenv("API_HASH", "fd88d7339b0371eb2a9501d523f3e2a7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7347631253:AAFX3dmD0N8q6u0l2zghoBFu-7TXvMC571M")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/streambot?retryWrites=true&w=majority&appName=Cluster")
BASE_URL = os.getenv("BASE_URL", "https://unlikely-atlanta-nahidbrow-2c574cde.koyeb.app")

# Initialize Clients with retry logic
def create_client():
    return Client(
        "bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
        workers=1  # Reduce workers to minimize API calls
    )

bot = create_client()

app = Flask(__name__)
CORS(app)

# MongoDB Connection
mongo = MongoClient(MONGO_URI)
db = mongo["streambot"]
links = db["links"]

def generate_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def safe_send_message(chat_id, text):
    """Safe message sending with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id, text)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (attempt + 1) * 5  # Exponential backoff
            print(f"Retry {attempt + 1} for sending message. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)

@bot.on_message(filters.command("upload") & filters.reply)
async def handle_upload(client, message: Message):
    try:
        if not message.reply_to_message:
            return await safe_send_message(message.chat.id, "❌ Please reply to a file with this command")

        media = (
            message.reply_to_message.document or 
            message.reply_to_message.video or 
            message.reply_to_message.audio
        )
        
        if not media:
            return await safe_send_message(message.chat.id, "❌ Unsupported file type")

        link_id = generate_id()
        file_name = getattr(media, "file_name", None) or "file"
        
        links.insert_one({
            "link_id": link_id,
            "file_id": media.file_id,
            "file_name": file_name,
            "mime_type": media.mime_type,
            "created_at": datetime.utcnow()
        })

        url = f"{BASE_URL}/watch/{link_id}"
        await safe_send_message(
            message.chat.id,
            f"**✅ File uploaded successfully!**\n\n"
            f"📁 File: {file_name}\n"
            f"🔗 Stream URL: {url}\n"
            f"⬇️ Download URL: {url}?download=true"
        )
    except Exception as e:
        print(f"Upload Error: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)}")

@app.route("/watch/<link_id>")
def watch_page(link_id):
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "<h1 style='color:red;text-align:center'>404 - Link Not Found</h1>", 404

        stream_url = f"{BASE_URL}/stream/{link_id}"
        download_url = f"{BASE_URL}/watch/{link_id}?download=true"
        file_name = data["file_name"]

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stream: {file_name}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                video {{ width: 100%; border-radius: 8px; }}
                .btn {{ display: inline-block; margin: 10px; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🎬 {file_name}</h2>
                <video controls autoplay>
                    <source src="{stream_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div>
                    <a href="{download_url}" class="btn">⬇️ Download</a>
                    <a href="{stream_url}" class="btn">🎥 Stream</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        print(f"Watch Page Error: {e}")
        return "<h1 style='color:red;text-align:center'>500 - Internal Server Error</h1>", 500

@app.route("/stream/<link_id>")
def stream_file(link_id):
    try:
        data = links.find_one({"link_id": link_id})
        if not data:
            return "File not found", 404

        # Create new client for each request to avoid session issues
        temp_client = create_client()
        
        def generate():
            with temp_client:
                for chunk in temp_client.stream_media(data["file_id"]):
                    yield chunk

        return Response(
            generate(),
            mimetype=data.get("mime_type", "video/mp4"),
            headers={"Content-Disposition": f'inline; filename="{data["file_name"]}"'}
        )
    except Exception as e:
        print(f"Streaming Error: {str(e)}")
        return f"Internal Server Error: {str(e)}", 500

async def run_bot():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await bot.start()
            print("Bot started successfully")
            await asyncio.Event().wait()  # Run forever
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (attempt + 1) * 30  # Exponential backoff
            print(f"Retry {attempt + 1} for starting bot. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Temporarily disable the bot if FloodWait is active
    # Wait for the required time (check your logs for exact seconds)
    # flood_wait_time = 2900  # Adjust based on your error message
    # print(f"Waiting {flood_wait_time} seconds due to FloodWait...")
    # time.sleep(flood_wait_time)
    
    from threading import Thread
    
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run bot with retry logic
    asyncio.run(run_bot())
