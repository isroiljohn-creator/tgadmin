import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from dotenv import load_dotenv

from database.database import SessionLocal
from database.models import SourceChannel, Post, Settings
from services.ai_processor import assess_content, rewrite_content

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Need to ensure unique session name for the user client
userbot_client = Client("userbot_session", api_id=API_ID, api_hash=API_HASH) if API_ID else None

def get_active_source_channels():
    db = SessionLocal()
    channels = db.query(SourceChannel).filter(SourceChannel.is_active == True).all()
    channel_ids = [int(c.channel_id) if c.channel_id.lstrip('-').isdigit() else c.channel_id for c in channels]
    db.close()
    return channel_ids

@userbot_client.on_message(filters.channel) if userbot_client else None
async def handle_new_post(client: Client, message: Message):
    # Retrieve active channels dynamically
    db = SessionLocal()
    active_channels = db.query(SourceChannel).filter(SourceChannel.is_active == True).all()
    
    # Create mapping of channel strings/ints to database IDs
    channel_mapping = {}
    for ch in active_channels:
        if str(message.chat.id) == ch.channel_id or message.chat.username == ch.channel_id:
            channel_mapping["db_id"] = ch.id
            break
            
    if "db_id" not in channel_mapping:
        db.close()
        return

    text = message.text or message.caption
    if not text:
        db.close()
        return
        
    print(f"New message gracefully caught in {message.chat.title}")
    
    # 1. AI Assessment
    assessment = await assess_content(text)
    score = assessment.get("relevance_score", 0.0)
    is_spam = assessment.get("is_spam_or_ad", False)
    
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
        
    # Filter
    if is_spam or score < 0.4:
        print(f"Post rejected: Spam={is_spam}, Score={score}")
        db.close()
        return
        
    # 2. AI Rewriting
    rewritten_data = await rewrite_content(text, settings.tone_style, settings.target_language)
    
    # 3. Store in specific status
    status = "pending"
    if settings.post_mode == "Automatic" and score >= settings.auto_publish_threshold:
        status = "queued"
        
    new_post = Post(
        source_channel_id=channel_mapping["db_id"],
        original_message_id=str(message.id),
        original_text=text,
        rewritten_text=rewritten_data.get("rewritten_text", ""),
        suggested_headline=rewritten_data.get("headline", ""),
        relevance_score=score,
        topic=assessment.get("topic", ""),
        is_spam_or_ad=is_spam,
        status=status
    )
    db.add(new_post)
    db.commit()
    print(f"Post saved as {status}!")
    db.close()

async def start_userbot():
    if userbot_client:
        print("Starting Userbot Client...")
        await userbot_client.start()
    else:
        print("Userbot omitted: API_ID or API_HASH missing.")
