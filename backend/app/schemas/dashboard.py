# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour Dashboard - Sprint 10 Phase 1

Définit les schémas de validation et sérialisation pour les endpoints dashboard.

Auteur: IroBot Team
Date: 2025-11-27
Sprint: 10 - Phase 1
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# SCHEMAS USERS STATS
# =============================================================================

class UsersStats(BaseModel):
    """Statistiques utilisateurs."""
    total: int = Field(..., description="Nombre total d'utilisateurs")
    active: int = Field(..., description="Utilisateurs actifs")
    new: int = Field(..., description="Nouveaux utilisateurs (période)")
    inactive: int = Field(..., description="Utilisateurs inactifs")


# =============================================================================
# SCHEMAS DOCUMENTS STATS
# =============================================================================

class DocumentsStats(BaseModel):
    """Statistiques documents."""
    total: int = Field(..., description="Nombre total de documents")
    completed: int = Field(..., description="Documents complétés")
    processing: int = Field(..., description="Documents en traitement")
    failed: int = Field(..., description="Documents en erreur")
    total_chunks: int = Field(..., description="Nombre total de chunks")


# =============================================================================
# SCHEMAS CONVERSATIONS STATS
# =============================================================================

class ConversationsStats(BaseModel):
    """Statistiques conversations."""
    total: int = Field(..., description="Nombre total de conversations")


# =============================================================================
# SCHEMAS MESSAGES STATS
# =============================================================================

class MessagesStats(BaseModel):
    """Statistiques messages."""
    total: int = Field(..., description="Nombre total de messages")
    user_messages: int = Field(..., description="Messages utilisateurs")
    assistant_messages: int = Field(..., description="Messages assistant")


# =============================================================================
# SCHEMAS CACHE STATS
# =============================================================================

class CacheStats(BaseModel):
    """Statistiques cache."""
    total_requests: int = Field(..., description="Total requêtes")
    cache_hits: int = Field(..., description="Cache hits")
    cache_misses: int = Field(..., description="Cache misses")
    hit_rate: float = Field(..., description="Taux de hit (%)")
    tokens_saved: int = Field(..., description="Tokens économisés")
    cost_saved_usd: float = Field(..., description="Coût économisé USD")
    cost_saved_xaf: float = Field(..., description="Coût économisé XAF")


# =============================================================================
# SCHEMAS TOKEN USAGE STATS
# =============================================================================

class OperationTokenStats(BaseModel):
    """Statistiques tokens pour une opération."""
    total_tokens: int = Field(..., description="Total tokens")
    total_cost_usd: float = Field(..., description="Coût total USD")
    total_cost_xaf: float = Field(..., description="Coût total XAF")
    count: int = Field(..., description="Nombre d'opérations")


class TokenUsageStats(BaseModel):
    """Statistiques d'usage des tokens."""
    embedding: OperationTokenStats = Field(..., description="Stats embedding")
    reranking: OperationTokenStats = Field(..., description="Stats reranking")
    title_generation: OperationTokenStats = Field(..., description="Stats génération titre")
    response_generation: OperationTokenStats = Field(..., description="Stats génération réponse")
    total: Dict[str, float] = Field(..., description="Totaux globaux")


# =============================================================================
# SCHEMAS FEEDBACKS STATS (réutilisé de feedback_service)
# =============================================================================

class FeedbacksStats(BaseModel):
    """Statistiques feedbacks (du FeedbackService)."""
    total_feedbacks: int
    thumbs_up: int
    thumbs_down: int
    with_comments: int
    satisfaction_rate: float
    feedback_rate: float
    total_messages: int


# =============================================================================
# SCHEMAS DATE RANGE
# =============================================================================

class DateRange(BaseModel):
    """Plage de dates."""
    start: str = Field(..., description="Date de début (ISO)")
    end: str = Field(..., description="Date de fin (ISO)")


# =============================================================================
# SCHEMA OVERVIEW COMPLET
# =============================================================================

class DashboardOverview(BaseModel):
    """Vue d'ensemble dashboard admin."""
    users: UsersStats
    documents: DocumentsStats
    conversations: ConversationsStats
    messages: MessagesStats
    cache: CacheStats
    tokens: Dict  # TokenUsageStats en dict pour flexibilité
    feedbacks: Dict  # FeedbacksStats en dict pour flexibilité
    date_range: DateRange


# =============================================================================
# SCHEMAS TOP DOCUMENTS
# =============================================================================

class TopDocument(BaseModel):
    """Détails d'un document top utilisé."""
    document_id: str = Field(..., description="ID du document")
    title: str = Field(..., description="Titre/nom du document")
    category: Optional[str] = Field(None, description="Catégorie")
    usage_count: int = Field(..., description="Nombre d'utilisations")
    total_chunks: int = Field(..., description="Nombre de chunks")


class TopDocumentsResponse(BaseModel):
    """Réponse top documents."""
    documents: List[TopDocument]
    total: int = Field(..., description="Nombre total retourné")


# =============================================================================
# SCHEMAS ACTIVITY TIMELINE
# =============================================================================

class ActivityDay(BaseModel):
    """Activité d'une journée."""
    date: str = Field(..., description="Date (ISO)")
    messages: int = Field(..., description="Nombre de messages")
    documents: int = Field(..., description="Nombre de documents traités")


class ActivityTimelineResponse(BaseModel):
    """Réponse timeline d'activité."""
    timeline: List[ActivityDay]
    days: int = Field(..., description="Nombre de jours analysés")


# =============================================================================
# SCHEMAS USER ACTIVITY
# =============================================================================

class UserActivity(BaseModel):
    """Activité d'un utilisateur."""
    user_id: str = Field(..., description="ID utilisateur")
    matricule: str = Field(..., description="Matricule")
    name: str = Field(..., description="Nom complet")
    message_count: int = Field(..., description="Nombre de messages")


class UserActivityResponse(BaseModel):
    """Réponse activité utilisateurs."""
    users: List[UserActivity]
    total: int = Field(..., description="Nombre d'utilisateurs retournés")