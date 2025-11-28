"""Schemas Pydantic pour SystemConfig."""
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


# ============== Base Schemas ==============

class SystemConfigBase(BaseModel):
    """Schema de base pour SystemConfig."""
    key: str = Field(..., max_length=100, pattern=r"^[a-z][a-z0-9_.]+$")
    value: Any = Field(..., description="Valeur de configuration (JSONB)")
    description: Optional[str] = None


class SystemConfigCreate(SystemConfigBase):
    """Schema pour créer une SystemConfig."""
    pass


class SystemConfigUpdate(BaseModel):
    """Schema pour mettre à jour une SystemConfig."""
    value: Any = Field(..., description="Nouvelle valeur")
    description: Optional[str] = None


class SystemConfigResponse(SystemConfigBase):
    """Schema de réponse pour SystemConfig."""
    id: UUID
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    model_config = ConfigDict(from_attributes=True)


# ============== Grouped Configs ==============

class ConfigGroup(BaseModel):
    """Groupe de configurations par préfixe."""
    group: str = Field(description="Préfixe du groupe (ex: models, chunking)")
    configs: list[SystemConfigResponse]


# ============== Predefined Config Keys ==============

class ModelConfigKeys:
    """Clés de configuration pour les modèles Mistral."""
    EMBEDDING = "models.embedding"
    RERANKING = "models.reranking"
    GENERATION = "models.generation"
    OCR = "models.ocr"


class ChunkingConfigKeys:
    """Clés de configuration pour le chunking."""
    SIZE = "chunking.size"
    OVERLAP = "chunking.overlap"


class SearchConfigKeys:
    """Clés de configuration pour la recherche."""
    ALPHA = "search.alpha"
    TOP_K_BEFORE_RERANK = "search.top_k_before_rerank"
    TOP_K_AFTER_RERANK = "search.top_k_after_rerank"


class CacheConfigKeys:
    """Clés de configuration pour le cache."""
    TTL_DAYS = "cache.ttl_days"
    SIMILARITY_THRESHOLD = "cache.similarity_threshold"


class PricingConfigKeys:
    """Clés de configuration pour les prix Mistral (USD par million tokens)."""
    MISTRAL_EMBED = "pricing.mistral_embed"
    MISTRAL_SMALL = "pricing.mistral_small"
    MISTRAL_MEDIUM = "pricing.mistral_medium"
    MISTRAL_LARGE = "pricing.mistral_large"
    MISTRAL_OCR = "pricing.mistral_ocr"


# ============== Default Config Values ==============

DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    # Modèles Mistral
    "models.embedding": {
        "value": "mistral-embed",
        "description": "Modèle Mistral pour l'embedding"
    },
    "models.reranking": {
        "value": "mistral-small-latest",
        "description": "Modèle Mistral pour le reranking"
    },
    "models.generation": {
        "value": "mistral-medium-latest",
        "description": "Modèle Mistral pour la génération de réponses"
    },
    "models.ocr": {
        "value": "pixtral-12b-2409",
        "description": "Modèle Mistral pour l'OCR"
    },
    
    # Chunking
    "chunking.size": {
        "value": 1000,
        "description": "Taille des chunks en caractères"
    },
    "chunking.overlap": {
        "value": 200,
        "description": "Overlap entre les chunks en caractères"
    },
    
    # Recherche
    "search.alpha": {
        "value": 0.75,
        "description": "Poids de la recherche sémantique (0=BM25, 1=Vector)"
    },
    "search.top_k_before_rerank": {
        "value": 10,
        "description": "Nombre de résultats avant reranking"
    },
    "search.top_k_after_rerank": {
        "value": 3,
        "description": "Nombre de résultats après reranking"
    },
    
    # Cache
    "cache.ttl_days": {
        "value": 7,
        "description": "Durée de vie du cache en jours"
    },
    "cache.similarity_threshold": {
        "value": 0.95,
        "description": "Seuil de similarité pour cache L2"
    },
    
    # Pricing Mistral (USD par million tokens) - Tarifs approximatifs
    "pricing.mistral_embed": {
        "value": 0.1,
        "description": "Prix embedding par million tokens (USD)"
    },
    "pricing.mistral_small": {
        "value": 0.2,
        "description": "Prix mistral-small par million tokens (USD)"
    },
    "pricing.mistral_medium": {
        "value": 2.7,
        "description": "Prix mistral-medium par million tokens (USD)"
    },
    "pricing.mistral_large": {
        "value": 8.0,
        "description": "Prix mistral-large par million tokens (USD)"
    },
    "pricing.mistral_ocr": {
        "value": 0.15,
        "description": "Prix pixtral OCR par million tokens (USD)"
    },
    
    # Taux de change par défaut
    "exchange.default_rate": {
        "value": 655.957,
        "description": "Taux de change USD/XAF par défaut (taux fixe FCFA)"
    },
}


# ============== Bulk Operations ==============

class SystemConfigBulkUpdate(BaseModel):
    """Mise à jour en masse de configurations."""
    configs: dict[str, Any] = Field(
        ..., 
        description="Dict de clé -> valeur à mettre à jour"
    )


class SystemConfigList(BaseModel):
    """Liste de toutes les configurations."""
    items: list[SystemConfigResponse]
    total: int