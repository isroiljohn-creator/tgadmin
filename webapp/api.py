from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel

from database.database import SessionLocal
from database.models import Settings, SourceChannel, Post
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Telegram Content Agent API")

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Allow Web App to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your specific Web App URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for incoming data ---
class ActionModel(BaseModel):
    action: str # "approve", "reject", "delete"

class SettingUpdateModel(BaseModel):
    tone_style: str
    bot_language: str
    target_language: str
    post_mode: str
    auto_publish_threshold: float
    target_channel_id: str

@app.get("/api/stats")
async def get_stats():
    db = SessionLocal()
    total = db.query(Post).count()
    pending = db.query(Post).filter(Post.status == "pending").count()
    rejected = db.query(Post).filter(Post.status == "rejected").count()
    published = db.query(Post).filter(Post.status == "published").count()
    channels = db.query(SourceChannel).count()
    db.close()
    return {
        "totalProcesssed": total,
        "pendingDrafts": pending,
        "rejected": rejected,
        "published": published,
        "activeChannels": channels
    }

@app.get("/api/drafts/pending")
async def get_pending_drafts():
    db = SessionLocal()
    # return list of drafts, most recent first
    drafts = db.query(Post).filter(Post.status == "pending").order_by(Post.created_at.desc()).all()
    
    result = []
    for d in drafts:
        result.append({
            "id": d.id,
            "original_text": d.original_text,
            "rewritten_text": d.rewritten_text,
            "suggested_headline": d.suggested_headline,
            "relevance_score": d.relevance_score,
            "topic": d.topic,
            "is_spam": d.is_spam_or_ad,
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    db.close()
    return result

@app.post("/api/drafts/{post_id}/action")
async def draft_action(post_id: int, action_data: ActionModel):
    db = SessionLocal()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        db.close()
        raise HTTPException(status_code=404, detail="Post not found")
        
    if action_data.action == "approve":
        post.status = "queued"
    elif action_data.action == "reject":
        post.status = "rejected"
    else:
        post.status = "deleted"
        
    db.commit()
    db.close()
    return {"status": "success", "new_status": post.status}

@app.get("/api/settings")
async def get_settings():
    db = SessionLocal()
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
    
    # Transform correctly
    data = {
        "id": settings.id,
        "target_channel_id": settings.target_channel_id or "",
        "bot_language": settings.bot_language,
        "target_language": settings.target_language,
        "post_mode": settings.post_mode,
        "tone_style": settings.tone_style,
        "auto_publish_threshold": settings.auto_publish_threshold
    }
    db.close()
    return data

@app.put("/api/settings")
async def update_settings(updates: SettingUpdateModel):
    db = SessionLocal()
    settings = db.query(Settings).first()
    if not settings:
        db.close()
        raise HTTPException(status_code=404, detail="Settings not found")
        
    settings.tone_style = updates.tone_style
    settings.bot_language = updates.bot_language
    settings.target_language = updates.target_language
    settings.post_mode = updates.post_mode
    settings.auto_publish_threshold = updates.auto_publish_threshold
    settings.target_channel_id = updates.target_channel_id
    
    db.commit()
    db.close()
    return {"status": "success"}
