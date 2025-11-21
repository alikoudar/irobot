"""Feedback model."""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class FeedbackRating(str, enum.Enum):
    """Feedback rating."""
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"


class Feedback(Base):
    """Feedback model."""
    
    __tablename__ = "feedbacks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Feedback
    rating = Column(SQLEnum(FeedbackRating), nullable=False)
    comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="feedbacks")
    conversation = relationship("Conversation", back_populates="feedbacks")
    message = relationship("Message", back_populates="feedbacks")
    
    def __repr__(self):
        return f"<Feedback {self.rating} on Message {self.message_id}>"