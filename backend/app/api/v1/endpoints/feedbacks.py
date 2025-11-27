# -*- coding: utf-8 -*-
"""
Endpoints API pour les feedbacks - VERSION CORRIGÉE

Ce module expose les endpoints pour :
- GET /feedbacks : Lister les feedbacks avec filtres (pagination, rating, commentaires)
- GET /feedbacks/stats : Statistiques feedbacks globales ou par utilisateur
- GET /feedbacks/trends : Tendances feedbacks sur N jours
- GET /feedbacks/export : Export CSV des feedbacks

CORRECTIONS :
- Ajout jointures User pour récupérer nom, prénom, matricule
- Ajout jointures Message pour récupérer contenu et rôle message
- Ajout jointures Conversation pour conversation_id
- Enrichissement FeedbackResponse avec infos utilisateur

Sprint 9 - Phase 1 : Stats feedbacks et analyse
"""

import logging
import csv
import io
import json
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, cast, Integer, case
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackResponse,
    FeedbackStats,
    FeedbackTrend,
    FeedbackTrendsResponse
)

# Configuration du logger
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])


# =============================================================================
# SCHEMAS ENRICHIS
# =============================================================================

class EnrichedFeedbackResponse(BaseModel):
    """Feedback enrichi avec infos utilisateur et message."""
    # Champs Feedback
    id: UUID
    message_id: UUID
    user_id: UUID
    rating: str
    comment: Optional[str] = None
    created_at: datetime
    
    # Champs User (enrichis)
    user_nom: Optional[str] = None
    user_prenom: Optional[str] = None
    user_matricule: Optional[str] = None
    user_email: Optional[str] = None
    
    # Champs Message (enrichis)
    message_content: Optional[str] = None
    message_role: Optional[str] = None
    conversation_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Réponse paginée de la liste des feedbacks."""
    feedbacks: List[EnrichedFeedbackResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS FEEDBACKS
# =============================================================================

@router.get("", response_model=FeedbackListResponse)
async def list_feedbacks(
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    page_size: int = Query(default=20, ge=1, le=100, description="Taille de la page"),
    user_id: Optional[UUID] = Query(default=None, description="Filtrer par utilisateur (admin uniquement)"),
    rating: Optional[str] = Query(default=None, description="Filtrer par rating (THUMBS_UP, THUMBS_DOWN)"),
    has_comment: Optional[bool] = Query(default=None, description="Filtrer par présence de commentaire"),
    start_date: Optional[datetime] = Query(default=None, description="Date de début"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FeedbackListResponse:
    """
    Liste les feedbacks avec filtres et pagination.
    
    CORRECTIONS :
    - Jointure avec User pour récupérer nom, prénom, matricule
    - Jointure avec Message pour récupérer contenu et rôle
    - Jointure avec Conversation pour conversation_id
    
    - Utilisateur normal : Voit uniquement ses propres feedbacks
    - Admin : Peut voir tous les feedbacks ou filtrer par user_id
    
    Args:
        page: Numéro de page (1-indexed)
        page_size: Nombre d'éléments par page
        user_id: Filtrer par utilisateur (admin uniquement)
        rating: Filtrer par rating
        has_comment: Filtrer par présence de commentaire
        start_date: Date de début
        end_date: Date de fin
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Liste paginée de feedbacks enrichis
    """
    # Construction de la requête avec jointures
    query = db.query(
        Feedback,
        User.nom.label('user_nom'),
        User.prenom.label('user_prenom'),
        User.matricule.label('user_matricule'),
        User.email.label('user_email'),
        Message.content.label('message_content'),
        Message.role.label('message_role'),
        Message.conversation_id.label('conversation_id')
    ).join(
        User, Feedback.user_id == User.id
    ).join(
        Message, Feedback.message_id == Message.id
    )
    
    # Filtre par utilisateur
    if current_user.role == "ADMIN":
        # Admin peut voir tous les feedbacks ou filtrer par user_id
        if user_id:
            query = query.filter(Feedback.user_id == user_id)
    else:
        # Utilisateur normal voit uniquement ses feedbacks
        query = query.filter(Feedback.user_id == current_user.id)
    
    # Filtre par rating
    if rating:
        query = query.filter(Feedback.rating == rating)
    
    # Filtre par commentaire
    if has_comment is not None:
        if has_comment:
            query = query.filter(Feedback.comment.isnot(None), Feedback.comment != "")
        else:
            query = query.filter(or_(Feedback.comment.is_(None), Feedback.comment == ""))
    
    # Filtre par dates
    if start_date:
        query = query.filter(Feedback.created_at >= start_date)
    if end_date:
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Feedback.created_at <= end_of_day)
    
    # Compter le total
    total = query.count()
    
    # Pagination
    skip = (page - 1) * page_size
    results = query.order_by(Feedback.created_at.desc()).offset(skip).limit(page_size).all()
    
    # Construire les réponses enrichies
    enriched_feedbacks = []
    for row in results:
        feedback = row[0]  # Objet Feedback
        
        enriched_feedback = EnrichedFeedbackResponse(
            # Champs Feedback
            id=feedback.id,
            message_id=feedback.message_id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            comment=feedback.comment,
            created_at=feedback.created_at,
            
            # Champs User (jointure)
            user_nom=row.user_nom,
            user_prenom=row.user_prenom,
            user_matricule=row.user_matricule,
            user_email=row.user_email,
            
            # Champs Message (jointure)
            message_content=row.message_content,
            message_role=row.message_role,
            conversation_id=row.conversation_id
        )
        enriched_feedbacks.append(enriched_feedback)
    
    return FeedbackListResponse(
        feedbacks=enriched_feedbacks,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(results)) < total
    )


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    user_id: Optional[UUID] = Query(default=None, description="Filtrer par utilisateur (admin uniquement)"),
    start_date: Optional[datetime] = Query(default=None, description="Date de début"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FeedbackStats:
    """
    Récupère les statistiques de feedback.
    
    - Utilisateur normal : Voit uniquement ses propres stats
    - Admin : Peut voir les stats globales ou d'un utilisateur spécifique
    
    Args:
        user_id: Filtrer par utilisateur (admin uniquement)
        start_date: Date de début
        end_date: Date de fin
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Statistiques feedbacks
    """
    # Déterminer l'utilisateur cible
    target_user_id = None
    if current_user.role == "ADMIN":
        # Admin peut voir stats globales (user_id=None) ou d'un utilisateur spécifique
        target_user_id = user_id
    else:
        # Utilisateur normal voit uniquement ses stats
        target_user_id = current_user.id
    
    # Construction de la requête feedbacks
    feedback_query = db.query(Feedback)
    
    if target_user_id:
        feedback_query = feedback_query.filter(Feedback.user_id == target_user_id)
    
    if start_date:
        feedback_query = feedback_query.filter(Feedback.created_at >= start_date)
    if end_date:
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        feedback_query = feedback_query.filter(Feedback.created_at <= end_of_day)
    
    # Statistiques feedbacks
    feedbacks = feedback_query.all()
    total_feedbacks = len(feedbacks)
    thumbs_up = sum(1 for f in feedbacks if f.rating == "THUMBS_UP")
    thumbs_down = sum(1 for f in feedbacks if f.rating == "THUMBS_DOWN")
    with_comments = sum(1 for f in feedbacks if f.comment and f.comment.strip())
    
    # Calcul taux de satisfaction
    satisfaction_rate = (thumbs_up / total_feedbacks * 100) if total_feedbacks > 0 else 0.0
    
    # Nombre total de messages assistant
    message_query = db.query(Message).join(Conversation).filter(
        Message.role == "ASSISTANT"
    )
    
    if target_user_id:
        message_query = message_query.filter(Conversation.user_id == target_user_id)
    
    if start_date:
        message_query = message_query.filter(Message.created_at >= start_date)
    if end_date:
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        message_query = message_query.filter(Message.created_at <= end_of_day)
    
    total_messages = message_query.count()
    
    # Calcul taux de feedback
    feedback_rate = (total_feedbacks / total_messages * 100) if total_messages > 0 else 0.0
    
    return FeedbackStats(
        total_feedbacks=total_feedbacks,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        with_comments=with_comments,
        satisfaction_rate=round(satisfaction_rate, 2),
        feedback_rate=round(feedback_rate, 2),
        total_messages=total_messages
    )


@router.get("/trends", response_model=FeedbackTrendsResponse)
async def get_feedback_trends(
    days: int = Query(default=30, ge=1, le=365, description="Nombre de jours à analyser"),
    user_id: Optional[UUID] = Query(default=None, description="Filtrer par utilisateur (admin uniquement)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FeedbackTrendsResponse:
    """
    Récupère les tendances de feedback sur N jours.
    
    Agrège les feedbacks par jour pour analyser l'évolution.
    
    - Utilisateur normal : Voit uniquement ses propres tendances
    - Admin : Peut voir les tendances globales ou d'un utilisateur spécifique
    
    Args:
        days: Nombre de jours à analyser
        user_id: Filtrer par utilisateur (admin uniquement)
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Tendances feedbacks
    """
    # Déterminer l'utilisateur cible
    target_user_id = None
    if current_user.role == "ADMIN":
        # Admin peut voir tendances globales ou d'un utilisateur spécifique
        target_user_id = user_id
    else:
        # Utilisateur normal voit uniquement ses tendances
        target_user_id = current_user.id
    
    # Calcul des dates
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # Construction de la requête avec agrégation par jour
    query = db.query(
        func.date(Feedback.created_at).label('date'),
        func.count(Feedback.id).label('total'),
        func.sum(case((Feedback.rating == "THUMBS_UP", 1), else_=0)).label('thumbs_up'),
        func.sum(case((Feedback.rating == "THUMBS_DOWN", 1), else_=0)).label('thumbs_down')
    ).filter(
        func.date(Feedback.created_at) >= start_date
    )
    
    if target_user_id:
        query = query.filter(Feedback.user_id == target_user_id)
    
    trends_data = query.group_by(
        func.date(Feedback.created_at)
    ).order_by(
        func.date(Feedback.created_at)
    ).all()
    
    # Construire les tendances
    trends = []
    for row in trends_data:
        total = row.total or 0
        thumbs_up = row.thumbs_up or 0
        thumbs_down = row.thumbs_down or 0
        satisfaction_rate = (thumbs_up / total * 100) if total > 0 else 0.0
        
        trends.append(FeedbackTrend(
            date=row.date,
            total=total,
            thumbs_up=thumbs_up,
            thumbs_down=thumbs_down,
            satisfaction_rate=round(satisfaction_rate, 2)
        ))
    
    return FeedbackTrendsResponse(
        trends=trends,
        period_days=days,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/export")
async def export_feedbacks(
    format: str = Query(default="csv", description="Format d'export (csv, json)"),
    user_id: Optional[UUID] = Query(default=None, description="Filtrer par utilisateur (admin uniquement)"),
    rating: Optional[str] = Query(default=None, description="Filtrer par rating"),
    has_comment: Optional[bool] = Query(default=None, description="Filtrer par présence de commentaire"),
    start_date: Optional[datetime] = Query(default=None, description="Date de début"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporte les feedbacks en CSV ou JSON avec infos enrichies.
    
    - Utilisateur normal : Exporte uniquement ses propres feedbacks
    - Admin : Peut exporter tous les feedbacks ou filtrer par user_id
    
    Args:
        format: Format d'export (csv, json)
        user_id: Filtrer par utilisateur (admin uniquement)
        rating: Filtrer par rating
        has_comment: Filtrer par présence de commentaire
        start_date: Date de début
        end_date: Date de fin
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Fichier CSV ou JSON des feedbacks
    """
    # Construction de la requête avec jointures
    query = db.query(
        Feedback,
        User.nom.label('user_nom'),
        User.prenom.label('user_prenom'),
        User.matricule.label('user_matricule'),
        Message.content.label('message_content'),
        Message.role.label('message_role')
    ).join(
        User, Feedback.user_id == User.id
    ).join(
        Message, Feedback.message_id == Message.id
    )
    
    # Filtre par utilisateur
    if current_user.role == "ADMIN":
        if user_id:
            query = query.filter(Feedback.user_id == user_id)
    else:
        query = query.filter(Feedback.user_id == current_user.id)
    
    # Filtres additionnels
    if rating:
        query = query.filter(Feedback.rating == rating)
    if has_comment is not None:
        if has_comment:
            query = query.filter(Feedback.comment.isnot(None), Feedback.comment != "")
        else:
            query = query.filter(or_(Feedback.comment.is_(None), Feedback.comment == ""))
    if start_date:
        query = query.filter(Feedback.created_at >= start_date)
    if end_date:
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Feedback.created_at <= end_of_day)
    
    # Récupérer les feedbacks
    results = query.order_by(Feedback.created_at.desc()).all()
    
    if format.lower() == "csv":
        # Export CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes enrichis
        writer.writerow([
            "ID", "Message ID", "User ID", "User Nom", "User Prenom", "User Matricule",
            "Rating", "Comment", "Message Content", "Message Role",
            "Created At"
        ])
        
        # Données enrichies
        for row in results:
            feedback = row[0]
            writer.writerow([
                str(feedback.id),
                str(feedback.message_id),
                str(feedback.user_id),
                row.user_nom or "",
                row.user_prenom or "",
                row.user_matricule or "",
                feedback.rating,
                feedback.comment or "",
                row.message_content or "",
                row.message_role or "",
                feedback.created_at.isoformat()
            ])
        
        # Retourner le CSV
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=feedbacks_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    elif format.lower() == "json":
        # Export JSON enrichi
        feedback_list = []
        for row in results:
            feedback = row[0]
            feedback_list.append({
                "id": str(feedback.id),
                "message_id": str(feedback.message_id),
                "user_id": str(feedback.user_id),
                "user_nom": row.user_nom,
                "user_prenom": row.user_prenom,
                "user_matricule": row.user_matricule,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "message_content": row.message_content,
                "message_role": row.message_role,
                "created_at": feedback.created_at.isoformat()
            })
        
        return Response(
            content=json.dumps(feedback_list, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=feedbacks_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format non supporté: {format}. Utilisez 'csv' ou 'json'."
        )