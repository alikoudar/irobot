# -*- coding: utf-8 -*-
"""
Service Dashboard - Sprint 10 Phase 1 - VERSION v1.3

CORRECTIFS v1.3 (2025-11-28) :
- Intégration ConfigService pour récupérer tarifs Mistral depuis system_configs
- Intégration ExchangeRateService pour récupérer taux USD→XAF
- Calcul correct des coûts cache économisés (cost_saved_usd et cost_saved_xaf)
- Tous les montants XAF arrondis à 2 décimales partout dans le code
- Logs ajoutés pour debugging des calculs de coûts

CORRECTIFS v1.2 :
- Tous les enums en MAJUSCULES (COMPLETED, PENDING, USER, ASSISTANT, etc.)
- Utilisation des enums du modèle quand possible

Fournit les statistiques et métriques pour le dashboard admin.

Auteur: IroBot Team
Date: 2025-11-28
Sprint: 10 - Phase 1 - Correctif v1.3
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from app.models.cache_statistics import CacheStatistics
from app.models.chunk import Chunk
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.feedback import Feedback, FeedbackRating
from app.models.message import Message, MessageRole
from app.models.token_usage import TokenUsage
from app.models.user import User

# ✅ NOUVEAUX IMPORTS v1.3
from app.services.config_service import get_config_service
from app.services.exchange_rate_service import ExchangeRateService

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service pour les statistiques et métriques du dashboard admin.
    
    Méthodes principales :
    - get_overview_stats : Vue d'ensemble complète
    - get_cache_statistics : Statistiques du cache (v1.3: calcul coûts corrects)
    - get_token_usage_stats : Usage des tokens par opération
    - get_top_documents : Top N documents les plus consultés
    - get_activity_timeline : Timeline d'activité journalière
    - get_user_activity_stats : Statistiques d'activité par utilisateur
    - get_feedback_statistics : Statistiques feedbacks (méthode interne)
    """
    
    @staticmethod
    def get_feedback_statistics(
        db: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Calcule les statistiques de feedback.
        
        Args:
            db: Session SQLAlchemy
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Dict avec total_feedbacks, thumbs_up, thumbs_down, satisfaction_rate, etc.
        """
        # Récupérer tous les feedbacks dans la période
        feedbacks = db.query(Feedback).filter(
            Feedback.created_at >= start_date,
            Feedback.created_at <= end_date
        ).all()
        
        total_feedbacks = len(feedbacks)
        # CORRECTIF v1.2: Utilisation de FeedbackRating.THUMBS_UP (enum en MAJUSCULES)
        thumbs_up = sum(1 for f in feedbacks if f.rating == FeedbackRating.THUMBS_UP)
        thumbs_down = sum(1 for f in feedbacks if f.rating == FeedbackRating.THUMBS_DOWN)
        with_comments = sum(1 for f in feedbacks if f.comment and f.comment.strip())
        
        # Calcul taux de satisfaction
        satisfaction_rate = (thumbs_up / total_feedbacks * 100) if total_feedbacks > 0 else 0.0
        
        # Nombre total de messages assistant (pour calcul feedback_rate)
        # CORRECTIF v1.2: MessageRole.ASSISTANT (enum en MAJUSCULES)
        total_messages = db.query(Message).filter(
            Message.role == MessageRole.ASSISTANT,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        # Calcul taux de feedback
        feedback_rate = (total_feedbacks / total_messages * 100) if total_messages > 0 else 0.0
        
        return {
            "total_feedbacks": total_feedbacks,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "with_comments": with_comments,
            "satisfaction_rate": round(satisfaction_rate, 2),
            "feedback_rate": round(feedback_rate, 2),
            "total_messages": total_messages
        }
    
    @staticmethod
    def get_overview_stats(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Récupère les statistiques overview du dashboard.
        
        Args:
            db: Session SQLAlchemy
            start_date: Date de début (par défaut 30 jours avant)
            end_date: Date de fin (par défaut maintenant)
            
        Returns:
            Dict avec clés : users, documents, conversations, messages, 
                           cache, tokens, feedbacks, date_range
        """
        # Dates par défaut
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        logger.info(f"Récupération stats overview de {start_date} à {end_date}")
        
        # ========== USERS STATS ==========
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        new_users = db.query(User).filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        ).count()
        
        # ========== DOCUMENTS STATS ==========
        total_documents = db.query(Document).count()
        
        # CORRECTIF v1.2: Utilisation de DocumentStatus (enum en MAJUSCULES)
        completed_documents = db.query(Document).filter(
            Document.status == DocumentStatus.COMPLETED
        ).count()
        
        processing_documents = db.query(Document).filter(
            Document.status.in_([DocumentStatus.PENDING, DocumentStatus.PROCESSING])
        ).count()
        
        failed_documents = db.query(Document).filter(
            Document.status == DocumentStatus.FAILED
        ).count()
        
        # Total chunks
        total_chunks = db.query(Chunk).count()
        
        # ========== CONVERSATIONS STATS ==========
        total_conversations = db.query(Conversation).filter(
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date
        ).count()
        
        # ========== MESSAGES STATS ==========
        total_messages = db.query(Message).filter(
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        # CORRECTIF v1.2: MessageRole.USER et MessageRole.ASSISTANT (enums en MAJUSCULES)
        user_messages = db.query(Message).filter(
            Message.role == MessageRole.USER,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        assistant_messages = db.query(Message).filter(
            Message.role == MessageRole.ASSISTANT,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        # ========== CACHE STATS ==========
        cache_stats = DashboardService.get_cache_statistics(db, start_date, end_date)
        
        # ========== TOKEN USAGE ==========
        token_stats = DashboardService.get_token_usage_stats(db, start_date, end_date)
        
        # ========== FEEDBACKS (calcul direct) ==========
        feedback_stats = DashboardService.get_feedback_statistics(db, start_date, end_date)
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "new": new_users,
                "inactive": total_users - active_users
            },
            "documents": {
                "total": total_documents,
                "completed": completed_documents,
                "processing": processing_documents,
                "failed": failed_documents,
                "total_chunks": total_chunks
            },
            "conversations": {
                "total": total_conversations
            },
            "messages": {
                "total": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages
            },
            "cache": cache_stats,
            "tokens": token_stats,
            "feedbacks": feedback_stats,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    @staticmethod
    def get_cache_statistics(
        db: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Récupère les statistiques du cache.
        
        CORRECTIF v1.3:
        - Récupération tarifs Mistral depuis system_configs (via ConfigService)
        - Récupération exchange_rate depuis la base (via ExchangeRateService)
        - Calcul correct de cost_saved_usd et cost_saved_xaf
        - Tous les montants XAF arrondis à 2 décimales
        
        Args:
            db: Session SQLAlchemy
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Dict avec total_requests, cache_hits, cache_misses, hit_rate,
                      tokens_saved, cost_saved_usd, cost_saved_xaf
        """
        # CORRECTIF v1.2: MessageRole.ASSISTANT (enum en MAJUSCULES)
        # Total des requêtes (messages assistant)
        total_messages = db.query(Message).filter(
            Message.role == MessageRole.ASSISTANT,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        # Cache hits
        cache_hits = db.query(Message).filter(
            Message.role == MessageRole.ASSISTANT,
            Message.cache_hit == True,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).count()
        
        cache_misses = total_messages - cache_hits
        hit_rate = (cache_hits / total_messages * 100) if total_messages > 0 else 0
        
        # ✅ NOUVEAUTÉ v1.3 : Calcul correct des coûts cache économisés
        
        # 1. Récupérer les messages en cache avec leurs tokens
        cached_messages = db.query(Message).filter(
            Message.cache_hit == True,
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).all()
        
        tokens_saved = sum(msg.token_count_output or 0 for msg in cached_messages)
        
        logger.info(f"💾 Cache stats: {cache_hits} hits, {tokens_saved} tokens économisés")
        
        # 2. Récupérer les tarifs Mistral depuis system_configs
        config_service = get_config_service()
        
        # Les tokens économisés sont principalement des tokens LLM (génération)
        # On utilise donc les tarifs de mistral.pricing.medium
        pricing = config_service.get_pricing("medium", db)
        
        # Prix par million de tokens OUTPUT (car le cache économise des tokens de génération)
        price_per_million_output = pricing.get("price_per_million_output", 2.0)
        
        logger.debug(f"💰 Tarif Mistral medium output: ${price_per_million_output} / 1M tokens")
        
        # 3. Récupérer le taux de change USD → XAF
        exchange_rate = ExchangeRateService.get_rate_for_calculation(db)
        
        logger.debug(f"💱 Taux de change USD→XAF: {exchange_rate}")
        
        # 4. Calculer les coûts économisés
        # Formule: cost_usd = (tokens / 1_000_000) * price_per_million
        cost_saved_usd = (tokens_saved / 1_000_000) * price_per_million_output
        
        # Conversion en XAF
        cost_saved_xaf = cost_saved_usd * exchange_rate
        
        logger.info(
            f"✅ Cache savings: ${cost_saved_usd:.4f} USD = "
            f"{cost_saved_xaf:.2f} FCFA ({tokens_saved} tokens)"
        )
        
        # ✅ CORRECTIF v1.3: Tous les montants XAF arrondis à 2 décimales
        return {
            "total_requests": total_messages,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "hit_rate": round(hit_rate, 2),
            "tokens_saved": tokens_saved,
            "cost_saved_usd": round(cost_saved_usd, 4),  # USD: 4 décimales
            "cost_saved_xaf": round(cost_saved_xaf, 2)   # XAF: 2 décimales ✅
        }
    
    @staticmethod
    def get_token_usage_stats(
        db: Session,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Récupère les statistiques d'usage des tokens par type d'opération.
        
        CORRECTIF v1.3: Tous les montants XAF arrondis à 2 décimales
        
        Args:
            db: Session SQLAlchemy
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Dict avec stats par operation_type (embedding, reranking, 
                 title_generation, response_generation) + totaux
        """
        stats = {}
        
        # Stats par opération
        for operation in ["EMBEDDING", "RERANKING", "TITLE_GENERATION", "RESPONSE_GENERATION"]:
            records = db.query(TokenUsage).filter(
                TokenUsage.operation_type == operation,
                TokenUsage.created_at >= start_date,
                TokenUsage.created_at <= end_date
            ).all()
            
            total_tokens = sum(r.token_count_total for r in records)
            total_cost_usd = sum(float(r.cost_usd) for r in records)
            total_cost_xaf = sum(float(r.cost_xaf) for r in records)
            
            stats[operation] = {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost_usd, 4),  # USD: 4 décimales
                "total_cost_xaf": round(total_cost_xaf, 2),  # XAF: 2 décimales ✅
                "count": len(records)
            }
        
        # Grand total
        all_records = db.query(TokenUsage).filter(
            TokenUsage.created_at >= start_date,
            TokenUsage.created_at <= end_date
        ).all()
        
        stats["total"] = {
            "total_tokens": sum(r.token_count_total for r in all_records),
            "total_cost_usd": round(sum(float(r.cost_usd) for r in all_records), 4),  # USD: 4 décimales
            "total_cost_xaf": round(sum(float(r.cost_xaf) for r in all_records), 2)   # XAF: 2 décimales ✅
        }
        
        return stats
    
    @staticmethod
    def get_top_documents(
        db: Session,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Récupère les top N documents les plus consultés.
        
        Calcule le nombre de fois qu'un document a été utilisé comme source
        dans les réponses générées.
        
        Args:
            db: Session SQLAlchemy
            limit: Nombre de documents à retourner
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            
        Returns:
            Liste de dicts avec document_id, title, category, usage_count, total_chunks
        """
        # CORRECTIF v1.2: MessageRole.ASSISTANT (enum en MAJUSCULES)
        # Stratégie simplifiée : compter les chunks par document
        query = db.query(
            Chunk.document_id,
            func.count(Chunk.id).label('usage_count')
        ).join(
            Message,
            and_(
                Message.sources.isnot(None),
                Message.role == MessageRole.ASSISTANT
            )
        )
        
        if start_date:
            query = query.filter(Message.created_at >= start_date)
        if end_date:
            query = query.filter(Message.created_at <= end_date)
        
        results = query.group_by(
            Chunk.document_id
        ).order_by(
            func.count(Chunk.id).desc()
        ).limit(limit).all()
        
        # Enrichir avec les détails des documents
        top_docs = []
        for doc_id, usage_count in results:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                top_docs.append({
                    "document_id": str(document.id),
                    "title": document.original_filename,
                    "category": document.category.name if document.category else None,
                    "usage_count": usage_count,
                    "total_chunks": document.total_chunks or 0
                })
        
        return top_docs
    
    @staticmethod
    def get_activity_timeline(
        db: Session,
        days: int = 30
    ) -> List[Dict]:
        """
        Récupère la timeline d'activité journalière.
        
        Args:
            db: Session SQLAlchemy
            days: Nombre de jours à analyser
            
        Returns:
            Liste de dicts avec date, messages, documents (par jour)
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Messages par jour
        messages_per_day = db.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('count')
        ).filter(
            Message.created_at >= start_date
        ).group_by(
            func.date(Message.created_at)
        ).order_by(
            func.date(Message.created_at)
        ).all()
        
        # CORRECTIF v1.2: DocumentStatus.COMPLETED (enum en MAJUSCULES)
        # Documents traités par jour
        docs_per_day = db.query(
            func.date(Document.processed_at).label('date'),
            func.count(Document.id).label('count')
        ).filter(
            Document.processed_at >= start_date,
            Document.status == DocumentStatus.COMPLETED
        ).group_by(
            func.date(Document.processed_at)
        ).order_by(
            func.date(Document.processed_at)
        ).all()
        
        # Fusionner les données
        timeline = {}
        for date, count in messages_per_day:
            date_str = date.isoformat()
            timeline[date_str] = {
                "date": date_str, 
                "messages": count, 
                "documents": 0
            }
        
        for date, count in docs_per_day:
            date_str = date.isoformat()
            if date_str in timeline:
                timeline[date_str]["documents"] = count
            else:
                timeline[date_str] = {
                    "date": date_str, 
                    "messages": 0, 
                    "documents": count
                }
        
        return sorted(timeline.values(), key=lambda x: x["date"])
    
    @staticmethod
    def get_user_activity_stats(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        limit: int = 20
    ) -> List[Dict]:
        """
        Récupère les statistiques d'activité par utilisateur.
        
        Args:
            db: Session SQLAlchemy
            start_date: Date de début
            end_date: Date de fin
            limit: Nombre d'utilisateurs à retourner
            
        Returns:
            Liste de dicts avec user_id, matricule, name, message_count
        """
        # CORRECTIF v1.2: MessageRole.USER (enum en MAJUSCULES)
        results = db.query(
            User.id,
            User.matricule,
            User.nom,
            User.prenom,
            func.count(Message.id).label('message_count')
        ).join(
            Conversation, Conversation.user_id == User.id
        ).join(
            Message, Message.conversation_id == Conversation.id
        ).filter(
            Message.created_at >= start_date,
            Message.created_at <= end_date,
            Message.role == MessageRole.USER
        ).group_by(
            User.id
        ).order_by(
            func.count(Message.id).desc()
        ).limit(limit).all()
        
        return [
            {
                "user_id": str(r.id),
                "matricule": r.matricule,
                "name": f"{r.prenom} {r.nom}",
                "message_count": r.message_count
            }
            for r in results
        ]