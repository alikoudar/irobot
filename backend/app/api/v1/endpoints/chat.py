# -*- coding: utf-8 -*-
"""
Endpoints API pour le chatbot.

Ce module expose les endpoints pour :
- POST /chat/stream : Envoyer un message et recevoir une réponse streamée (SSE)
- GET /conversations : Lister les conversations de l'utilisateur
- GET /conversations/{id} : Récupérer une conversation avec ses messages
- DELETE /conversations/{id} : Supprimer une conversation
- PUT /conversations/{id}/archive : Archiver/désarchiver une conversation
- POST /messages/{id}/feedback : Ajouter un feedback sur un message

Sprint 7 - Phase 4 : Endpoints Chat
Sprint 9 - Phase 1 : Recherche avancée, export, auto-archivage, stats feedbacks
"""

import logging
import json
import csv
import io
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, cast, Integer

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.schemas.message import ChatRequest
from app.schemas.conversation import (
    ConversationResponse,
    ConversationListResponse,
    ConversationUpdate,
    ConversationArchive,
    ConversationSummaryListResponse,
    AutoArchiveResponse
)
from app.schemas.feedback import (
    FeedbackCreate, 
    FeedbackResponse,
    FeedbackStats,
    FeedbackTrend,
    FeedbackTrendsResponse
)
from app.services.chat_service import get_chat_service

# Configuration du logger
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/chat", tags=["Chat"])


# =============================================================================
# ENDPOINTS CHAT
# =============================================================================

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envoie un message et reçoit une réponse streamée via SSE.
    
    Le streaming envoie les événements suivants :
    - start : Début du streaming (conversation_id, message_id)
    - sources : Sources citées dans la réponse
    - token : Token de la réponse (streamé)
    - metadata : Métadonnées finales (tokens, coûts, temps)
    - done : Fin du streaming
    - error : En cas d'erreur
    
    Args:
        request: Message et conversation_id optionnel
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        StreamingResponse avec les événements SSE
    """
    chat_service = get_chat_service()
    
    async def event_generator():
        """Générateur d'événements SSE."""
        try:
            async for event in chat_service.process_query_streaming(
                user=current_user,
                query=request.message,
                conversation_id=request.conversation_id,
                db=db
            ):
                event_type = event.get("event", "message")
                event_data = event.get("data", {})
                
                # Format SSE: chaque ligne doit commencer par "event:" ou "data:"
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data, default=str)}\n\n"
        
        except Exception as e:
            logger.error(f"Erreur streaming: {e}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e), 'code': 'STREAM_ERROR'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Désactiver le buffering Nginx
        }
    )


@router.post("", status_code=status.HTTP_200_OK)
async def chat_sync(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envoie un message et reçoit une réponse complète (non-streamée).
    
    Alternative au streaming pour les clients qui ne supportent pas SSE.
    
    Args:
        request: Message et conversation_id optionnel
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Réponse complète avec conversation_id, message_id, content, sources
    """
    chat_service = get_chat_service()
    
    # Collecter tous les événements
    result = {
        "conversation_id": None,
        "message_id": None,
        "content": "",
        "sources": [],
        "token_count_input": 0,
        "token_count_output": 0,
        "cost_usd": 0.0,
        "cost_xaf": 0.0,
        "cache_hit": False,
        "response_time_seconds": 0.0,
        "model_used": ""
    }
    
    async for event in chat_service.process_query_streaming(
        user=current_user,
        query=request.message,
        conversation_id=request.conversation_id,
        db=db
    ):
        event_type = event.get("event")
        event_data = event.get("data", {})
        
        if event_type == "start":
            result["conversation_id"] = event_data.get("conversation_id")
            result["message_id"] = event_data.get("message_id")
        
        elif event_type == "token":
            result["content"] += event_data.get("content", "")
        
        elif event_type == "sources":
            result["sources"] = event_data.get("sources", [])
        
        elif event_type == "metadata":
            result["token_count_input"] = event_data.get("token_count_input", 0)
            result["token_count_output"] = event_data.get("token_count_output", 0)
            result["cost_usd"] = event_data.get("cost_usd", 0.0)
            result["cost_xaf"] = event_data.get("cost_xaf", 0.0)
            result["cache_hit"] = event_data.get("cache_hit", False)
            result["response_time_seconds"] = event_data.get("response_time_seconds", 0.0)
            result["model_used"] = event_data.get("model_used", "")
        
        elif event_type == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=event_data.get("error", "Erreur de traitement")
            )
    
    return result


# =============================================================================
# ENDPOINTS CONVERSATIONS
# =============================================================================

@router.get("/conversations", response_model=ConversationSummaryListResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    page_size: int = Query(default=20, ge=1, le=100, description="Taille de la page"),
    include_archived: bool = Query(default=False, description="Inclure les conversations archivées"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ConversationSummaryListResponse:
    """
    Liste les conversations de l'utilisateur.
    
    Args:
        page: Numéro de page (1-indexed)
        page_size: Nombre d'éléments par page
        include_archived: Inclure les conversations archivées
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Liste paginée de conversations avec résumés
    """
    chat_service = get_chat_service()
    
    skip = (page - 1) * page_size
    conversations, total = chat_service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        include_archived=include_archived,
        db=db
    )
    
    has_more = (skip + len(conversations)) < total
    
    return ConversationSummaryListResponse(
        conversations=conversations,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/conversations/search/advanced", response_model=ConversationListResponse)
async def search_conversations_advanced(
    search: Optional[str] = Query(default=None, description="Texte à rechercher dans titre et messages"),
    start_date: Optional[datetime] = Query(default=None, description="Date de début (ISO format)"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin (ISO format)"),
    is_archived: Optional[bool] = Query(default=None, description="Filtrer par statut archivé"),
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    page_size: int = Query(default=20, ge=1, le=100, description="Taille de la page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ConversationListResponse:
    """
    Recherche avancée dans les conversations.
    
    Permet de chercher par :
    - Texte dans titre et contenu des messages
    - Plage de dates
    - Statut d'archivage
    
    Sprint 9 - Phase 1
    """
    skip = (page - 1) * page_size
    
    # Construction de la requête
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    # Filtre de recherche textuelle
    if search:
        # Recherche dans titre ET messages
        query = query.outerjoin(Message).filter(
            or_(
                Conversation.title.ilike(f"%{search}%"),
                Message.content.ilike(f"%{search}%")
            )
        ).distinct()
    
    # Filtre par dates
    if start_date:
        query = query.filter(Conversation.created_at >= start_date)
    if end_date:
        # Inclure toute la journée
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Conversation.created_at <= end_of_day)
    
    # Filtre par archivage
    if is_archived is not None:
        query = query.filter(Conversation.is_archived == is_archived)
    
    # Compter le total
    total = query.count()
    
    # Pagination et tri
    conversations = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(page_size).all()
    
    # Ajouter message_count
    for conv in conversations:
        conv.message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
    
    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/conversations/export")
async def export_conversations(
    format: str = Query(default="json", pattern="^(json|csv)$", description="Format d'export"),
    start_date: Optional[datetime] = Query(default=None, description="Date de début"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporte les conversations de l'utilisateur.
    
    Formats supportés : JSON, CSV
    Limite : 10000 conversations pour éviter timeout
    
    Sprint 9 - Phase 1
    """
    # Construction de la requête
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    if start_date:
        query = query.filter(Conversation.created_at >= start_date)
    if end_date:
        end_of_day = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Conversation.created_at <= end_of_day)
    
    # Limite de sécurité
    conversations = query.order_by(Conversation.created_at.desc()).limit(10000).all()
    
    if format == "json":
        # Export JSON avec messages
        data = []
        for conv in conversations:
            messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
            
            data.append({
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "is_archived": conv.is_archived,
                "message_count": len(messages),
                "messages": [
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "token_count_input": msg.token_count_input,
                        "token_count_output": msg.token_count_output,
                        "cost_usd": float(msg.cost_usd) if msg.cost_usd else 0.0,
                        "cost_xaf": float(msg.cost_xaf) if msg.cost_xaf else 0.0
                    }
                    for msg in messages
                ]
            })
        
        return {
            "data": data,
            "count": len(conversations),
            "format": "json",
            "exported_at": datetime.utcnow().isoformat()
        }
    
    else:  # CSV
        # Export CSV (un message par ligne)
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            "conversation_id", "conversation_title", "conversation_created_at",
            "message_id", "message_role", "message_content", "message_created_at",
            "tokens_input", "tokens_output", "cost_usd", "cost_xaf"
        ])
        
        # Données
        for conv in conversations:
            messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
            for msg in messages:
                writer.writerow([
                    str(conv.id),
                    conv.title,
                    conv.created_at.isoformat(),
                    str(msg.id),
                    msg.role,
                    msg.content[:500],  # Tronquer le contenu
                    msg.created_at.isoformat(),
                    msg.token_count_input or 0,
                    msg.token_count_output or 0,
                    float(msg.cost_usd) if msg.cost_usd else 0.0,
                    float(msg.cost_xaf) if msg.cost_xaf else 0.0
                ])
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=conversations_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )


@router.post("/conversations/auto-archive", response_model=AutoArchiveResponse)
async def auto_archive_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AutoArchiveResponse:
    """
    Archive automatiquement les anciennes conversations.
    
    Garde les 50 conversations les plus récentes actives,
    archive toutes les autres.
    
    Sprint 9 - Phase 1
    """
    threshold = 50
    
    # Récupérer toutes les conversations actives
    active_conversations = db.query(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.is_archived == False
        )
    ).order_by(Conversation.updated_at.desc()).all()
    
    # Si moins de threshold conversations, ne rien faire
    if len(active_conversations) <= threshold:
        return AutoArchiveResponse(
            archived_count=0,
            threshold=threshold,
            message=f"Vous avez {len(active_conversations)} conversations actives. Aucune archivage nécessaire."
        )
    
    # Archiver les conversations au-delà du threshold
    conversations_to_archive = active_conversations[threshold:]
    archived_count = 0
    
    for conv in conversations_to_archive:
        conv.is_archived = True
        conv.archived_at = datetime.utcnow()
        archived_count += 1
    
    db.commit()
    
    return AutoArchiveResponse(
        archived_count=archived_count,
        threshold=threshold,
        message=f"{archived_count} conversation(s) archivée(s) automatiquement. {threshold} conversations actives maintenues."
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère une conversation avec tous ses messages.
    
    Args:
        conversation_id: ID de la conversation
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Conversation avec la liste des messages
    
    Raises:
        HTTPException 404: Conversation non trouvée
    """
    chat_service = get_chat_service()
    
    result = chat_service.get_conversation_with_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        db=db
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )
    
    return result


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprime une conversation et tous ses messages.
    
    Args:
        conversation_id: ID de la conversation
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Raises:
        HTTPException 404: Conversation non trouvée
    """
    chat_service = get_chat_service()
    
    success = chat_service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )
    
    return None


@router.put("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: UUID,
    request: ConversationArchive,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archive ou désarchive une conversation.
    
    Args:
        conversation_id: ID de la conversation
        request: is_archived = True pour archiver, False pour désarchiver
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Conversation mise à jour
    
    Raises:
        HTTPException 404: Conversation non trouvée
    """
    chat_service = get_chat_service()
    
    conversation = chat_service.archive_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        archive=request.is_archived,
        db=db
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )
    
    return ConversationResponse.model_validate(conversation)


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour une conversation (titre, archivage).
    
    Args:
        conversation_id: ID de la conversation
        request: Champs à mettre à jour
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Conversation mise à jour
    
    Raises:
        HTTPException 404: Conversation non trouvée
    """
    conversation = db.query(Conversation).filter(
        and_(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )
    
    # Mettre à jour les champs fournis
    if request.title is not None:
        conversation.title = request.title
    
    if request.is_archived is not None:
        conversation.is_archived = request.is_archived
        if request.is_archived:
            conversation.archived_at = datetime.utcnow()
        else:
            conversation.archived_at = None
    
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse.model_validate(conversation)


# =============================================================================
# ENDPOINTS FEEDBACKS
# =============================================================================

@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse)
async def add_feedback(
    message_id: UUID,
    request: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajoute un feedback sur un message.
    
    Un seul feedback par utilisateur et par message est autorisé.
    Si un feedback existe déjà, il sera mis à jour.
    
    Args:
        message_id: ID du message
        request: Rating et commentaire optionnel
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Feedback créé ou mis à jour
    
    Raises:
        HTTPException 404: Message non trouvé
    """
    # Vérifier que le message_id de la requête correspond à l'URL
    if request.message_id != message_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID du message dans la requête ne correspond pas à l'URL"
        )
    
    chat_service = get_chat_service()
    
    feedback = chat_service.add_feedback(
        message_id=message_id,
        user_id=current_user.id,
        rating=request.rating.value,
        comment=request.comment,
        db=db
    )
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message non trouvé ou accès refusé"
        )
    
    return FeedbackResponse.model_validate(feedback)


@router.get("/messages/{message_id}/feedback", response_model=Optional[FeedbackResponse])
async def get_feedback(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère le feedback d'un utilisateur sur un message.
    
    Args:
        message_id: ID du message
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Returns:
        Feedback si existant, null sinon
    """
    feedback = db.query(Feedback).filter(
        and_(
            Feedback.message_id == message_id,
            Feedback.user_id == current_user.id
        )
    ).first()
    
    if not feedback:
        return None
    
    return FeedbackResponse.model_validate(feedback)


@router.delete("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprime le feedback d'un utilisateur sur un message.
    
    Args:
        message_id: ID du message
        current_user: Utilisateur authentifié
        db: Session de base de données
    
    Raises:
        HTTPException 404: Feedback non trouvé
    """
    feedback = db.query(Feedback).filter(
        and_(
            Feedback.message_id == message_id,
            Feedback.user_id == current_user.id
        )
    ).first()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback non trouvé"
        )
    
    db.delete(feedback)
    db.commit()
    
    return None


@router.get("/feedbacks/statistics", response_model=FeedbackStats)
async def get_feedback_statistics(
    start_date: Optional[datetime] = Query(default=None, description="Date de début"),
    end_date: Optional[datetime] = Query(default=None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FeedbackStats:
    """
    Récupère les statistiques de feedback de l'utilisateur.
    
    Sprint 9 - Phase 1
    """
    # Construction de la requête feedbacks
    feedback_query = db.query(Feedback).filter(Feedback.user_id == current_user.id)
    
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
    with_comments = sum(1 for f in feedbacks if f.comment)
    
    # Calcul taux de satisfaction
    satisfaction_rate = (thumbs_up / total_feedbacks * 100) if total_feedbacks > 0 else 0.0
    
    # Nombre total de messages assistant
    message_query = db.query(Message).join(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Message.role == "ASSISTANT"
        )
    )
    
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


@router.get("/feedbacks/trends", response_model=FeedbackTrendsResponse)
async def get_feedback_trends(
    days: int = Query(default=30, ge=1, le=365, description="Nombre de jours à analyser"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> FeedbackTrendsResponse:
    """
    Récupère les tendances de feedback sur N jours (admin seulement).
    
    Agrège les feedbacks par jour pour analyser l'évolution.
    
    Sprint 9 - Phase 1
    """
    # Calcul des dates
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # Requête avec agrégation par jour
    trends_data = db.query(
        func.date(Feedback.created_at).label('date'),
        func.count(Feedback.id).label('total'),
        func.sum(cast(Feedback.rating == "THUMBS_UP", Integer)).label('thumbs_up'),
        func.sum(cast(Feedback.rating == "THUMBS_DOWN", Integer)).label('thumbs_down')
    ).filter(
        func.date(Feedback.created_at) >= start_date
    ).group_by(
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
            date=row.date,  # Pydantic utilise l'alias
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