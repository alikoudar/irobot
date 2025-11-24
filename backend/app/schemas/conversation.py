# -*- coding: utf-8 -*-
"""
Schemas Pydantic pour les Conversations.

Définit les schemas de validation pour les opérations CRUD
sur les conversations du chatbot.

Sprint 7 - Phase 2 : Schemas Conversations
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# SCHEMAS DE BASE
# =============================================================================

class ConversationBase(BaseModel):
    """Schema de base pour une conversation."""
    
    title: str = Field(
        default="Nouvelle conversation",
        max_length=255,
        description="Titre de la conversation"
    )


# =============================================================================
# SCHEMAS DE CRÉATION
# =============================================================================

class ConversationCreate(BaseModel):
    """Schema pour créer une nouvelle conversation."""
    
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Titre optionnel (généré automatiquement si non fourni)"
    )


# =============================================================================
# SCHEMAS DE MISE À JOUR
# =============================================================================

class ConversationUpdate(BaseModel):
    """Schema pour mettre à jour une conversation."""
    
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Nouveau titre"
    )
    is_archived: Optional[bool] = Field(
        default=None,
        description="Archiver/désarchiver la conversation"
    )


class ConversationArchive(BaseModel):
    """Schema pour archiver/désarchiver une conversation."""
    
    is_archived: bool = Field(
        ...,
        description="True pour archiver, False pour désarchiver"
    )


# =============================================================================
# SCHEMAS DE RÉPONSE
# =============================================================================

class ConversationResponse(BaseModel):
    """Schema de réponse pour une conversation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    
    # Champs calculés (optionnels, ajoutés par le service)
    message_count: Optional[int] = Field(
        default=None,
        description="Nombre de messages dans la conversation"
    )
    last_message_at: Optional[datetime] = Field(
        default=None,
        description="Date du dernier message"
    )


class ConversationListResponse(BaseModel):
    """Schema de réponse pour une liste de conversations."""
    
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ConversationSummary(BaseModel):
    """Schema résumé pour l'affichage dans la sidebar."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    title: str
    is_archived: bool
    updated_at: datetime
    message_count: Optional[int] = None
    
    # Aperçu du dernier message (optionnel)
    last_message_preview: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Aperçu du dernier message (tronqué)"
    )

class ConversationSummaryListResponse(BaseModel):
    """Schema de réponse pour une liste de résumés de conversations."""
    
    conversations: List[ConversationSummary]  # ← Utilise ConversationSummary
    total: int
    page: int
    page_size: int
    has_more: bool

# =============================================================================
# SCHEMAS POUR LE CHAT
# =============================================================================

# Import différé pour éviter l'import circulaire
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.message import MessageResponse


class ConversationWithMessages(ConversationResponse):
    """Schema de réponse avec les messages inclus."""
    
    messages: List["MessageResponse"] = Field(
        default_factory=list,
        description="Liste des messages de la conversation"
    )


# =============================================================================
# SCHEMAS DE RECHERCHE / FILTRAGE
# =============================================================================

class ConversationSearchParams(BaseModel):
    """Paramètres de recherche pour les conversations."""
    
    search_query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Recherche dans le titre et les messages"
    )
    is_archived: Optional[bool] = Field(
        default=None,
        description="Filtrer par statut d'archivage"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Date de début (created_at >= start_date)"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Date de fin (created_at <= end_date)"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Numéro de page"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Taille de la page"
    )


# =============================================================================
# SCHEMAS D'EXPORT
# =============================================================================

class ConversationExportRequest(BaseModel):
    """Schema pour demander un export de conversations."""
    
    conversation_ids: Optional[List[UUID]] = Field(
        default=None,
        description="IDs des conversations à exporter (toutes si non spécifié)"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Date de début pour le filtre"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Date de fin pour le filtre"
    )
    format: str = Field(
        default="json",
        pattern="^(json|csv)$",
        description="Format d'export : json ou csv"
    )
    include_messages: bool = Field(
        default=True,
        description="Inclure les messages dans l'export"
    )