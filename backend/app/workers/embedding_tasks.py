"""
Worker Celery pour l'embedding des chunks avec Mistral.

Ce worker :
1. Charge les chunks d'un document depuis la DB
2. Génère les embeddings par batches (depuis config DB)
3. Calcule et enregistre les coûts (tarifs depuis config DB, taux depuis exchange_rates)
4. Met à jour les chunks avec les infos d'embedding
5. Envoie le document à la queue d'indexation

MODIFICATION: Utilise ConfigService pour les tarifs et paramètres.
"""
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
from copy import deepcopy

from celery import Task
from sqlalchemy.orm.attributes import flag_modified

from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# TASK BASE CLASS
# =============================================================================

class EmbeddingTask(Task):
    """Classe de base pour les tâches d'embedding."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Gestion des échecs de tâche."""
        logger.error(f"Embedding task {task_id} failed: {exc}")
        document_id = args[0] if args else kwargs.get('document_id')
        if document_id:
            self._update_document_status_failed(document_id, str(exc))
    
    def _update_document_status_failed(self, document_id: str, error_message: str):
        """Met à jour le status du document en cas d'échec."""
        db = SessionLocal()
        try:
            from app.models.document import Document, DocumentStatus, ProcessingStage
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_stage = ProcessingStage.EMBEDDING
                document.error_message = error_message[:1000]
                db.commit()
        except Exception as e:
            logger.error(f"Échec mise à jour status document: {e}")
            db.rollback()
        finally:
            db.close()


# =============================================================================
# MAIN EMBEDDING TASK
# =============================================================================

@celery_app.task(
    base=EmbeddingTask,
    bind=True,
    name="app.workers.embedding_tasks.embed_chunks",
    queue="embedding",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300
)
def embed_chunks(self, document_id: str) -> Dict[str, Any]:
    """
    Génère les embeddings pour tous les chunks d'un document.
    
    Les paramètres (batch_size, modèle, tarifs) sont lus depuis la DB.
    Le taux de change est lu depuis la table exchange_rates.
    
    Args:
        document_id: UUID du document
        
    Returns:
        Dict avec statistiques de l'embedding
    """
    # Imports à l'intérieur pour éviter les imports circulaires
    from app.models.document import Document, DocumentStatus, ProcessingStage
    from app.models.chunk import Chunk
    from app.models.token_usage import TokenUsage, OperationType
    from app.clients.mistral_client import (
        get_mistral_client, 
        get_embedding_model,
        get_embedding_batch_size,
        get_pricing
    )
    from app.services.exchange_rate_service import ExchangeRateService
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        # =================================================================
        # 0. CHARGER LES CONFIGURATIONS DEPUIS LA DB
        # =================================================================
        
        embedding_model = get_embedding_model()
        batch_size = get_embedding_batch_size()
        pricing = get_pricing("embed")
        
        logger.info(
            f"Config chargée - Modèle: {embedding_model}, "
            f"Batch: {batch_size}, Prix: ${pricing.get('price_per_million_input', 0.1)}/M"
        )
        
        # =================================================================
        # 1. CHARGER LE DOCUMENT ET SES CHUNKS
        # =================================================================
        
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} non trouvé")
        
        # Mettre à jour le status
        document.status = DocumentStatus.PROCESSING
        document.processing_stage = ProcessingStage.EMBEDDING
        db.commit()
        
        # Charger les chunks
        chunks = db.query(Chunk).filter(
            Chunk.document_id == document.id
        ).order_by(Chunk.chunk_index).all()
        
        if not chunks:
            raise ValueError(f"Aucun chunk trouvé pour le document {document_id}")
        
        logger.info(f"Embedding document {document_id}: {len(chunks)} chunks")
        
        # =================================================================
        # 2. GÉNÉRER LES EMBEDDINGS PAR BATCHES
        # =================================================================
        
        mistral_client = get_mistral_client()
        
        total_tokens = 0
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        embeddings_map: Dict[str, List[float]] = {}
        
        for batch_num, i in enumerate(range(0, len(chunks), batch_size), 1):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]
            
            logger.info(
                f"Document {document_id}: Batch {batch_num}/{total_batches} "
                f"({len(batch_texts)} chunks)"
            )
            
            # Appel API Mistral avec le modèle de la config
            result = mistral_client.embed_texts(batch_texts, model=embedding_model)
            
            # Mapper les embeddings aux chunks
            for chunk, embedding in zip(batch_chunks, result.embeddings):
                embeddings_map[str(chunk.id)] = embedding
            
            total_tokens += result.token_count
        
        # =================================================================
        # 3. CALCULER ET ENREGISTRER LES COÛTS (depuis config DB)
        # =================================================================
        
        # Récupérer le taux de change depuis la DB
        exchange_rate = ExchangeRateService.get_rate_for_calculation(db)
        
        # Récupérer le tarif depuis la config DB
        price_per_million = pricing.get("price_per_million_input", 0.1)
        
        # Calculer le coût
        cost_usd = (total_tokens / 1_000_000) * price_per_million
        cost_xaf = cost_usd * exchange_rate
        
        logger.info(
            f"Coûts calculés - Tokens: {total_tokens}, "
            f"Prix: ${price_per_million}/M, Taux: {exchange_rate} XAF/USD, "
            f"Coût: ${cost_usd:.6f} USD = {cost_xaf:.2f} XAF"
        )
        
        # Enregistrer dans TokenUsage
        token_usage = TokenUsage(
            operation_type=OperationType.EMBEDDING,
            model_name=embedding_model,
            token_count_input=total_tokens,
            token_count_output=0,
            token_count_total=total_tokens,
            cost_usd=cost_usd,
            cost_xaf=cost_xaf,
            exchange_rate=exchange_rate,
            document_id=document.id,
            token_metadata={
                "chunks_count": len(chunks),
                "batches_count": total_batches,
                "avg_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0,
                "price_per_million_used": price_per_million,
                "exchange_rate_used": exchange_rate,
            }
        )
        db.add(token_usage)
        
        # =================================================================
        # 4. METTRE À JOUR LES CHUNKS AVEC LES EMBEDDINGS
        # =================================================================
        
        embedding_time = time.time() - start_time
        chunks_updated = 0
        
        for chunk in chunks:
            chunk.embedding_model = embedding_model
            chunk.embedding_time_seconds = embedding_time / len(chunks)
            
            # Utiliser deepcopy et flag_modified pour JSONB
            chunk_metadata = deepcopy(chunk.chunk_metadata) if chunk.chunk_metadata else {}
            embedding = embeddings_map.get(str(chunk.id))
            
            if embedding:
                chunk_metadata["embedding"] = embedding
                chunk.chunk_metadata = chunk_metadata
                flag_modified(chunk, "chunk_metadata")
                chunks_updated += 1
            else:
                logger.warning(f"Pas d'embedding trouvé pour chunk {chunk.id}")
        
        # Mettre à jour le document
        document.embedding_time_seconds = embedding_time
        
        # Mettre à jour les métadonnées du document
        doc_metadata = deepcopy(document.document_metadata) if document.document_metadata else {}
        doc_metadata["embedding_stats"] = {
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "cost_xaf": cost_xaf,
            "model": embedding_model,
            "batches": total_batches,
            "time_seconds": embedding_time,
            "chunks_updated": chunks_updated,
            "price_per_million": price_per_million,
            "exchange_rate": exchange_rate,
        }
        document.document_metadata = doc_metadata
        flag_modified(document, "document_metadata")
        
        db.commit()
        
        logger.info(
            f"Embedding terminé pour document {document_id}: "
            f"{chunks_updated}/{len(chunks)} chunks, {total_tokens} tokens, "
            f"${cost_usd:.6f} USD ({cost_xaf:.2f} XAF), {embedding_time:.2f}s"
        )
        
        # =================================================================
        # 5. ENVOYER À LA QUEUE D'INDEXATION
        # =================================================================
        
        from app.workers.indexing_tasks import index_to_weaviate
        index_to_weaviate.delay(str(document_id))
        
        logger.info(f"Document {document_id} envoyé à la queue indexing")
        
        return {
            "document_id": str(document_id),
            "status": "success",
            "chunks_embedded": len(chunks),
            "chunks_updated": chunks_updated,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "cost_xaf": cost_xaf,
            "exchange_rate": exchange_rate,
            "price_per_million": price_per_million,
            "model": embedding_model,
            "processing_time_seconds": embedding_time,
            "next_stage": "indexing"
        }
        
    except Exception as e:
        logger.error(f"Erreur embedding document {document_id}: {e}")
        
        try:
            from app.models.document import Document, DocumentStatus, ProcessingStage
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_stage = ProcessingStage.EMBEDDING
                document.error_message = str(e)[:1000]
                document.retry_count = (document.retry_count or 0) + 1
                db.commit()
        except Exception:
            db.rollback()
        
        raise
        
    finally:
        db.close()