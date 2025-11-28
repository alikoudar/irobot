"""Schemas Pydantic pour TokenUsage."""
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class OperationType(str, Enum):
    """Type d'opération ayant consommé des tokens."""
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"
    TITLE_GENERATION = "TITLE_GENERATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    OCR = "OCR"


# ============== Base Schemas ==============

class TokenUsageBase(BaseModel):
    """Schema de base pour TokenUsage."""
    operation_type: OperationType
    model_name: str = Field(..., max_length=50)
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    token_count_total: int = Field(..., ge=0)
    cost_usd: float = Field(..., ge=0)
    cost_xaf: float = Field(..., ge=0)
    exchange_rate: float = Field(..., gt=0)


class TokenUsageCreate(TokenUsageBase):
    """Schema pour créer un TokenUsage."""
    user_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    message_id: Optional[UUID] = None
    token_metadata: Optional[dict[str, Any]] = None


class TokenUsageResponse(TokenUsageBase):
    """Schema de réponse pour TokenUsage."""
    id: UUID
    user_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    message_id: Optional[UUID] = None
    token_metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    model_config = ConfigDict(from_attributes=True)


# ============== Aggregation Schemas ==============

class TokenUsageSummary(BaseModel):
    """Résumé agrégé de l'utilisation des tokens."""
    total_tokens: int = Field(default=0, description="Total tokens consommés")
    total_cost_usd: float = Field(default=0.0, description="Coût total en USD")
    total_cost_xaf: float = Field(default=0.0, description="Coût total en XAF")
    count: int = Field(default=0, description="Nombre d'opérations")


class TokenUsageByOperation(BaseModel):
    """Utilisation des tokens par type d'opération."""
    operation_type: OperationType
    total_tokens: int
    total_cost_usd: float
    total_cost_xaf: float
    count: int


class TokenUsageByModel(BaseModel):
    """Utilisation des tokens par modèle."""
    model_name: str
    total_tokens: int
    total_cost_usd: float
    total_cost_xaf: float
    count: int


class TokenUsageByDate(BaseModel):
    """Utilisation des tokens par date."""
    date: datetime
    total_tokens: int
    total_cost_usd: float
    total_cost_xaf: float
    count: int
    
    @field_serializer('date')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None


class TokenUsageStats(BaseModel):
    """Statistiques complètes d'utilisation des tokens."""
    summary: TokenUsageSummary
    by_operation: list[TokenUsageByOperation] = []
    by_model: list[TokenUsageByModel] = []
    by_date: list[TokenUsageByDate] = []


# ============== Filter Schemas ==============

class TokenUsageFilter(BaseModel):
    """Filtres pour la recherche de TokenUsage."""
    operation_type: Optional[OperationType] = None
    model_name: Optional[str] = None
    user_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ============== List Response ==============

class TokenUsageList(BaseModel):
    """Liste paginée de TokenUsage."""
    items: list[TokenUsageResponse]
    total: int
    page: int
    size: int
    pages: int