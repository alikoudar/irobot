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
"""

import logging
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.message import ChatRequest
from app.schemas.conversation import (
    ConversationResponse,
    ConversationListResponse,
    ConversationUpdate,
    ConversationArchive,
    ConversationSummaryListResponse
)
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
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
        EventSourceResponse avec les événements SSE
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
                
                yield {
                    "event": event_type,
                    "data": json.dumps(event_data, default=str)
                }
        
        except Exception as e:
            logger.error(f"Erreur streaming: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "code": "STREAM_ERROR"})
            }
    
    return EventSourceResponse(event_generator())


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
    from app.models.conversation import Conversation
    from sqlalchemy import and_
    
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
            from datetime import datetime
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
    from app.models.feedback import Feedback
    from sqlalchemy import and_
    
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
    from app.models.feedback import Feedback
    from sqlalchemy import and_
    
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