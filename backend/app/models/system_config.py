"""System configuration model."""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base


class SystemConfig(Base):
    """System configuration model for dynamic settings."""
    
    __tablename__ = "system_configs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Config
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SystemConfig {self.key}>"