"""Embedding worker tasks - Placeholder for Sprint 5."""
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.embedding_tasks.embed_chunks",
    queue="embedding"
)
def embed_chunks(document_id: str):
    """
    Placeholder pour l'embedding des chunks.
    
    Cette task sera implémentée dans le Sprint 5 - Phase 2.
    Pour l'instant, elle log simplement qu'elle a été appelée.
    
    Args:
        document_id: UUID du document
    """
    logger.info(f"Embedding task called for document {document_id} (not yet implemented)")
    # TODO: Implémenter l'embedding dans Sprint 5
    pass