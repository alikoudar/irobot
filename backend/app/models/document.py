"""Document model."""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    """Document model."""
    
    __tablename__ = "documents"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File info
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(10), nullable=False)
    
    # Processing
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    # Content
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, default=0, nullable=False)
    extracted_text_length = Column(Integer, nullable=True)
    
    # Metadata
    document_metadata = Column(JSONB, nullable=True)
    
    # Processing times
    extraction_time_seconds = Column(Float, nullable=True)
    chunking_time_seconds = Column(Float, nullable=True)
    embedding_time_seconds = Column(Float, nullable=True)
    total_processing_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    category = relationship("Category", back_populates="documents")
    uploader = relationship("User", back_populates="documents", foreign_keys=[uploaded_by])
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document {self.original_filename} - {self.status}>"