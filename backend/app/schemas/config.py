# -*- coding: utf-8 -*-
"""
Schemas Pydantic pour les Configurations Système.

Définit les schemas de validation pour les opérations CRUD
sur les configurations système (models, chunking, search, etc.).

Sprint 12 - Phase 2 : Schemas Configurations
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_serializer


# =============================================================================
# SCHEMAS DE BASE
# =============================================================================

class ConfigBase(BaseModel):
    """Schema de base pour une configuration."""
    
    key: str = Field(
        ...,
        max_length=100,
        description="Clé unique de la configuration (ex: mistral.models.embed)"
    )
    value: Dict[str, Any] = Field(
        ...,
        description="Valeur de la configuration (JSON)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Description de la modification (optionnel)"
    )


# =============================================================================
# SCHEMAS DE CRÉATION
# =============================================================================

class ConfigCreate(ConfigBase):
    """Schema pour créer une nouvelle configuration."""
    
    category: str = Field(
        ...,
        max_length=50,
        description="Catégorie de la configuration (models, chunking, search, etc.)"
    )


# =============================================================================
# SCHEMAS DE MISE À JOUR
# =============================================================================

class ConfigUpdate(BaseModel):
    """Schema pour mettre à jour une configuration."""
    
    value: Dict[str, Any] = Field(
        ...,
        description="Nouvelle valeur de la configuration (JSON)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Description de la modification (optionnel)"
    )


# =============================================================================
# SCHEMAS DE RÉPONSE
# =============================================================================

class ConfigResponse(BaseModel):
    """Schema de réponse pour une configuration."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    key: str
    category: str
    value: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # ✅ CORRECTION : Serializer pour timezone UTC+1
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z pour timezone correcte."""
        return dt.isoformat() + 'Z' if dt else None


class ConfigListResponse(BaseModel):
    """Schema de réponse pour une liste de configurations."""
    
    items: List[ConfigResponse]
    total: int
    page: int = 1
    page_size: int = 100


class ConfigCategoryResponse(BaseModel):
    """Schema de réponse pour les configurations d'une catégorie."""
    
    category: str
    configs: Dict[str, Dict[str, Any]]
    count: int


# =============================================================================
# SCHEMAS POUR L'HISTORIQUE
# =============================================================================

class ConfigHistoryEntry(BaseModel):
    """Schema pour une entrée dans l'historique des modifications."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    config_id: UUID
    modified_by: str = Field(
        ...,
        description="Email de l'utilisateur qui a fait la modification"
    )
    old_value: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ancienne valeur (null pour création)"
    )
    new_value: Dict[str, Any] = Field(
        ...,
        description="Nouvelle valeur"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description de la modification"
    )
    created_at: datetime = Field(
        ...,
        description="Date/heure de la modification"
    )
    
    # ✅ CORRECTION : Serializer pour timezone UTC+1
    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z pour timezone correcte."""
        return dt.isoformat() + 'Z' if dt else None


class ConfigHistoryResponse(BaseModel):
    """Schema de réponse pour l'historique d'une configuration."""
    
    key: str
    history: List[ConfigHistoryEntry]
    total: int


# =============================================================================
# SCHEMAS DE RECHERCHE / FILTRAGE
# =============================================================================

class ConfigSearchParams(BaseModel):
    """Paramètres de recherche pour les configurations."""
    
    category: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Filtrer par catégorie"
    )
    search_query: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Recherche dans les clés et descriptions"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Filtrer par statut actif/inactif"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Numéro de page"
    )
    page_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Taille de la page"
    )


# =============================================================================
# SCHEMAS SPÉCIFIQUES PAR TYPE DE CONFIG
# =============================================================================

class ModelConfig(BaseModel):
    """Schema pour une configuration de modèle."""
    
    model_name: str = Field(
        ...,
        description="Nom du modèle Mistral"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description du modèle"
    )


class ChunkingConfig(BaseModel):
    """Schema pour une configuration de chunking."""
    
    size: int = Field(
        ...,
        ge=50,
        le=2048,
        description="Taille du chunk en tokens"
    )
    overlap: int = Field(
        default=0,
        ge=0,
        le=512,
        description="Chevauchement entre chunks"
    )


class SearchConfig(BaseModel):
    """Schema pour une configuration de recherche."""
    
    top_k: int = Field(
        ...,
        ge=1,
        le=100,
        description="Nombre de résultats à retourner"
    )
    hybrid_alpha: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Poids entre BM25 (0) et sémantique (1)"
    )


class PricingConfig(BaseModel):
    """Schema pour une configuration de tarification."""
    
    model: str = Field(
        ...,
        description="Nom du modèle"
    )
    unit: str = Field(
        default="tokens",
        description="Unité de tarification (tokens, pages)"
    )
    price_per_million_input: Optional[float] = Field(
        default=None,
        ge=0,
        description="Prix par million de tokens en entrée (USD)"
    )
    price_per_million_output: Optional[float] = Field(
        default=None,
        ge=0,
        description="Prix par million de tokens en sortie (USD)"
    )
    price_per_thousand_pages: Optional[float] = Field(
        default=None,
        ge=0,
        description="Prix par millier de pages (USD)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description du tarif"
    )


# =============================================================================
# SCHEMAS DE STATISTIQUES
# =============================================================================

class ConfigStatsResponse(BaseModel):
    """Schema de réponse pour les statistiques des configurations."""
    
    total_configs: int
    categories: Dict[str, int]
    last_modified: Optional[datetime] = None
    active_configs: int
    inactive_configs: int
    
    # ✅ CORRECTION : Serializer pour timezone UTC+1
    @field_serializer('last_modified')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z pour timezone correcte."""
        return dt.isoformat() + 'Z' if dt else None


# =============================================================================
# SCHEMAS DE VALIDATION
# =============================================================================

class ConfigValidationResponse(BaseModel):
    """Schema de réponse pour la validation d'une configuration."""
    
    is_valid: bool
    errors: List[str] = Field(
        default_factory=list,
        description="Liste des erreurs de validation"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Liste des avertissements"
    )


# =============================================================================
# SCHEMAS D'EXPORT
# =============================================================================

class ConfigExportRequest(BaseModel):
    """Schema pour demander un export de configurations."""
    
    categories: Optional[List[str]] = Field(
        default=None,
        description="Catégories à exporter (toutes si non spécifié)"
    )
    include_history: bool = Field(
        default=False,
        description="Inclure l'historique des modifications"
    )
    format: str = Field(
        default="json",
        pattern="^(json|yaml)$",
        description="Format d'export : json ou yaml"
    )


class ConfigExportResponse(BaseModel):
    """Schema de réponse pour l'export de configurations."""
    
    data: Any = Field(
        ...,
        description="Données exportées (structure dépend du format)"
    )
    format: str
    count: int
    exported_at: datetime
    
    # ✅ CORRECTION : Serializer pour timezone UTC+1
    @field_serializer('exported_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z pour timezone correcte."""
        return dt.isoformat() + 'Z' if dt else None