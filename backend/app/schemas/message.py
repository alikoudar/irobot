# -*- coding: utf-8 -*-
"""
Schemas Pydantic pour les Messages.

Définit les schemas de validation pour les messages
des conversations du chatbot, incluant le tracking des tokens et coûts.

Sprint 7 - Phase 2 : Schemas Messages
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================

class MessageRoleEnum(str, Enum):
    """Rôle du message dans la conversation."""
    USER = "USER"
    ASSISTANT = "ASSISTANT"


# =============================================================================
# SCHEMAS POUR LES SOURCES
# =============================================================================

class SourceReference(BaseModel):
    """Référence à une source citée dans la réponse."""
    
    document_id: str = Field(..., description="ID du document source")
    title: str = Field(..., description="Titre du document")
    category: Optional[str] = Field(default=None, description="Catégorie du document")
    page: Optional[int] = Field(default=None, description="Numéro de page")
    chunk_index: Optional[int] = Field(default=None, description="Index du chunk")
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de pertinence (0-1)"
    )
    excerpt: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Extrait du texte source"
    )


# =============================================================================
# SCHEMAS DE BASE
# =============================================================================

class MessageBase(BaseModel):
    """Schema de base pour un message."""
    
    role: MessageRoleEnum = Field(..., description="Rôle : user ou assistant")
    content: str = Field(..., min_length=1, description="Contenu du message")


# =============================================================================
# SCHEMAS DE CRÉATION
# =============================================================================

class MessageCreate(BaseModel):
    """Schema pour créer un nouveau message utilisateur."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Contenu du message"
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="ID de la conversation (nouvelle conversation si non fourni)"
    )


class MessageCreateInternal(BaseModel):
    """Schema interne pour créer un message (utilisé par le service)."""
    
    conversation_id: UUID
    role: MessageRoleEnum
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    token_count_total: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_xaf: Optional[float] = None
    model_used: Optional[str] = None
    cache_hit: bool = False
    cache_key: Optional[str] = None
    response_time_seconds: Optional[float] = None


# =============================================================================
# SCHEMAS DE RÉPONSE
# =============================================================================

class MessageResponse(BaseModel):
    """Schema de réponse pour un message."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    conversation_id: UUID
    role: MessageRoleEnum
    content: str
    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Sources citées dans la réponse (pour les messages assistant)"
    )
    token_count_input: Optional[int] = Field(
        default=None,
        description="Nombre de tokens en entrée"
    )
    token_count_output: Optional[int] = Field(
        default=None,
        description="Nombre de tokens en sortie"
    )
    token_count_total: Optional[int] = Field(
        default=None,
        description="Nombre total de tokens"
    )
    cost_usd: Optional[float] = Field(
        default=None,
        description="Coût en USD"
    )
    cost_xaf: Optional[float] = Field(
        default=None,
        description="Coût en XAF"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Modèle LLM utilisé"
    )
    cache_hit: bool = Field(
        default=False,
        description="Réponse servie depuis le cache"
    )
    response_time_seconds: Optional[float] = Field(
        default=None,
        description="Temps de réponse en secondes"
    )
    created_at: datetime


class MessageListResponse(BaseModel):
    """Schema de réponse pour une liste de messages."""
    
    messages: List[MessageResponse]
    total: int
    conversation_id: UUID


# =============================================================================
# SCHEMAS POUR LE STREAMING
# =============================================================================

class StreamChunk(BaseModel):
    """Schema pour un chunk de réponse streamée."""
    
    type: str = Field(
        ...,
        pattern="^(token|sources|metadata|error|done)$",
        description="Type de chunk"
    )
    content: Optional[str] = Field(
        default=None,
        description="Contenu textuel (pour type=token)"
    )
    sources: Optional[List[SourceReference]] = Field(
        default=None,
        description="Sources (pour type=sources)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Métadonnées (pour type=metadata)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Message d'erreur (pour type=error)"
    )


class ChatRequest(BaseModel):
    """Schema pour une requête de chat."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message de l'utilisateur"
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="ID de la conversation existante (nouvelle si non fourni)"
    )
    stream: bool = Field(
        default=True,
        description="Activer le streaming de la réponse"
    )


class ChatResponse(BaseModel):
    """Schema de réponse pour une requête de chat (non-streamée)."""
    
    conversation_id: UUID
    message_id: UUID
    content: str
    sources: List[SourceReference]
    token_count_input: int
    token_count_output: int
    cost_usd: float
    cost_xaf: float
    cache_hit: bool
    response_time_seconds: float
    model_used: str


class ChatStreamStartEvent(BaseModel):
    """Événement de début de streaming."""
    
    event: str = "start"
    conversation_id: UUID
    message_id: UUID
    is_new_conversation: bool = False


class ChatStreamTokenEvent(BaseModel):
    """Événement de token streamé."""
    
    event: str = "token"
    content: str


class ChatStreamSourcesEvent(BaseModel):
    """Événement avec les sources."""
    
    event: str = "sources"
    sources: List[SourceReference]


class ChatStreamMetadataEvent(BaseModel):
    """Événement avec les métadonnées finales."""
    
    event: str = "metadata"
    token_count_input: int
    token_count_output: int
    cost_usd: float
    cost_xaf: float
    cache_hit: bool
    response_time_seconds: float
    model_used: str


class ChatStreamEndEvent(BaseModel):
    """Événement de fin de streaming."""
    
    event: str = "done"
    message_id: UUID


class ChatStreamErrorEvent(BaseModel):
    """Événement d'erreur."""
    
    event: str = "error"
    error: str
    code: Optional[str] = None


# =============================================================================
# SCHEMAS POUR L'HISTORIQUE
# =============================================================================

class MessageHistoryItem(BaseModel):
    """Item d'historique pour le contexte LLM."""
    
    role: MessageRoleEnum
    content: str


class ConversationHistory(BaseModel):
    """Historique de conversation pour le contexte LLM."""
    
    messages: List[MessageHistoryItem] = Field(
        default_factory=list,
        max_length=10,
        description="Derniers messages (max 10)"
    )