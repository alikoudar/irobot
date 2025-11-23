"""RAG module for document processing and text chunking."""
from app.rag.document_processor import DocumentProcessor
from app.rag.ocr_processor import MistralOCRClient, OCRFallbackClient
from app.rag.chunker import TextChunker, SemanticChunker
# Retriever - Recherche hybride
from app.rag.retriever import (
    HybridRetriever,
    RetrievedChunk,
    create_retriever
)

# Reranker - Reranking Mistral
from app.rag.reranker import (
    MistralReranker,
    RerankResult,
    create_reranker
)

__all__ = [
    "DocumentProcessor",
    "MistralOCRClient",
    "OCRFallbackClient",
    "TextChunker",
    "SemanticChunker",
    "HybridRetriever",
    "RetrievedChunk",
    "create_retriever",
    "MistralReranker",
    "RerankResult",
    "create_reranker",
]