"""Schemas Pydantic pour ExchangeRate."""
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============== Base Schemas ==============

class ExchangeRateBase(BaseModel):
    """Schema de base pour ExchangeRate."""
    currency_from: str = Field(default="USD", max_length=3, pattern=r"^[A-Z]{3}$")
    currency_to: str = Field(default="XAF", max_length=3, pattern=r"^[A-Z]{3}$")
    rate: Decimal = Field(..., gt=0, decimal_places=6)


class ExchangeRateCreate(ExchangeRateBase):
    """Schema pour créer un ExchangeRate."""
    fetched_at: Optional[datetime] = None


class ExchangeRateResponse(ExchangeRateBase):
    """Schema de réponse pour ExchangeRate."""
    id: UUID
    fetched_at: datetime
    created_at: datetime
    
    @field_serializer('fetched_at', 'created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    model_config = ConfigDict(from_attributes=True)


# ============== Current Rate ==============

class CurrentExchangeRate(BaseModel):
    """Taux de change actuel."""
    currency_from: str
    currency_to: str
    rate: float
    fetched_at: datetime
    age_seconds: int = Field(description="Âge du taux en secondes")
    is_stale: bool = Field(description="True si le taux est périmé (> 24h)")
    
    @field_serializer('fetched_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None


# ============== Conversion ==============

class ConversionRequest(BaseModel):
    """Requête de conversion de devises."""
    amount: float = Field(..., gt=0)
    from_currency: str = Field(default="USD", max_length=3)
    to_currency: str = Field(default="XAF", max_length=3)


class ConversionResponse(BaseModel):
    """Réponse de conversion de devises."""
    original_amount: float
    converted_amount: float
    from_currency: str
    to_currency: str
    rate_used: float
    rate_fetched_at: datetime
    
    @field_serializer('rate_fetched_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None


# ============== API Response ==============

class ExchangeRateAPIResponse(BaseModel):
    """Réponse de l'API externe de taux de change."""
    base: str
    date: str
    rates: dict[str, float]


# ============== List Response ==============

class ExchangeRateList(BaseModel):
    """Liste paginée d'ExchangeRate (historique)."""
    items: list[ExchangeRateResponse]
    total: int
    page: int
    size: int
    pages: int


# ============== Stats ==============

class ExchangeRateStats(BaseModel):
    """Statistiques des taux de change."""
    current_rate: float
    min_rate_30d: float
    max_rate_30d: float
    avg_rate_30d: float
    last_update: datetime
    update_count_30d: int
    
    @field_serializer('last_update')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None