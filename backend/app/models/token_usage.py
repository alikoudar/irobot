"""Modèle TokenUsage pour le suivi des coûts et tokens consommés."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class OperationType(str, enum.Enum):
    """Type d'opération ayant consommé des tokens."""
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"
    TITLE_GENERATION = "TITLE_GENERATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    OCR = "OCR"


class TokenUsage(Base):
    """
    Modèle de suivi de l'utilisation des tokens.
    
    Enregistre chaque appel API Mistral avec :
    - Type d'opération (embedding, génération, etc.)
    - Nombre de tokens consommés
    - Coût en USD et XAF
    - Références optionnelles vers user, document, message
    """
    
    __tablename__ = "token_usages"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Information sur l'opération
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    model_name = Column(String(50), nullable=False)
    
    # Comptage des tokens
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    token_count_total = Column(Integer, nullable=False)
    
    # Coûts
    cost_usd = Column(Float, nullable=False)
    cost_xaf = Column(Float, nullable=False)
    exchange_rate = Column(Float, nullable=False)
    
    # Références optionnelles (FK)
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    document_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("documents.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    message_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("messages.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Métadonnées additionnelles (batch_id, chunk_ids, etc.)
    token_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relations (optionnelles, pour jointures)
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    document = relationship("Document", foreign_keys=[document_id], lazy="select")
    message = relationship("Message", foreign_keys=[message_id], lazy="select")
    
    def __repr__(self):
        return f"<TokenUsage {self.operation_type.value} - {self.token_count_total} tokens - ${self.cost_usd:.4f}>"
    
    @classmethod
    def calculate_cost(
        cls,
        token_count: int,
        price_per_million: float,
        exchange_rate: float
    ) -> tuple[float, float]:
        """
        Calcule le coût en USD et XAF.
        
        Args:
            token_count: Nombre de tokens
            price_per_million: Prix par million de tokens en USD
            exchange_rate: Taux de change USD -> XAF
            
        Returns:
            Tuple (cost_usd, cost_xaf)
        """
        cost_usd = (token_count / 1_000_000) * price_per_million
        cost_xaf = cost_usd * exchange_rate
        return cost_usd, cost_xaf