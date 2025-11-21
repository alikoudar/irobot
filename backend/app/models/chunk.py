"""Chunk model."""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base


class Chunk(Base):
    """Document chunk model."""
    
    __tablename__ = "chunks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Weaviate
    weaviate_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Stats
    token_count = Column(Integer, nullable=False)
    char_count = Column(Integer, nullable=False)
    
    # Position in document
    page_number = Column(Integer, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    
    # Metadata
    chunk_metadata = Column(JSONB, nullable=True)
    
    # Embedding info
    embedding_model = Column(String(50), nullable=True)
    embedding_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    indexed_at = Column(DateTime, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<Chunk {self.chunk_index} of Document {self.document_id}>"