"""Category model."""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base


class Category(Base):
    """Document category model."""
    
    __tablename__ = "categories"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Info
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="category")
    
    def __repr__(self):
        return f"<Category {self.name}>"