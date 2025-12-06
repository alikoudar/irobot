# -*- coding: utf-8 -*-
"""
ChatService - Service d'orchestration du pipeline RAG pour le chatbot.

Ce service gère le flux complet d'une requête utilisateur :
1. Vérification du cache (L1 puis L2)
2. Si miss : Embedding → Recherche hybride → Reranking → Génération
3. Sauvegarde dans le cache
4. Gestion des conversations et messages
5. Génération automatique des titres
6. Tracking des tokens et coûts

Sprint 7 - Phase 3 : Chat Service
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
import asyncio
from app.services.notification import NotificationService

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.feedback import Feedback, FeedbackRating
from app.models.token_usage import TokenUsage, OperationType
from app.schemas.message import (
    ChatRequest,
    ChatStreamStartEvent,
    ChatStreamTokenEvent,
    ChatStreamSourcesEvent,
    ChatStreamMetadataEvent,
    ChatStreamEndEvent,
    ChatStreamErrorEvent,
    SourceReference,
    MessageResponse
)
from app.schemas.conversation import ConversationResponse, ConversationSummary

def _send_notification_in_thread(notification_func: str, **kwargs):
    """
    Exécute une notification dans un thread séparé avec sa propre session DB et event loop.
    
    Cette approche garantit que la notification est envoyée même si la requête
    HTTP se termine avant.
    
    Args:
        notification_func: Nom de la méthode NotificationService à appeler
        **kwargs: Arguments à passer à la méthode (sans db)
    """
    import threading
    
    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        db = SessionLocal()
        try:
            method = getattr(NotificationService, notification_func)
            loop.run_until_complete(method(db=db, **kwargs))
            logger.info(f"✅ Notification {notification_func} envoyée avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur notification {notification_func}: {e}", exc_info=True)
        finally:
            db.close()
            loop.close()
    
    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    logger.info(f"🔔 Thread notification {notification_func} démarré")

# Configuration du logger
logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT
# =============================================================================

DEFAULT_HISTORY_LIMIT = 5
DEFAULT_SEARCH_TOP_K = 10
DEFAULT_RERANK_TOP_N = 3


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_chat_config() -> Dict[str, Any]:
    """
    Récupère la configuration du chat depuis la DB.
    
    Returns:
        Dict avec history_limit, search_top_k, rerank_top_n
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            return {
                "history_limit": service.get_value(
                    "chat.history_limit", db, default=DEFAULT_HISTORY_LIMIT
                ),
                "search_top_k": service.get_value(
                    "search.top_k", db, default=DEFAULT_SEARCH_TOP_K
                ),
                "rerank_top_n": service.get_value(
                    "search.rerank_top_n", db, default=DEFAULT_RERANK_TOP_N
                ),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config chat: {e}")
        return {
            "history_limit": DEFAULT_HISTORY_LIMIT,
            "search_top_k": DEFAULT_SEARCH_TOP_K,
            "rerank_top_n": DEFAULT_RERANK_TOP_N,
        }


# =============================================================================
# CHAT SERVICE
# =============================================================================

class ChatService:
    """
    Service d'orchestration du pipeline RAG.
    
    Gère le flux complet d'une requête utilisateur depuis la réception
    jusqu'à la génération de la réponse streamée.
    """
    
    def __init__(self):
        """Initialise le ChatService."""
        # Import différé pour éviter les imports circulaires
        from app.clients.mistral_client import get_mistral_client
        from app.rag.retriever import get_retriever
        from app.rag.reranker import get_reranker
        from app.rag.generator import get_generator
        from app.services.cache_service import get_cache_service
        
        self.mistral_client = get_mistral_client()
        self.retriever = get_retriever()
        self.reranker = get_reranker()
        self.generator = get_generator()
        self.cache_service = get_cache_service()
        
        config = get_chat_config()
        logger.info(
            f"ChatService initialisé - History: {config['history_limit']}, "
            f"TopK: {config['search_top_k']}, TopN: {config['rerank_top_n']}"
        )

    def _truncate_excerpt(self, text: Optional[str], max_length: int = 500) -> Optional[str]:
        '''Tronque l'extrait à max_length caractères.'''
        if not text:
            return None
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."   
    
    # =========================================================================
    # PIPELINE PRINCIPAL
    # =========================================================================
    
    async def process_query_streaming(
        self,
        user: User,
        query: str,
        conversation_id: Optional[UUID] = None,
        db: Session = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Traite une requête utilisateur avec streaming.
        
        Pipeline complet :
        1. Créer/récupérer la conversation
        2. Sauvegarder le message utilisateur
        3. Vérifier le cache (L1 puis L2)
        4. Si miss : Embedding → Search → Rerank → Generate
        5. Sauvegarder la réponse et le cache
        6. Générer le titre si première question
        7. Streamer les tokens
        
        Args:
            user: Utilisateur authentifié
            query: Question de l'utilisateur
            conversation_id: ID de la conversation (optionnel)
            db: Session de base de données
        
        Yields:
            Dict avec les événements SSE (start, token, sources, metadata, done, error)
        """
        start_time = time.time()
        
        # Créer une session si non fournie
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            # 1. Créer ou récupérer la conversation
            conversation, is_new_conversation = await self._get_or_create_conversation(
                user_id=user.id,
                conversation_id=conversation_id,
                db=db
            )
            
            # 2. Sauvegarder le message utilisateur
            user_message = self._save_user_message(
                conversation_id=conversation.id,
                content=query,
                db=db
            )
            
            # Envoyer l'événement de démarrage
            assistant_message_id = uuid.uuid4()
            yield {
                "event": "start",
                "data": ChatStreamStartEvent(
                    conversation_id=conversation.id,
                    message_id=assistant_message_id,
                    is_new_conversation=is_new_conversation
                ).model_dump()
            }
            
            # 3. Générer l'embedding de la question
            query_embedding = await self._embed_query(query)
            
            # 4. Vérifier le cache
            cache_result = self.cache_service.check_cache(
                query=query,
                query_embedding=query_embedding,
                db=db
            )
            
            if cache_result:
                # Cache HIT - Retourner la réponse cachée
                logger.info(f"Cache HIT (level {cache_result['cache_level']})")
                
                async for event in self._stream_cached_response(
                    cache_result=cache_result,
                    conversation=conversation,
                    assistant_message_id=assistant_message_id,
                    start_time=start_time,
                    is_new_conversation=is_new_conversation,
                    query=query,
                    db=db
                ):
                    yield event
            else:
                # Cache MISS - Pipeline RAG complet
                logger.info("Cache MISS - Exécution pipeline RAG")
                
                async for event in self._execute_rag_pipeline(
                    query=query,
                    query_embedding=query_embedding,
                    conversation=conversation,
                    assistant_message_id=assistant_message_id,
                    start_time=start_time,
                    is_new_conversation=is_new_conversation,
                    user=user,
                    db=db
                ):
                    yield event
            
        except Exception as e:
            logger.error(f"Erreur dans process_query_streaming: {e}")
            yield {
                "event": "error",
                "data": ChatStreamErrorEvent(
                    error=str(e),
                    code="PROCESSING_ERROR"
                ).model_dump()
            }
        
        finally:
            if close_db:
                db.close()
    
    async def _stream_cached_response(
        self,
        cache_result: Dict[str, Any],
        conversation: Conversation,
        assistant_message_id: UUID,
        start_time: float,
        is_new_conversation: bool,
        query: str,
        db: Session
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streame une réponse depuis le cache.
        
        Args:
            cache_result: Résultat du cache
            conversation: Conversation en cours
            assistant_message_id: ID du message assistant
            start_time: Timestamp de début
            is_new_conversation: Si c'est une nouvelle conversation
            query: Question originale
            db: Session DB
        
        Yields:
            Événements SSE
        """
        response_content = cache_result["response"]
        sources = cache_result.get("sources", [])
        
        # Envoyer les sources
        source_refs = [
                SourceReference(
                    document_id=s.get("document_id", ""),
                    title=s.get("title", ""),
                    category=s.get("category"),
                    page=s.get("page"),
                    chunk_index=s.get("chunk_index"),
                    relevance_score=s.get("relevance_score"),
                    excerpt=self._truncate_excerpt(s.get("text") or s.get("content") or s.get("excerpt"))
                )
                for s in sources
            ]
        
        yield {
            "event": "sources",
            "data": ChatStreamSourcesEvent(sources=source_refs).model_dump()
        }
        
        # Streamer les tokens (simulé par chunks)
        chunk_size = 20  # Caractères par chunk
        for i in range(0, len(response_content), chunk_size):
            chunk = response_content[i:i + chunk_size]
            yield {
                "event": "token",
                "data": ChatStreamTokenEvent(content=chunk).model_dump()
            }
        
        # Calculer les métadonnées
        response_time = time.time() - start_time
        token_count = cache_result.get("token_count", 0)
        
        # Sauvegarder le message assistant
        assistant_message = self._save_assistant_message(
            id=assistant_message_id,
            conversation_id=conversation.id,
            content=response_content,
            sources=sources,
            token_count_input=0,
            token_count_output=token_count,
            cost_usd=0.0,
            cost_xaf=0.0,
            model_used="cached",
            cache_hit=True,
            cache_key=cache_result.get("cache_id"),
            response_time_seconds=response_time,
            db=db
        )
        
        # Générer le titre si nouvelle conversation
        if is_new_conversation:
            await self._generate_and_save_title(conversation, query, db)
        
        # Envoyer les métadonnées
        yield {
            "event": "metadata",
            "data": ChatStreamMetadataEvent(
                token_count_input=0,
                token_count_output=token_count,
                cost_usd=0.0,
                cost_xaf=0.0,
                cache_hit=True,
                response_time_seconds=response_time,
                model_used="cached"
            ).model_dump()
        }
        
        # Envoyer l'événement de fin
        yield {
            "event": "done",
            "data": ChatStreamEndEvent(message_id=assistant_message_id).model_dump()
        }
    
    async def _execute_rag_pipeline(
        self,
        query: str,
        query_embedding: List[float],
        conversation: Conversation,
        assistant_message_id: UUID,
        start_time: float,
        is_new_conversation: bool,
        user: User,
        db: Session
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Exécute le pipeline RAG complet avec streaming.
        
        Args:
            query: Question de l'utilisateur
            query_embedding: Embedding de la question
            conversation: Conversation en cours
            assistant_message_id: ID du message assistant
            start_time: Timestamp de début
            is_new_conversation: Si nouvelle conversation
            user: Utilisateur
            db: Session DB
        
        Yields:
            Événements SSE
        """
        # 1. Recherche hybride
        chunks = await self.retriever.search(
            query=query,
            top_k=get_chat_config()["search_top_k"]
        )
        
        if not chunks:
            # Aucun résultat de recherche
            from app.rag.prompts import NO_CONTEXT_RESPONSE
            
            yield {
                "event": "token",
                "data": ChatStreamTokenEvent(content=NO_CONTEXT_RESPONSE).model_dump()
            }
            
            response_time = time.time() - start_time
            
            # Sauvegarder le message
            self._save_assistant_message(
                id=assistant_message_id,
                conversation_id=conversation.id,
                content=NO_CONTEXT_RESPONSE,
                sources=[],
                token_count_input=0,
                token_count_output=len(NO_CONTEXT_RESPONSE) // 4,
                cost_usd=0.0,
                cost_xaf=0.0,
                model_used="none",
                cache_hit=False,
                response_time_seconds=response_time,
                db=db
            )
            
            if is_new_conversation:
                await self._generate_and_save_title(conversation, query, db)
            
            yield {
                "event": "metadata",
                "data": ChatStreamMetadataEvent(
                    token_count_input=0,
                    token_count_output=len(NO_CONTEXT_RESPONSE) // 4,
                    cost_usd=0.0,
                    cost_xaf=0.0,
                    cache_hit=False,
                    response_time_seconds=response_time,
                    model_used="none"
                ).model_dump()
            }
            
            yield {
                "event": "done",
                "data": ChatStreamEndEvent(message_id=assistant_message_id).model_dump()
            }
            return
        
        # 2. Reranking
        reranked_results = await self.reranker.rerank(
            query=query,
            chunks=chunks,
            top_n=get_chat_config()["rerank_top_n"],
            user_id=user.id,  
            db=db   
        )
        
        # Convertir en format dict pour le generator
        chunks_for_generation = [
            result.chunk.to_dict() for result in reranked_results
        ]
        
        # Extraire les sources
        sources = []
        for result in reranked_results:
            chunk = result.chunk
            source_dict = chunk.to_source_dict()
            # Ajouter explicitement le texte du chunk
            if hasattr(chunk, 'text') and chunk.text:
                source_dict['text'] = chunk.text
            elif hasattr(chunk, 'content') and chunk.content:
                source_dict['text'] = chunk.content
            # Ajouter le score de pertinence
            source_dict['relevance_score'] = result.relevance_score / 10.0
            sources.append(source_dict)
        
        # Envoyer les sources
        source_refs = [
            SourceReference(
                document_id=s.get("document_id", ""),
                title=s.get("title", ""),
                category=s.get("category"),
                page=s.get("page"),
                chunk_index=s.get("chunk_index"),
                relevance_score=s.get("relevance_score"),
                excerpt=self._truncate_excerpt(s.get("text") or s.get("content") or s.get("excerpt"))
            )
            for s in sources
        ]
        
        yield {
            "event": "sources",
            "data": ChatStreamSourcesEvent(sources=source_refs).model_dump()
        }
        
        # 3. Récupérer l'historique
        history = self._get_conversation_history(
            conversation_id=conversation.id,
            limit=get_chat_config()["history_limit"],
            db=db
        )
        
        # 4. Génération streamée
        full_response = ""
        total_tokens_input = 0
        total_tokens_output = 0
        model_used = ""
        
        async for chunk in self.generator.generate_streaming(
            query=query,
            chunks=chunks_for_generation,
            history=history
        ):
            if chunk.type == "token" and chunk.content:
                full_response += chunk.content
                yield {
                    "event": "token",
                    "data": ChatStreamTokenEvent(content=chunk.content).model_dump()
                }
            
            elif chunk.type == "metadata" and chunk.metadata:
                total_tokens_input = chunk.metadata.token_count_input
                total_tokens_output = chunk.metadata.token_count_output
                model_used = chunk.metadata.model_used
            
            elif chunk.type == "error":
                yield {
                    "event": "error",
                    "data": ChatStreamErrorEvent(
                        error=chunk.error or "Erreur de génération",
                        code="GENERATION_ERROR"
                    ).model_dump()
                }
                return
        
        response_time = time.time() - start_time
        
        # 5. Calculer les coûts
        from app.rag.generator import get_generation_pricing, get_exchange_rate
        pricing = get_generation_pricing()
        cost_usd = (
            (total_tokens_input / 1_000_000) * pricing.get("price_per_million_input", 0.4) +
            (total_tokens_output / 1_000_000) * pricing.get("price_per_million_output", 2.0)
        )
        cost_xaf = cost_usd * get_exchange_rate()
        
        # 6. Sauvegarder le message assistant
        assistant_message = self._save_assistant_message(
            id=assistant_message_id,
            conversation_id=conversation.id,
            content=full_response,
            sources=sources,
            token_count_input=total_tokens_input,
            token_count_output=total_tokens_output,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            model_used=model_used,
            cache_hit=False,
            response_time_seconds=response_time,
            db=db
        )
        
        # 7. Sauvegarder dans le cache
        document_ids = list(set(s.get("document_id", "") for s in sources if s.get("document_id")))
        self.cache_service.save_to_cache(
            query=query,
            query_embedding=query_embedding,
            response=full_response,
            sources=sources,
            document_ids=document_ids,
            tokens=total_tokens_input + total_tokens_output,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            db=db
        )
        
        # 8. Tracker l'utilisation des tokens
        self._track_token_usage(
            operation_type=OperationType.RESPONSE_GENERATION,
            user_id=user.id,
            model_name=model_used,
            token_count_input=total_tokens_input,
            token_count_output=total_tokens_output,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            db=db,
            message_id=assistant_message_id
        )
        
        # 9. Générer le titre si nouvelle conversation
        if is_new_conversation:
            await self._generate_and_save_title(conversation, query, db)
        
        # Envoyer les métadonnées finales
        yield {
            "event": "metadata",
            "data": ChatStreamMetadataEvent(
                token_count_input=total_tokens_input,
                token_count_output=total_tokens_output,
                cost_usd=cost_usd,
                cost_xaf=cost_xaf,
                cache_hit=False,
                response_time_seconds=response_time,
                model_used=model_used
            ).model_dump()
        }
        
        # Envoyer l'événement de fin
        yield {
            "event": "done",
            "data": ChatStreamEndEvent(message_id=assistant_message_id).model_dump()
        }
    
    # =========================================================================
    # GESTION DES CONVERSATIONS
    # =========================================================================
    
    async def _get_or_create_conversation(
        self,
        user_id: UUID,
        conversation_id: Optional[UUID],
        db: Session
    ) -> tuple[Conversation, bool]:
        """
        Récupère ou crée une conversation.
        
        Args:
            user_id: ID de l'utilisateur
            conversation_id: ID de la conversation (optionnel)
            db: Session DB
        
        Returns:
            Tuple (conversation, is_new)
        """
        if conversation_id:
            # Récupérer la conversation existante
            conversation = db.query(Conversation).filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            ).first()
            
            if conversation:
                return conversation, False
            
            logger.warning(f"Conversation {conversation_id} non trouvée, création d'une nouvelle")
        
        # Créer une nouvelle conversation
        conversation = Conversation(
            user_id=user_id,
            title="Nouvelle conversation",
            is_archived=False
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"Nouvelle conversation créée: {conversation.id}")
        return conversation, True
    
    def get_user_conversations(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        include_archived: bool = False,
        db: Session = None
    ) -> tuple[List[ConversationSummary], int]:
        """
        Récupère les conversations d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            skip: Nombre d'éléments à sauter
            limit: Nombre maximum d'éléments
            include_archived: Inclure les conversations archivées
            db: Session DB
        
        Returns:
            Tuple (liste de conversations, total)
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            query = db.query(Conversation).filter(Conversation.user_id == user_id)
            
            if not include_archived:
                query = query.filter(Conversation.is_archived == False)
            
            total = query.count()
            
            conversations = query.order_by(
                desc(Conversation.updated_at)
            ).offset(skip).limit(limit).all()
            
            # Convertir en summaries avec message count
            summaries = []
            for conv in conversations:
                message_count = db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).count()
                
                # Récupérer le dernier message
                last_message = db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).order_by(desc(Message.created_at)).first()
                
                MAX_PREVIEW_LENGTH = 100
                last_preview = None
                if last_message:
                    content = last_message.content
                    last_preview = content[:MAX_PREVIEW_LENGTH - 3] + "..." if len(content) > 100 else content
                
                summaries.append(ConversationSummary(
                    id=conv.id,
                    title=conv.title or "Nouvelle conversation",
                    is_archived=conv.is_archived,
                    updated_at=conv.updated_at,
                    message_count=message_count,
                    last_message_preview=last_preview
                ))
            
            return summaries, total
        
        finally:
            if close_db:
                db.close()
    
    def get_conversation_with_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation avec ses messages.
        
        Args:
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur (vérification)
            db: Session DB
        
        Returns:
            Dict avec conversation et messages, None si non trouvé
        """
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        ).first()
        
        if not conversation:
            return None
        
        messages = db.query(Message).options(
                joinedload(Message.feedbacks)  # Charger la relation feedbacks
            ).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at).all()
        
        for message in messages:
            # Filtrer les feedbacks pour ne garder que celui de l'utilisateur actuel
            user_feedback = next(
                (f for f in message.feedbacks if f.user_id == user_id),
                None
            )
            # Ajouter l'attribut .feedback (singulier) sur le message
            # Pydantic avec from_attributes=True utilisera cet attribut
            message.feedback = user_feedback
        
        return {
            "conversation": ConversationResponse.model_validate(conversation),
            "messages": [MessageResponse.model_validate(m) for m in messages]
        }
    
    def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        db: Session
    ) -> bool:
        """
        Supprime une conversation.
        
        Args:
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur (vérification)
            db: Session DB
        
        Returns:
            True si supprimé, False sinon
        """
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        ).first()
        
        if not conversation:
            return False
        
        # Les messages et feedbacks seront supprimés en cascade
        db.delete(conversation)
        db.commit()
        
        logger.info(f"Conversation {conversation_id} supprimée")
        return True
    
    def archive_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        archive: bool,
        db: Session
    ) -> Optional[Conversation]:
        """
        Archive ou désarchive une conversation.
        
        Args:
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur
            archive: True pour archiver, False pour désarchiver
            db: Session DB
        
        Returns:
            Conversation mise à jour, None si non trouvée
        """
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        ).first()
        
        if not conversation:
            return None
        
        conversation.is_archived = archive
        conversation.archived_at = datetime.utcnow() if archive else None
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    # =========================================================================
    # GESTION DES MESSAGES
    # =========================================================================
    
    def _save_user_message(
        self,
        conversation_id: UUID,
        content: str,
        db: Session
    ) -> Message:
        """
        Sauvegarde un message utilisateur.
        
        Args:
            conversation_id: ID de la conversation
            content: Contenu du message
            db: Session DB
        
        Returns:
            Message créé
        """
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            cache_hit=False
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Mettre à jour updated_at de la conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
            db.commit()
        
        return message
    
    def _save_assistant_message(
        self,
        id: UUID,
        conversation_id: UUID,
        content: str,
        sources: List[Dict[str, Any]],
        token_count_input: int,
        token_count_output: int,
        cost_usd: float,
        cost_xaf: float,
        model_used: str,
        cache_hit: bool,
        response_time_seconds: float,
        db: Session,
        cache_key: Optional[str] = None
    ) -> Message:
        """
        Sauvegarde un message assistant.
        
        Args:
            id: ID du message
            conversation_id: ID de la conversation
            content: Contenu du message
            sources: Sources citées
            token_count_input: Tokens en entrée
            token_count_output: Tokens en sortie
            cost_usd: Coût USD
            cost_xaf: Coût XAF
            model_used: Modèle utilisé
            cache_hit: Si depuis le cache
            response_time_seconds: Temps de réponse
            db: Session DB
            cache_key: Clé du cache (optionnel)
        
        Returns:
            Message créé
        """
        message = Message(
            id=id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            sources=sources,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            token_count_total=token_count_input + token_count_output,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            model_used=model_used,
            cache_hit=cache_hit,
            cache_key=cache_key,
            response_time_seconds=response_time_seconds
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Mettre à jour updated_at de la conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
            db.commit()
        
        return message
    
    def _get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique de conversation.
        
        Args:
            conversation_id: ID de la conversation
            limit: Nombre de messages max
            db: Session DB
        
        Returns:
            Liste de messages formatés pour le prompt
        """
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit * 2).all()
        
        # Inverser pour avoir l'ordre chronologique
        messages = list(reversed(messages))
        
        # Prendre les derniers messages (alternance user/assistant)
        return [
            {
                "role": m.role.value,
                "content": m.content
            }
            for m in messages[-limit:]
        ]
    
    # =========================================================================
    # GESTION DES FEEDBACKS
    # =========================================================================
    
    def add_feedback(
        self,
        message_id: UUID,
        user_id: UUID,
        rating: str,
        comment: Optional[str],
        db: Session,
        user_name: Optional[str] = None  # SPRINT 14 - Nouveau paramètre
    ) -> Optional[Feedback]:
        """
        Ajoute un feedback sur un message.
        
        Args:
            message_id: ID du message
            user_id: ID de l'utilisateur
            rating: Type de feedback (THUMBS_UP/THUMBS_DOWN)
            comment: Commentaire optionnel
            db: Session DB
            user_name: Nom de l'utilisateur (pour notification)
        
        Returns:
            Feedback créé, None si message non trouvé
        """
        # Vérifier que le message existe et appartient à l'utilisateur
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return None
        
        # Vérifier que la conversation appartient à l'utilisateur
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == message.conversation_id,
                Conversation.user_id == user_id
            )
        ).first()
        
        if not conversation:
            return None
        
        # Vérifier si un feedback existe déjà
        existing = db.query(Feedback).filter(
            and_(
                Feedback.message_id == message_id,
                Feedback.user_id == user_id
            )
        ).first()
        
        is_new_feedback = existing is None
        
        if existing:
            # Mettre à jour le feedback existant
            existing.rating = FeedbackRating(rating)
            existing.comment = comment
            db.commit()
            db.refresh(existing)
            feedback = existing
        else:
            # Créer un nouveau feedback
            feedback = Feedback(
                user_id=user_id,
                conversation_id=conversation.id,
                message_id=message_id,
                rating=FeedbackRating(rating),
                comment=comment
            )
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
        
        logger.info(f"Feedback ajouté: message={message_id}, rating={rating}")
        
        # SPRINT 14 - Notification temps réel (seulement pour nouveaux feedbacks)
        if is_new_feedback and user_name:
            _send_notification_in_thread(
                "notify_feedback_received",
                feedback_id=feedback.id,
                message_id=message_id,
                user_name=user_name,
                rating=rating,
                comment=comment
            )
        
        return feedback
    # =========================================================================
    # UTILITAIRES
    # =========================================================================
    
    async def _embed_query(self, query: str) -> List[float]:
        """
        Génère l'embedding d'une question.
        
        Args:
            query: Question à embedder
        
        Returns:
            Vecteur embedding
        """
        result = self.mistral_client.embed_texts([query])
        return result.embeddings[0] if result.embeddings else []
    
    async def _generate_and_save_title(
        self,
        conversation: Conversation,
        query: str,
        db: Session
    ) -> None:
        """
        Génère et sauvegarde le titre d'une conversation.
        
        Args:
            conversation: Conversation à mettre à jour
            query: Question initiale
            db: Session DB
        """
        try:
            result = self.generator.generate_title_with_metrics(query)
            conversation.title = result.content
            db.commit()

            self._track_token_usage(
            operation_type=OperationType.TITLE_GENERATION,
            user_id=conversation.user_id,
            model_name=result.model_name,
            token_count_input=result.token_count_input,
            token_count_output=result.token_count_output,
            cost_usd=result.cost_usd,
            cost_xaf=result.cost_xaf,
            db=db,
            message_id=None  # Pas de message associé
            )
            
            logger.info(
                f"Titre généré pour conversation {conversation.id}: {conversation.title} "
                f"(tokens: {result.token_count_total}, cost: ${result.cost_usd})")
            
        except Exception as e:
            logger.error(f"Erreur génération titre: {e}")
            # Fallback : premiers mots de la question
            words = query.split()[:5]
            conversation.title = " ".join(words)[:50]
            db.commit()
    
    def _track_token_usage(
        self,
        user_id: UUID,
        message_id: UUID,
        operation_type: OperationType, 
        model_name: str,
        token_count_input: int,
        token_count_output: int,
        cost_usd: float,
        cost_xaf: float,
        db: Session, 
        document_id: Optional[UUID] = None
    ) -> None:
        """
        Enregistre l'utilisation des tokens.
        
        Args:
            user_id: ID de l'utilisateur
            message_id: ID du message
            operation_type=operation_type,
            model_name: Nom du modèle
            token_count_input: Tokens en entrée
            token_count_output: Tokens en sortie
            cost_usd: Coût USD
            cost_xaf: Coût XAF
            db: Session DB
        """
        """Enregistre l'utilisation des tokens."""
        # Récupérer le taux de change depuis la DB
        from app.services.exchange_rate_service import ExchangeRateService
        exchange_rate = ExchangeRateService.get_current_rate(db, "USD", "XAF")
        if exchange_rate is None:
            exchange_rate = 569.41080  # Fallback

        usage = TokenUsage(
            operation_type=operation_type,
            model_name=model_name,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            token_count_total=token_count_input + token_count_output,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            exchange_rate=float(exchange_rate),
            user_id=user_id,
            message_id=message_id,
            document_id=document_id 
        )
        db.add(usage)
        db.commit()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """
    Retourne une instance singleton du ChatService.
    
    Returns:
        Instance ChatService
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service