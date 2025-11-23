"""
Clients module.

Ce module contient les clients pour les APIs externes:
- MistralClient: API Mistral (embedding, génération, reranking)
- WeaviateClient: Base de données vectorielle Weaviate
"""

from app.clients.mistral_client import (
    MistralClient,
    get_mistral_client,
    EmbeddingResult,
    GenerationResult,
    # Fonctions de configuration
    get_embedding_model,
    get_embedding_batch_size,
    get_embedding_dimension,
    get_reranking_model,
    get_generation_model,
    get_pricing,
    get_model_config,
    # Constantes (fallback)
    EMBEDDING_MODEL,
    RERANKING_MODEL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSION,
    DEFAULT_PRICING,
)

from app.clients.weaviate_client import (
    WeaviateClient,
    get_weaviate_client,
)

__all__ = [
    # Mistral
    "MistralClient",
    "get_mistral_client",
    "EmbeddingResult",
    "GenerationResult",
    "get_embedding_model",
    "get_embedding_batch_size",
    "get_embedding_dimension",
    "get_reranking_model",
    "get_generation_model",
    "get_pricing",
    "get_model_config",
    "EMBEDDING_MODEL",
    "RERANKING_MODEL",
    "EMBEDDING_BATCH_SIZE",
    "EMBEDDING_DIMENSION",
    "DEFAULT_PRICING",
    # Weaviate
    "WeaviateClient",
    "get_weaviate_client",
]