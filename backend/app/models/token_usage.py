"""Token usage model for tracking costs."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class OperationType(str, enum.Enum):
    """Type of operation that consumed tokens."""
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"
    TITLE_GENERATION = "TITLE_GENERATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"


class TokenUsage(Base):
    """Token usage tracking model."""
    
    __tablename__ = "token_usages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Operation info
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    model_name = Column(String(50), nullable=False)
    
    # Token counts
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    token_count_total = Column(Integer, nullable=False)
    
    # Cost
    cost_usd = Column(Float, nullable=False)
    cost_xaf = Column(Float, nullable=False)
    exchange_rate = Column(Float, nullable=False)
    
    # Metadata
    token_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<TokenUsage {self.operation_type} - {self.token_count_total} tokens - ${self.cost_usd}>"