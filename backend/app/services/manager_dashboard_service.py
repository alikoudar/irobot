# app/services/manager_dashboard_service.py
"""
Service pour le dashboard manager.
Fournit des statistiques sur les documents uploadés par le manager SANS affichage des coûts.
Version simplifiée du DashboardService admin.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID
import logging

from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.message import Message
from app.models.conversation import Conversation
from app.models.category import Category

logger = logging.getLogger(__name__)


class ManagerDashboardService:
    """Service pour le dashboard manager (sans affichage des coûts)."""
    
    @staticmethod
    def get_manager_stats(
        db: Session,
        manager_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Récupère les statistiques du dashboard manager.
        
        Args:
            db: Session de base de données
            manager_id: UUID du manager
            start_date: Date de début (optionnel, défaut: 30 jours avant)
            end_date: Date de fin (optionnel, défaut: maintenant)
            
        Returns:
            Dictionnaire avec les statistiques (sans coûts)
        """
        try:
            # Date range par défaut : 30 derniers jours
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            logger.info(f"📊 Récupération stats manager {manager_id} du {start_date} au {end_date}")
            
            # Documents uploadés par le manager
            documents_query = db.query(Document).filter(
                Document.uploaded_by == manager_id
            )
            
            total_documents = documents_query.count()
            completed_documents = documents_query.filter(
                Document.status == "COMPLETED"
            ).count()
            processing_documents = documents_query.filter(
                Document.status.in_(["PENDING", "PROCESSING"])
            ).count()
            failed_documents = documents_query.filter(
                Document.status == "FAILED"
            ).count()
            
            # Total chunks des documents du manager
            total_chunks = db.query(Chunk).join(Document).filter(
                Document.uploaded_by == manager_id
            ).count()
            
            # Messages utilisant les documents du manager (période filtrée)
            manager_doc_ids = [doc.id for doc in documents_query.all()]
            
            messages_count = 0
            if manager_doc_ids:
                # Compter les messages qui ont référencé des chunks des docs du manager
                # Pour simplifier, on compte les messages assistant dans la période
                # qui ont des sources (dans un vrai système, il faudrait parser les sources)
                messages_count = db.query(Message).filter(
                    Message.role == "ASSISTANT",
                    Message.created_at >= start_date,
                    Message.created_at <= end_date,
                    Message.sources.isnot(None)
                ).count()
            
            # Documents par catégorie (tous les documents du manager, pas de filtre temporel)
            docs_by_category = db.query(
                Category.name,
                func.count(Document.id).label('count')
            ).join(Document).filter(
                Document.uploaded_by == manager_id
            ).group_by(Category.name).all()
            
            logger.info(f"✅ Stats manager récupérées: {total_documents} docs, {messages_count} messages")
            
            return {
                "documents": {
                    "total": total_documents,
                    "completed": completed_documents,
                    "processing": processing_documents,
                    "failed": failed_documents,
                    "total_chunks": total_chunks
                },
                "messages": {
                    "total": messages_count
                },
                "documents_by_category": [
                    {"category": name, "count": count}
                    for name, count in docs_by_category
                ],
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats manager: {str(e)}")
            raise
    
    @staticmethod
    def get_manager_top_documents(
        db: Session,
        manager_id: UUID,
        limit: int = 10
    ) -> List[Dict]:
        """
        Récupère les top documents du manager les plus utilisés.
        
        Args:
            db: Session de base de données
            manager_id: UUID du manager
            limit: Nombre maximum de documents à retourner (défaut: 10)
            
        Returns:
            Liste des documents avec leur usage_count (nombre réel d'utilisations dans les messages)
        """
        try:
            logger.info(f"🔝 Récupération top {limit} documents du manager {manager_id}")
            
            # Récupérer tous les documents complétés du manager
            documents = db.query(Document).filter(
                Document.uploaded_by == manager_id,
                Document.status == "COMPLETED"
            ).all()
            
            if not documents:
                logger.info("📭 Aucun document complété trouvé pour ce manager")
                return []
            
            # Créer un set des document IDs du manager pour filtrage rapide
            manager_doc_ids = {str(doc.id) for doc in documents}
            
            # Construire le mapping document_id -> usage_count
            document_usage = {}
            
            # Récupérer tous les messages avec sources
            messages_with_sources = db.query(Message).filter(
                Message.sources.isnot(None),
                Message.role == "ASSISTANT"
            ).all()
            
            logger.info(f"📊 Analyse de {len(messages_with_sources)} messages avec sources")
            
            # Parser toutes les sources et compter les utilisations
            # ✅ CORRECTIF v3.0: Compter 1 fois par message, pas par chunk
            for message in messages_with_sources:
                if message.sources:
                    # Extraire les document_id UNIQUES du manager dans ce message
                    doc_ids_in_message = set()
                    for source in message.sources:
                        if isinstance(source, dict):
                            doc_id = source.get("document_id")
                            # Ne compter que les documents du manager
                            if doc_id and doc_id in manager_doc_ids:
                                doc_ids_in_message.add(doc_id)
                    
                    # Incrémenter 1 fois par document unique utilisé dans le message
                    for doc_id in doc_ids_in_message:
                        document_usage[doc_id] = document_usage.get(doc_id, 0) + 1
            
            logger.info(f"✅ {len(document_usage)} documents du manager utilisés dans les messages")
            
            # Trier par usage_count décroissant
            sorted_docs = sorted(document_usage.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            # Enrichir avec les détails des documents
            doc_stats = []
            for doc_id, usage_count in sorted_docs:
                # Trouver le document dans notre liste
                document = next((d for d in documents if str(d.id) == doc_id), None)
                if document:
                    doc_stats.append({
                        "document_id": str(document.id),
                        "title": document.original_filename,
                        "category": document.category.name if document.category else None,
                        "usage_count": usage_count,
                        "total_chunks": document.total_chunks or 0,
                        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None
                    })
            
            # Ajouter les documents avec 0 utilisations si on n'a pas encore le limit
            if len(doc_stats) < limit:
                for doc in documents:
                    if str(doc.id) not in document_usage:
                        doc_stats.append({
                            "document_id": str(doc.id),
                            "title": doc.original_filename,
                            "category": doc.category.name if doc.category else None,
                            "usage_count": 0,
                            "total_chunks": doc.total_chunks or 0,
                            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
                        })
                        if len(doc_stats) >= limit:
                            break
            
            logger.info(f"✅ Top documents calculés: {len(doc_stats)} documents retournés")
            
            return doc_stats
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération top documents manager: {str(e)}")
            raise
    
    @staticmethod
    def get_manager_documents_timeline(
        db: Session,
        manager_id: UUID,
        days: int = 30
    ) -> List[Dict]:
        """
        Récupère la timeline des documents uploadés par le manager.
        
        Args:
            db: Session de base de données
            manager_id: UUID du manager
            days: Nombre de jours à inclure (défaut: 30)
            
        Returns:
            Liste des documents par jour
        """
        try:
            logger.info(f"📅 Récupération timeline documents manager {manager_id} sur {days} jours")
            
            start_date = datetime.utcnow() - timedelta(days=days)
            end_date = datetime.utcnow()
            
            # Grouper les documents par jour
            timeline = db.query(
                func.date(Document.uploaded_at).label('date'),
                func.count(Document.id).label('count')
            ).filter(
                Document.uploaded_by == manager_id,
                Document.uploaded_at >= start_date,
                Document.uploaded_at <= end_date
            ).group_by(
                func.date(Document.uploaded_at)
            ).order_by(
                func.date(Document.uploaded_at)
            ).all()
            
            result = [
                {
                    "date": date.isoformat() if date else None,
                    "documents_count": count
                }
                for date, count in timeline
            ]
            
            logger.info(f"✅ Timeline récupérée: {len(result)} jours avec activité")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération timeline documents: {str(e)}")
            raise