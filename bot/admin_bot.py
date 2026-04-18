import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, WebAppInfo
from dotenv import load_dotenv

from database.database import SessionLocal
from database.models import Settings, SourceChannel, Post

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Standard tunnel URL for Mini Apps locally (Need Ngrok or Localtunnel)
# Replace with actual HTTPS URL once deployed
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://app.ngrok.dev/app/index.html")

admin_bot = Client("admin_bot_session", bot_token=BOT_TOKEN, api_id=os.getenv("API_ID"), api_hash=os.getenv("API_HASH")) if BOT_TOKEN else None

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Launch Dashboard", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

@admin_bot.on_message(filters.command("start")) if admin_bot else None
async def start_cmd(client: Client, message: Message):
    db = SessionLocal()
    # Init settings if missing
    if not db.query(Settings).first():
        db.add(Settings())
        db.commit()
    db.close()
    
    await message.reply_text(
        "👋 **Welcome to the AI Content Agent**\n\n"
        "I monitor your source channels, filter out spam, and rewrite high-quality posts in your brand style.\n\n"
        "Choose an option below to manage the system:",
        reply_markup=get_main_menu()
    )

@admin_bot.on_callback_query(filters.regex("^menu_dashboard$")) if admin_bot else None
async def cb_dashboard(client: Client, callback_query: CallbackQuery):
    db = SessionLocal()
    total_posts = db.query(Post).count()
    pending = db.query(Post).filter(Post.status == "pending").count()
    published = db.query(Post).filter(Post.status == "published").count()
    rejected = db.query(Post).filter(Post.status == "rejected").count()
    channels = db.query(SourceChannel).filter(SourceChannel.is_active == True).count()
    
    settings = db.query(Settings).first()
    db.close()
    
    text = (
        f"📊 **Content Dashboard**\n\n"
        f"**Active Source Channels:** {channels}\n"
        f"**Target Channel ID:** {settings.target_channel_id or 'Not Set'}\n"
        f"**Post Mode:** {settings.post_mode}\n\n"
        f"📝 **Pending Drafts:** {pending}\n"
        f"✅ **Published Posts:** {published}\n"
        f"🚫 **Rejected Posts:** {rejected}\n"
        f"📈 **Total Processed:** {total_posts}\n"
    )
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]))

@admin_bot.on_callback_query(filters.regex("^main_menu$")) if admin_bot else None
async def cb_main_menu(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "👋 **Welcome back to the AI Content Agent**\n\nChoose an option below:",
        reply_markup=get_main_menu()
    )

@admin_bot.on_callback_query(filters.regex("^menu_settings$")) if admin_bot else None
async def cb_settings(client: Client, callback_query: CallbackQuery):
    db = SessionLocal()
    settings = db.query(Settings).first()
    db.close()
    
    text = (
        f"⚙️ **System Settings**\n\n"
        f"• **Target Channel:** {settings.target_channel_id}\n"
        f"• **Tone:** {settings.tone_style[:50]}...\n"
        f"• **Mode:** {settings.post_mode}\n"
        f"• **Auto-Publish Threshold:** {settings.auto_publish_threshold}\n"
        f"\n_(Setting specific values directly via bot chat is a WIP. For now, edit the DB directly or add commands)._"
    )
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]))

@admin_bot.on_callback_query(filters.regex("^menu_channels$")) if admin_bot else None
async def cb_channels(client: Client, callback_query: CallbackQuery):
    db = SessionLocal()
    channels = db.query(SourceChannel).all()
    db.close()
    
    text = f"📡 **Source Channels ({len(channels)})**\n\n"
    for ch in channels:
        status = "✅" if ch.is_active else "❌"
        text += f"{status} {ch.channel_name} (`{ch.channel_id}`)\n"
        
    text += "\nTo add a channel, send `/addchannel <id> <name>`"
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]))

@admin_bot.on_message(filters.command("addchannel")) if admin_bot else None
async def add_channel_cmd(client: Client, message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Usage: `/addchannel <channel_id_or_username> <Name>`")
        return
        
    ch_id, name = parts[1], parts[2]
    db = SessionLocal()
    if db.query(SourceChannel).filter(SourceChannel.channel_id == ch_id).first():
        await message.reply_text("Channel already exists.")
    else:
        db.add(SourceChannel(channel_id=ch_id, channel_name=name))
        db.commit()
        await message.reply_text(f"Added {name} (`{ch_id}`) to active monitor!")
    db.close()

@admin_bot.on_callback_query(filters.regex("^menu_drafts$")) if admin_bot else None
async def cb_drafts(client: Client, callback_query: CallbackQuery):
    db = SessionLocal()
    post = db.query(Post).filter(Post.status == "pending").first()
    
    if not post:
        db.close()
        await callback_query.message.edit_text(
            "🎉 **No pending drafts!**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
        )
        return
        
    await render_draft(callback_query.message, post)
    db.close()

async def render_draft(message: Message, post: Post):
    text = (
        f"📝 **Draft Review (Score: {post.relevance_score})**\n\n"
        f"**Suggested Headline:** {post.suggested_headline}\n\n"
        f"{post.rewritten_text}\n\n"
        f"_(Topic: {post.topic})_\n"
        f"_(Original ID: {post.id})_"
    )
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve & Queue", callback_data=f"draft_approve_{post.id}"),
         InlineKeyboardButton("🚫 Reject", callback_data=f"draft_reject_{post.id}")],
        [InlineKeyboardButton("⏭ Skip", callback_data="menu_drafts"),
         InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ])
    
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except:
        await message.reply_text(text, reply_markup=markup, disable_web_page_preview=True)


@admin_bot.on_callback_query(filters.regex(r"^draft_(approve|reject)_(\d+)$")) if admin_bot else None
async def handle_draft_action(client: Client, callback_query: CallbackQuery):
    action = callback_query.matches[0].group(1)
    post_id = int(callback_query.matches[0].group(2))
    
    db = SessionLocal()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        db.close()
        await callback_query.answer("Post not found!")
        return
        
    if action == "approve":
        post.status = "queued"
    else:
        post.status = "rejected"
        
    db.commit()
    db.close()
    
    await callback_query.answer(f"Post {action}d!", show_alert=False)
    # Recursively load the next draft
    await cb_drafts(client, callback_query)


async def start_admin_bot():
    if admin_bot:
        print("Starting Admin Bot...")
        await admin_bot.start()
    else:
        print("Admin bot omitted: BOT_TOKEN missing.")
