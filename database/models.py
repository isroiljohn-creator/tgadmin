import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    target_channel_id = Column(String, nullable=True) # ID or username
    bot_language = Column(String, default="English")
    target_language = Column(String, default="English")
    post_mode = Column(String, default="Draft") # Draft, Semi-Automatic, Automatic
    tone_style = Column(Text, default="Professional and engaging")
    auto_publish_threshold = Column(Float, default=0.8) # Only used if mode is Semi/Auto
    post_frequency_minutes = Column(Integer, default=60) # How often to publish from queue

class SourceChannel(Base):
    __tablename__ = "source_channels"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, unique=True, index=True) # The actual telegram ID or username
    channel_name = Column(String)
    whitelist_topics = Column(String, nullable=True) # Comma-separated
    blacklist_topics = Column(String, nullable=True) # Comma-separated
    is_active = Column(Boolean, default=True)
    
    posts = relationship("Post", back_populates="source_channel", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_channel_id = Column(Integer, ForeignKey("source_channels.id"))
    original_message_id = Column(String)
    original_text = Column(Text)
    
    rewritten_text = Column(Text, nullable=True)
    suggested_headline = Column(String, nullable=True)
    
    relevance_score = Column(Float, default=0.0)
    topic = Column(String, nullable=True)
    is_spam_or_ad = Column(Boolean, default=False)
    
    # Status: 'pending', 'approved', 'rejected', 'published', 'queued'
    status = Column(String, default="pending") 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    source_channel = relationship("SourceChannel", back_populates="posts")
