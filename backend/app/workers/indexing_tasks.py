"""
Worker Celery pour l'indexation des chunks dans Weaviate.

Ce worker :
1. Charge les chunks avec leurs embeddings depuis la DB
2. Prépare les objets pour Weaviate avec métadonnées
3. Insère en batch dans Weaviate
4. Met à jour les weaviate_id des chunks
5. Met à jour le document: status=COMPLETED
"""
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from celery import Task

from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Taille des batches pour l'indexation Weaviate
WEAVIATE_BATCH_SIZE = 100


# =============================================================================
# TASK BASE CLASS
# =============================================================================

class IndexingTask(Task):
    """Classe de base pour les tâches d'indexation."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Gestion des échecs de tâche."""
        logger.error(f"Indexing task {task_id} failed: {exc}")
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
                document.processing_stage = ProcessingStage.INDEXING
                document.error_message = error_message[:1000]
                db.commit()
        except Exception as e:
            logger.error(f"Échec mise à jour status document: {e}")
            db.rollback()
        finally:
            db.close()


# =============================================================================
# MAIN INDEXING TASK
# =============================================================================

@celery_app.task(
    base=IndexingTask,
    bind=True,
    name="app.workers.indexing_tasks.index_to_weaviate",
    queue="indexing",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300
)
def index_to_weaviate(self, document_id: str) -> Dict[str, Any]:
    """
    Indexe tous les chunks d'un document dans Weaviate.
    
    Étapes :
    1. Charger les chunks avec leurs embeddings
    2. Récupérer les métadonnées du document (catégorie, titre, etc.)
    3. Préparer les objets Weaviate
    4. Insérer en batch
    5. Mettre à jour les weaviate_id des chunks
    6. Marquer le document comme COMPLETED
    
    Args:
        document_id: UUID du document
        
    Returns:
        Dict avec statistiques de l'indexation
    """
    # Imports à l'intérieur de la fonction pour éviter les erreurs au chargement du module
    from app.models.document import Document, DocumentStatus, ProcessingStage
    from app.models.chunk import Chunk
    from app.models.category import Category
    from app.clients.weaviate_client import get_weaviate_client
    
    db = SessionLocal()
    start_time = time.time()
    weaviate_client = None
    
    try:
        # =================================================================
        # 1. CHARGER LE DOCUMENT ET SES CHUNKS
        # =================================================================
        
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} non trouvé")
        
        # Mettre à jour le status
        document.status = DocumentStatus.PROCESSING
        document.processing_stage = ProcessingStage.INDEXING
        db.commit()
        
        # Charger les chunks
        chunks = db.query(Chunk).filter(
            Chunk.document_id == document.id
        ).order_by(Chunk.chunk_index).all()
        
        if not chunks:
            raise ValueError(f"Aucun chunk trouvé pour le document {document_id}")
        
        logger.info(f"Indexation document {document_id}: {len(chunks)} chunks")
        
        # =================================================================
        # 2. RÉCUPÉRER LES MÉTADONNÉES
        # =================================================================
        
        # Catégorie
        category_name = ""
        if document.category_id:
            category = db.query(Category).filter(Category.id == document.category_id).first()
            if category:
                category_name = category.name
        
        # Titre du document (depuis métadonnées ou filename)
        doc_metadata = document.document_metadata or {}
        document_title = doc_metadata.get("document_title", document.original_filename)
        
        # =================================================================
        # 3. PRÉPARER LES OBJETS WEAVIATE
        # =================================================================
        
        chunks_data = []
        missing_embeddings = 0
        
        for chunk in chunks:
            # Récupérer l'embedding depuis les métadonnées du chunk
            chunk_metadata = chunk.chunk_metadata or {}
            embedding = chunk_metadata.get("embedding")
            
            if not embedding:
                logger.warning(f"Chunk {chunk.id} sans embedding, skip")
                missing_embeddings += 1
                continue
            
            chunks_data.append({
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "vector": embedding,
                "document_id": str(document.id),
                "chunk_index": chunk.chunk_index,
                "document_title": document_title,
                "category_name": category_name,
                "page_number": chunk.page_number,
                "filename": document.original_filename,
                "file_type": document.file_extension,
            })
        
        if not chunks_data:
            raise ValueError(f"Aucun chunk avec embedding pour le document {document_id}")
        
        if missing_embeddings > 0:
            logger.warning(
                f"Document {document_id}: {missing_embeddings} chunks sans embedding"
            )
        
        # =================================================================
        # 4. INSÉRER DANS WEAVIATE
        # =================================================================
        
        weaviate_client = get_weaviate_client()
        
        # S'assurer que la collection existe
        if not weaviate_client.collection_exists():
            weaviate_client.create_collection()
        
        # Supprimer les anciens chunks du document (si re-indexation)
        deleted_count = weaviate_client.delete_document_chunks(str(document_id))
        if deleted_count > 0:
            logger.info(f"Supprimé {deleted_count} anciens chunks de Weaviate")
        
        # Indexer par batches
        total_indexed = 0
        total_errors = 0
        all_weaviate_ids = []
        
        for i in range(0, len(chunks_data), WEAVIATE_BATCH_SIZE):
            batch = chunks_data[i:i + WEAVIATE_BATCH_SIZE]
            batch_num = (i // WEAVIATE_BATCH_SIZE) + 1
            total_batches = (len(chunks_data) + WEAVIATE_BATCH_SIZE - 1) // WEAVIATE_BATCH_SIZE
            
            logger.info(
                f"Document {document_id}: Indexation batch {batch_num}/{total_batches} "
                f"({len(batch)} chunks)"
            )
            
            result = weaviate_client.batch_insert(batch)
            
            total_indexed += result.success_count
            total_errors += result.error_count
            all_weaviate_ids.extend(result.weaviate_ids)
        
        # =================================================================
        # 5. METTRE À JOUR LES CHUNKS EN DB
        # =================================================================
        
        # Mapper les weaviate_ids aux chunks
        chunk_id_to_weaviate_id = {}
        for idx, chunk_data in enumerate(chunks_data):
            if idx < len(all_weaviate_ids):
                chunk_id_to_weaviate_id[chunk_data["chunk_id"]] = all_weaviate_ids[idx]
        
        for chunk in chunks:
            weaviate_id = chunk_id_to_weaviate_id.get(str(chunk.id))
            if weaviate_id:
                chunk.weaviate_id = weaviate_id
                chunk.indexed_at = datetime.utcnow()
                
                # Nettoyer l'embedding des métadonnées (plus besoin, dans Weaviate)
                chunk_metadata = chunk.chunk_metadata or {}
                if "embedding" in chunk_metadata:
                    del chunk_metadata["embedding"]
                chunk.chunk_metadata = chunk_metadata
        
        # =================================================================
        # 6. MARQUER LE DOCUMENT COMME COMPLETED
        # =================================================================
        
        indexing_time = time.time() - start_time
        total_processing_time = (
            (document.extraction_time_seconds or 0) +
            (document.chunking_time_seconds or 0) +
            (document.embedding_time_seconds or 0) +
            indexing_time
        )
        
        document.status = DocumentStatus.COMPLETED
        document.processing_stage = ProcessingStage.INDEXING
        document.total_chunks = total_indexed
        document.total_processing_time_seconds = total_processing_time
        document.processed_at = datetime.utcnow()
        
        # Mettre à jour les métadonnées
        doc_metadata = document.document_metadata or {}
        doc_metadata["indexing_stats"] = {
            "total_indexed": total_indexed,
            "total_errors": total_errors,
            "time_seconds": indexing_time,
            "collection": "DocumentChunk",
        }
        document.document_metadata = doc_metadata
        
        db.commit()
        
        logger.info(
            f"Indexation terminée pour document {document_id}: "
            f"{total_indexed} chunks indexés, {total_errors} erreurs, "
            f"{indexing_time:.2f}s"
        )
        
        return {
            "document_id": str(document_id),
            "status": "success",
            "chunks_indexed": total_indexed,
            "chunks_errors": total_errors,
            "missing_embeddings": missing_embeddings,
            "processing_time_seconds": indexing_time,
            "total_processing_time_seconds": total_processing_time,
            "document_status": "COMPLETED"
        }
        
    except Exception as e:
        logger.error(f"Erreur indexation document {document_id}: {e}")
        
        # Mettre à jour le status en cas d'erreur
        try:
            from app.models.document import Document, DocumentStatus, ProcessingStage
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_stage = ProcessingStage.INDEXING
                document.error_message = str(e)[:1000]
                document.retry_count = (document.retry_count or 0) + 1
                db.commit()
        except Exception:
            db.rollback()
        
        raise
        
    finally:
        if weaviate_client:
            weaviate_client.close()
        db.close()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def reindex_document(document_id: str) -> str:
    """
    Re-indexe un document (supprime et recrée dans Weaviate).
    
    Args:
        document_id: UUID du document
        
    Returns:
        Task ID de la tâche d'indexation
    """
    task = index_to_weaviate.delay(document_id)
    return task.id


def delete_document_from_index(document_id: str) -> int:
    """
    Supprime un document de l'index Weaviate.
    
    Args:
        document_id: UUID du document
        
    Returns:
        Nombre de chunks supprimés
    """
    from app.clients.weaviate_client import get_weaviate_client
    
    weaviate_client = get_weaviate_client()
    try:
        return weaviate_client.delete_document_chunks(document_id)
    finally:
        weaviate_client.close()


def get_indexing_stats() -> Dict[str, Any]:
    """
    Récupère les statistiques globales de l'index.
    
    Returns:
        Dict avec les statistiques
    """
    from app.clients.weaviate_client import get_weaviate_client
    
    weaviate_client = get_weaviate_client()
    try:
        return weaviate_client.get_collection_stats()
    finally:
        weaviate_client.close()