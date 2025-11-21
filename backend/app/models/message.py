"""Message model."""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class MessageRole(str, enum.Enum):
    """Message role."""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class Message(Base):
    """Message model."""
    
    __tablename__ = "messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Content
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Sources (for assistant messages)
    sources = Column(JSONB, nullable=True)  # List of chunk IDs and metadata
    
    # Token usage
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    token_count_total = Column(Integer, nullable=True)
    
    # Cost tracking
    cost_usd = Column(Float, nullable=True)
    cost_xaf = Column(Float, nullable=True)
    
    # Model used
    model_used = Column(String(50), nullable=True)
    
    # Cache
    cache_hit = Column(Boolean, default=False, nullable=False)
    cache_key = Column(String(255), nullable=True, index=True)
    
    # Performance
    response_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    feedbacks = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Message {self.role} in Conversation {self.conversation_id}>"