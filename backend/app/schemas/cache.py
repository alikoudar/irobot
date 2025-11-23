# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour le système de cache.

Définit les schémas de validation et sérialisation pour les modèles
QueryCache, CacheDocumentMap et CacheStatistics.

Sprint 6 - Phase 1 : Modèles Cache
"""

from datetime import date, datetime
from typing import Optional, List, Any
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


# =============================================================================
# Schémas QueryCache
# =============================================================================

class QueryCacheBase(BaseModel):
    """Schéma de base pour QueryCache."""
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Texte de la question posée"
    )


class QueryCacheCreate(QueryCacheBase):
    """Schéma pour la création d'une entrée de cache."""
    query_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Hash SHA-256 de la question"
    )
    query_embedding: Optional[List[float]] = Field(
        None,
        description="Vecteur embedding de la question"
    )
    response: str = Field(
        ...,
        min_length=1,
        description="Réponse générée par le LLM"
    )
    sources: Optional[List[dict]] = Field(
        default_factory=list,
        description="Liste des sources utilisées"
    )
    token_count: int = Field(
        default=0,
        ge=0,
        description="Nombre de tokens de la réponse"
    )
    cost_saved_usd: Decimal = Field(
        default=Decimal("0.0"),
        ge=0,
        description="Coût économisé en USD"
    )
    cost_saved_xaf: Decimal = Field(
        default=Decimal("0.0"),
        ge=0,
        description="Coût économisé en XAF"
    )
    document_ids: Optional[List[UUID]] = Field(
        default_factory=list,
        description="Liste des IDs de documents utilisés"
    )


class QueryCacheUpdate(BaseModel):
    """Schéma pour la mise à jour d'une entrée de cache."""
    hit_count: Optional[int] = Field(
        None,
        ge=0,
        description="Nombre de hits"
    )
    last_hit_at: Optional[datetime] = Field(
        None,
        description="Date du dernier hit"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Nouvelle date d'expiration"
    )


class QueryCacheResponse(QueryCacheBase):
    """Schéma de réponse pour QueryCache."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    query_hash: str
    response: str
    sources: Optional[List[dict]] = None
    token_count: int
    cost_saved_usd: Decimal
    cost_saved_xaf: Decimal
    hit_count: int
    last_hit_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    is_expired: bool = False
    
    @field_validator('is_expired', mode='before')
    @classmethod
    def check_expired(cls, v, info):
        """Calcule si le cache est expiré."""
        if hasattr(info, 'data') and 'expires_at' in info.data:
            return datetime.utcnow() > info.data['expires_at']
        return False


class QueryCacheListResponse(BaseModel):
    """Schéma de réponse pour une liste de caches."""
    items: List[QueryCacheResponse]
    total: int = Field(..., ge=0, description="Nombre total d'entrées")
    page: int = Field(default=1, ge=1, description="Page courante")
    page_size: int = Field(default=20, ge=1, le=100, description="Taille de page")


# =============================================================================
# Schémas CacheDocumentMap
# =============================================================================

class CacheDocumentMapBase(BaseModel):
    """Schéma de base pour CacheDocumentMap."""
    cache_id: UUID = Field(..., description="ID de l'entrée de cache")
    document_id: UUID = Field(..., description="ID du document")


class CacheDocumentMapCreate(CacheDocumentMapBase):
    """Schéma pour la création d'un mapping cache-document."""
    pass


class CacheDocumentMapResponse(CacheDocumentMapBase):
    """Schéma de réponse pour CacheDocumentMap."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime


# =============================================================================
# Schémas CacheStatistics
# =============================================================================

class CacheStatisticsBase(BaseModel):
    """Schéma de base pour CacheStatistics."""
    date: date = Field(..., description="Date des statistiques")


class CacheStatisticsCreate(CacheStatisticsBase):
    """Schéma pour la création de statistiques."""
    total_requests: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    cache_misses: int = Field(default=0, ge=0)
    hit_rate: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    tokens_saved: int = Field(default=0, ge=0)
    cost_saved_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    cost_saved_xaf: Decimal = Field(default=Decimal("0.0"), ge=0)


class CacheStatisticsUpdate(BaseModel):
    """Schéma pour la mise à jour des statistiques."""
    total_requests: Optional[int] = Field(None, ge=0)
    cache_hits: Optional[int] = Field(None, ge=0)
    cache_misses: Optional[int] = Field(None, ge=0)
    hit_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    tokens_saved: Optional[int] = Field(None, ge=0)
    cost_saved_usd: Optional[Decimal] = Field(None, ge=0)
    cost_saved_xaf: Optional[Decimal] = Field(None, ge=0)


class CacheStatisticsResponse(CacheStatisticsBase):
    """Schéma de réponse pour CacheStatistics."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: Decimal
    tokens_saved: int
    cost_saved_usd: Decimal
    cost_saved_xaf: Decimal
    created_at: datetime
    updated_at: datetime


class CacheStatisticsListResponse(BaseModel):
    """Schéma de réponse pour une liste de statistiques."""
    items: List[CacheStatisticsResponse]
    total: int = Field(..., ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CacheStatisticsSummary(BaseModel):
    """Schéma pour le résumé des statistiques sur une période."""
    period_days: int = Field(..., ge=0, description="Nombre de jours")
    total_requests: int = Field(..., ge=0, description="Total des requêtes")
    total_hits: int = Field(..., ge=0, description="Total des hits")
    total_misses: int = Field(..., ge=0, description="Total des misses")
    avg_hit_rate: Decimal = Field(..., ge=0, le=100, description="Taux de hit moyen")
    total_tokens_saved: int = Field(..., ge=0, description="Tokens économisés")
    total_cost_saved_usd: Decimal = Field(..., ge=0, description="Économies USD")
    total_cost_saved_xaf: Decimal = Field(..., ge=0, description="Économies XAF")


# =============================================================================
# Schémas pour les réponses d'API Cache
# =============================================================================

class CacheHitResponse(BaseModel):
    """Schéma de réponse lors d'un hit cache."""
    cache_hit: bool = True
    cache_level: int = Field(
        ...,
        ge=1,
        le=2,
        description="Niveau de cache (1=exact, 2=similarité)"
    )
    response: str = Field(..., description="Réponse mise en cache")
    sources: Optional[List[dict]] = Field(
        default_factory=list,
        description="Sources de la réponse"
    )
    cache_id: UUID = Field(..., description="ID de l'entrée de cache")
    tokens_saved: int = Field(..., ge=0, description="Tokens économisés")
    cost_saved_usd: Decimal = Field(..., ge=0)
    cost_saved_xaf: Decimal = Field(..., ge=0)


class CacheMissResponse(BaseModel):
    """Schéma de réponse lors d'un miss cache."""
    cache_hit: bool = False
    cache_level: None = None
    message: str = Field(
        default="Cache miss - pipeline RAG requis",
        description="Message informatif"
    )


class CacheInvalidationResponse(BaseModel):
    """Schéma de réponse pour l'invalidation de cache."""
    success: bool = True
    document_id: UUID = Field(..., description="ID du document invalidé")
    caches_invalidated: int = Field(
        ...,
        ge=0,
        description="Nombre d'entrées de cache invalidées"
    )
    message: str = Field(..., description="Message de confirmation")


# =============================================================================
# Schémas pour le dashboard Admin
# =============================================================================

class CacheDashboardStats(BaseModel):
    """Schéma pour les statistiques cache du dashboard Admin."""
    # Statistiques du jour
    today_requests: int = Field(default=0, ge=0)
    today_hits: int = Field(default=0, ge=0)
    today_misses: int = Field(default=0, ge=0)
    today_hit_rate: Decimal = Field(default=Decimal("0.0"))
    
    # Statistiques 7 derniers jours
    week_requests: int = Field(default=0, ge=0)
    week_hits: int = Field(default=0, ge=0)
    week_hit_rate: Decimal = Field(default=Decimal("0.0"))
    week_tokens_saved: int = Field(default=0, ge=0)
    week_cost_saved_usd: Decimal = Field(default=Decimal("0.0"))
    week_cost_saved_xaf: Decimal = Field(default=Decimal("0.0"))
    
    # Statistiques globales
    total_cache_entries: int = Field(default=0, ge=0)
    total_tokens_saved: int = Field(default=0, ge=0)
    total_cost_saved_usd: Decimal = Field(default=Decimal("0.0"))
    total_cost_saved_xaf: Decimal = Field(default=Decimal("0.0"))
    
    # Historique pour graphiques (7 derniers jours)
    daily_stats: List[CacheStatisticsResponse] = Field(default_factory=list)