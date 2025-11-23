"""Workers package for Celery tasks."""
from app.workers.processing_tasks import extract_document_text
from app.workers.chunking_tasks import chunk_document
from app.workers.embedding_tasks import embed_chunks
from app.workers.indexing_tasks import index_to_weaviate
from app.workers.periodic_tasks import (
    cleanup_expired_cache,
    update_exchange_rate,
    cleanup_old_logs
)

__all__ = [
    "extract_document_text",
    "chunk_document",
    "embed_chunks",
    "index_to_weaviate",
    "cleanup_expired_cache",
    "update_exchange_rate",
    "cleanup_old_logs",
]