import asyncio
import datetime
from pyrogram import Client

from database.database import SessionLocal
from database.models import Settings, Post

# We use the admin bot client to publish to the target channel
async def publish_queued_posts(admin_bot: Client):
    db = SessionLocal()
    settings = db.query(Settings).first()
    
    if not settings or not settings.target_channel_id:
        print("Scheduler: No target channel configured.")
        db.close()
        return
        
    # Get one queued post to publish
    # We could restrict this based on `post_frequency_minutes`
    post = db.query(Post).filter(Post.status == "queued").order_by(Post.created_at.asc()).first()
    
    if not post:
        db.close()
        return
        
    print(f"Scheduler: Publishing post {post.id} to {settings.target_channel_id}")
    
    text = ""
    if post.suggested_headline:
        text += f"**{post.suggested_headline}**\n\n"
    text += post.rewritten_text
    
    try:
        await admin_bot.send_message(settings.target_channel_id, text)
        post.status = "published"
        post.published_at = datetime.datetime.utcnow()
        db.commit()
    except Exception as e:
        print(f"Scheduler: Failed to publish: {e}")
        # Maybe retry later or mark failed, for now leave as queued or mark error
        
    db.close()

def start_scheduler(admin_bot: Client, apscheduler):
    from apscheduler.triggers.interval import IntervalTrigger
    
    # Ideally frequency is read from DB dynamically, but APScheduler needs a trigger setup.
    # We'll run the checker every 5 minutes. If we need strict frequency, we implement logic in `publish_queued_posts`
    # to only publish if `last_publish_time > frequency`.
    
    apscheduler.add_job(
        func=lambda: asyncio.create_task(publish_queued_posts(admin_bot)),
        trigger=IntervalTrigger(minutes=1),
        id='publish_job',
        name='Publish Queued Posts',
        replace_existing=True
    )
    print("Scheduler activated.")
