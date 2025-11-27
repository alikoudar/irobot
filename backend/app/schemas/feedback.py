# -*- coding: utf-8 -*-
"""
Schemas Pydantic pour les Feedbacks.

Définit les schemas de validation pour les feedbacks
utilisateurs sur les messages du chatbot.

Sprint 7 - Phase 2 : Schemas Feedbacks
Sprint 9 - Phase 1 : Ajout tendances et statistiques avancées
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================

class FeedbackRatingEnum(str, Enum):
    """Type de feedback."""
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"


# =============================================================================
# SCHEMAS DE CRÉATION
# =============================================================================

class FeedbackCreate(BaseModel):
    """Schema pour créer un nouveau feedback."""
    
    message_id: UUID = Field(
        ...,
        description="ID du message concerné"
    )
    rating: FeedbackRatingEnum = Field(
        ...,
        description="Type de feedback : thumbs_up ou thumbs_down"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Commentaire optionnel"
    )


class FeedbackCreateInternal(BaseModel):
    """Schema interne pour créer un feedback (utilisé par le service)."""
    
    user_id: UUID
    conversation_id: UUID
    message_id: UUID
    rating: FeedbackRatingEnum
    comment: Optional[str] = None


# =============================================================================
# SCHEMAS DE MISE À JOUR
# =============================================================================

class FeedbackUpdate(BaseModel):
    """Schema pour mettre à jour un feedback."""
    
    rating: Optional[FeedbackRatingEnum] = Field(
        default=None,
        description="Nouveau type de feedback"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Nouveau commentaire"
    )


# =============================================================================
# SCHEMAS DE RÉPONSE
# =============================================================================

class FeedbackResponse(BaseModel):
    """Schema de réponse pour un feedback."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    conversation_id: UUID
    message_id: UUID
    rating: FeedbackRatingEnum
    comment: Optional[str] = None
    created_at: datetime


class FeedbackWithContext(FeedbackResponse):
    """Schema de réponse avec contexte (pour admin)."""
    
    # Informations utilisateur
    user_matricule: Optional[str] = None
    user_nom: Optional[str] = None
    user_prenom: Optional[str] = None
    
    # Informations message
    message_content: Optional[str] = None
    message_role: Optional[str] = None
    
    # Informations conversation
    conversation_title: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """Schema de réponse pour une liste de feedbacks."""
    
    feedbacks: List[FeedbackResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# SCHEMAS DE RECHERCHE / FILTRAGE
# =============================================================================

class FeedbackSearchParams(BaseModel):
    """Paramètres de recherche pour les feedbacks."""
    
    user_id: Optional[UUID] = Field(
        default=None,
        description="Filtrer par utilisateur"
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Filtrer par conversation"
    )
    message_id: Optional[UUID] = Field(
        default=None,
        description="Filtrer par message"
    )
    rating: Optional[FeedbackRatingEnum] = Field(
        default=None,
        description="Filtrer par type de feedback"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Date de début"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Date de fin"
    )
    has_comment: Optional[bool] = Field(
        default=None,
        description="Filtrer par présence de commentaire"
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
# SCHEMAS DE STATISTIQUES - SPRINT 9 PHASE 1
# =============================================================================

class FeedbackStats(BaseModel):
    """Statistiques simplifiées des feedbacks."""
    
    total_feedbacks: int = Field(
        ..., 
        description="Nombre total de feedbacks"
    )
    thumbs_up: int = Field(
        ..., 
        description="Nombre de feedbacks positifs"
    )
    thumbs_down: int = Field(
        ..., 
        description="Nombre de feedbacks négatifs"
    )
    with_comments: int = Field(
        ...,
        description="Nombre de feedbacks avec commentaire"
    )
    satisfaction_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Taux de satisfaction (%)"
    )
    feedback_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Taux de feedback (feedbacks/messages assistant) en %"
    )
    total_messages: int = Field(
        ...,
        description="Nombre total de messages assistant"
    )


class FeedbackTrend(BaseModel):
    """Statistiques de feedback pour une journée."""
    
    trend_date: date = Field(
        ...,
        description="Date de la journée",
        alias="date"
    )
    total: int = Field(
        ...,
        description="Nombre total de feedbacks ce jour"
    )
    thumbs_up: int = Field(
        ...,
        description="Nombre de feedbacks positifs"
    )
    thumbs_down: int = Field(
        ...,
        description="Nombre de feedbacks négatifs"
    )
    satisfaction_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Taux de satisfaction pour ce jour (%)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class FeedbackTrendsResponse(BaseModel):
    """Réponse avec les tendances sur plusieurs jours."""
    
    trends: List[FeedbackTrend] = Field(
        ...,
        description="Tendances quotidiennes"
    )
    period_days: int = Field(
        ...,
        description="Nombre de jours analysés"
    )
    period_start_date: date = Field(
        ...,
        description="Date de début de la période",
        alias="start_date"
    )
    period_end_date: date = Field(
        ...,
        description="Date de fin de la période",
        alias="end_date"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# SCHEMAS LEGACY (COMPATIBILITÉ)
# =============================================================================

class FeedbackStatsByPeriod(BaseModel):
    """Statistiques des feedbacks par période (legacy)."""
    
    period: str = Field(..., description="Période (jour, semaine, mois)")
    date: datetime = Field(..., description="Date de début de la période")
    thumbs_up: int
    thumbs_down: int
    total: int
    satisfaction_rate: float


class FeedbackStatsResponse(BaseModel):
    """Réponse complète des statistiques de feedbacks (legacy)."""
    
    overall: FeedbackStats
    by_period: List[FeedbackStatsByPeriod] = Field(
        default_factory=list,
        description="Statistiques par période"
    )
    recent_negative: List[FeedbackWithContext] = Field(
        default_factory=list,
        description="Derniers feedbacks négatifs (pour analyse)"
    )


# =============================================================================
# SCHEMAS D'EXPORT
# =============================================================================

class FeedbackExportRequest(BaseModel):
    """Schema pour demander un export de feedbacks."""
    
    start_date: Optional[datetime] = Field(
        default=None,
        description="Date de début pour le filtre"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Date de fin pour le filtre"
    )
    rating: Optional[FeedbackRatingEnum] = Field(
        default=None,
        description="Filtrer par type de feedback"
    )
    include_context: bool = Field(
        default=True,
        description="Inclure le contexte (message, conversation)"
    )
    format: str = Field(
        default="json",
        pattern="^(json|csv)$",
        description="Format d'export : json ou csv"
    )