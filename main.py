import asyncio
from pyrogram import idle
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import Base, engine
from bot.admin_bot import start_admin_bot, admin_bot
from bot.userbot import start_userbot, userbot_client
from services.scheduler import start_scheduler

print("Initializing database...")
Base.metadata.create_all(bind=engine)

import uvicorn
from contextlib import suppress

async def start_webserver():
    from webapp.api import app
    import os
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    print(f"Starting Web Server on port {port}...")
    await server.serve()

async def main():
    print("Starting AI Telegram Content Agent...")
    
    # Start Telegram Clients
    await start_admin_bot()
    await start_userbot()
    
    # Start Scheduler
    scheduler = AsyncIOScheduler()
    start_scheduler(admin_bot, scheduler)
    scheduler.start()
    
    # Run Web Server
    # Create uvicorn background task
    web_task = asyncio.create_task(start_webserver())
    
    print("Agent is running! Press Ctrl+C to stop.")
    await idle()
    
    # Cleanup
    with suppress(Exception):
        web_task.cancel()
    if admin_bot:
        await admin_bot.stop()
    if userbot_client:
        await userbot_client.stop()
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down gracefully.")
