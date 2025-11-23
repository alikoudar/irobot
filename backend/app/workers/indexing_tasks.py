"""Indexing worker tasks - Placeholder for Sprint 5."""
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.indexing_tasks.index_to_weaviate",
    queue="indexing"
)
def index_to_weaviate(document_id: str):
    """
    Placeholder pour l'indexation dans Weaviate.
    
    Cette task sera implémentée dans le Sprint 5 - Phase 2.
    Pour l'instant, elle log simplement qu'elle a été appelée.
    
    Args:
        document_id: UUID du document
    """
    logger.info(f"Indexing task called for document {document_id} (not yet implemented)")
    # TODO: Implémenter l'indexing dans Sprint 5
    pass