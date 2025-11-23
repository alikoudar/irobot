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

# Prompts
from app.rag.prompts import (
    # Constantes
    SYSTEM_PROMPT_BASE,
    CONTEXT_HEADER,
    CONTEXT_CHUNK_TEMPLATE,
    CONTEXT_CHUNK_SIMPLE_TEMPLATE,
    HISTORY_HEADER,
    HISTORY_MESSAGE_TEMPLATE,
    QUERY_HEADER,
    INSTRUCTIONS_FOOTER,
    FORMAT_INSTRUCTIONS,
    TITLE_GENERATION_PROMPT,
    TITLE_GENERATION_SYSTEM_PROMPT,
    NO_CONTEXT_RESPONSE,
    # Enums
    ResponseFormat,
    # Data classes
    ChunkForPrompt,
    HistoryMessage,
    # Classes
    PromptBuilder,
    # Fonctions utilitaires
    chunks_to_prompt_format,
    messages_to_history_format,
    get_format_for_query,
    get_prompt_builder,
    create_prompt_builder,
)

# Generator
from app.rag.generator import (
    GenerationMetadata,
    StreamedChunk,
    GenerationResult,
    LLMGenerator,
    get_generator,
    create_generator,
    get_generation_config,
    get_title_generation_config,
    get_generation_pricing,
    get_exchange_rate,
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

    # Prompts - Constantes
    "SYSTEM_PROMPT_BASE",
    "CONTEXT_HEADER",
    "CONTEXT_CHUNK_TEMPLATE",
    "CONTEXT_CHUNK_SIMPLE_TEMPLATE",
    "HISTORY_HEADER",
    "HISTORY_MESSAGE_TEMPLATE",
    "QUERY_HEADER",
    "INSTRUCTIONS_FOOTER",
    "FORMAT_INSTRUCTIONS",
    "TITLE_GENERATION_PROMPT",
    "TITLE_GENERATION_SYSTEM_PROMPT",
    "NO_CONTEXT_RESPONSE",
    # Prompts - Enums
    "ResponseFormat",
    # Prompts - Data classes
    "ChunkForPrompt",
    "HistoryMessage",
    # Prompts - Classes
    "PromptBuilder",
    # Prompts - Fonctions
    "chunks_to_prompt_format",
    "messages_to_history_format",
    "get_format_for_query",
    "get_prompt_builder",
    "create_prompt_builder",
    # Generator
    "GenerationMetadata",
    "StreamedChunk",
    "GenerationResult",
    "LLMGenerator",
    "get_generator",
    "create_generator",
    "get_generation_config",
    "get_title_generation_config",
    "get_generation_pricing",
    "get_exchange_rate",
]