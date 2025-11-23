# -*- coding: utf-8 -*-
"""
HybridRetriever - Recherche hybride dans Weaviate.

Ce module implémente la recherche hybride combinant :
- BM25 (recherche lexicale/keyword)
- Recherche sémantique (vecteurs/embeddings)

Le paramètre alpha contrôle le ratio : alpha=0.75 signifie 75% sémantique, 25% BM25.

MODIFICATION: Les configurations (alpha, top_k) sont lues depuis la DB via ConfigService.

Sprint 6 - Phase 2 : Retriever & Reranker
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import settings
from app.db.session import SessionLocal

# Configuration du logger
logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT (fallback si DB non disponible)
# =============================================================================

DEFAULT_SEARCH_ALPHA = 0.75
DEFAULT_SEARCH_TOP_K = 10
DEFAULT_COLLECTION_NAME = "DocumentChunk"


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_search_config() -> Dict[str, Any]:
    """
    Récupère la configuration de recherche depuis la DB.
    
    Returns:
        Dict avec top_k, alpha, rerank_enabled
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            return {
                "top_k": service.get_value("search.top_k", db, default=DEFAULT_SEARCH_TOP_K),
                "alpha": service.get_value("search.hybrid_alpha", db, default=DEFAULT_SEARCH_ALPHA),
                "rerank_enabled": service.get_value("search.rerank_enabled", db, default=True),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config recherche: {e}")
        return {
            "top_k": DEFAULT_SEARCH_TOP_K,
            "alpha": DEFAULT_SEARCH_ALPHA,
            "rerank_enabled": True
        }


def get_search_alpha() -> float:
    """Récupère le paramètre alpha depuis la config DB."""
    config = get_search_config()
    return config.get("alpha", DEFAULT_SEARCH_ALPHA)


def get_search_top_k() -> int:
    """Récupère le paramètre top_k depuis la config DB."""
    config = get_search_config()
    return config.get("top_k", DEFAULT_SEARCH_TOP_K)


def is_rerank_enabled() -> bool:
    """Vérifie si le reranking est activé depuis la config DB."""
    config = get_search_config()
    return config.get("rerank_enabled", True)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetrievedChunk:
    """
    Représente un chunk récupéré par la recherche hybride.
    
    Attributes:
        chunk_id: ID unique du chunk dans la base de données
        weaviate_id: ID du chunk dans Weaviate
        document_id: ID du document source
        document_title: Titre du document source
        category_name: Nom de la catégorie du document
        text: Contenu textuel du chunk
        page_number: Numéro de page dans le document original
        chunk_index: Index du chunk dans le document
        score: Score de pertinence (0-1)
        score_bm25: Score BM25 (si disponible)
        score_vector: Score vectoriel (si disponible)
    """
    chunk_id: str
    weaviate_id: str
    document_id: str
    document_title: str
    category_name: str
    text: str
    page_number: int
    chunk_index: int
    score: float
    score_bm25: Optional[float] = None
    score_vector: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "chunk_id": self.chunk_id,
            "weaviate_id": self.weaviate_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "category_name": self.category_name,
            "text": self.text,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "score": self.score,
            "score_bm25": self.score_bm25,
            "score_vector": self.score_vector,
            "metadata": self.metadata
        }
    
    def to_source_dict(self) -> dict:
        """Convertit en format source pour l'affichage."""
        return {
            "document_id": self.document_id,
            "title": self.document_title,
            "category": self.category_name,
            "page": self.page_number,
            "chunk_index": self.chunk_index,
            "relevance_score": round(self.score, 4)
        }


# =============================================================================
# HYBRID RETRIEVER
# =============================================================================

class HybridRetriever:
    """
    Classe pour la recherche hybride dans Weaviate.
    
    Combine la recherche BM25 (lexicale) et la recherche vectorielle (sémantique)
    pour obtenir les chunks les plus pertinents pour une question donnée.
    
    Les configurations (alpha, top_k) sont lues dynamiquement depuis la DB.
    
    Attributes:
        weaviate_client: Client Weaviate pour les requêtes
        mistral_client: Client Mistral pour l'embedding des questions
        collection_name: Nom de la collection Weaviate
    """
    
    # Nom de la collection Weaviate pour les chunks
    COLLECTION_NAME = DEFAULT_COLLECTION_NAME
    
    def __init__(
        self,
        weaviate_client = None,
        mistral_client = None,
        collection_name: str = None
    ):
        """
        Initialise le HybridRetriever.
        
        Args:
            weaviate_client: Client Weaviate (optionnel, créé si non fourni)
            mistral_client: Client Mistral (optionnel, créé si non fourni)
            collection_name: Nom de la collection Weaviate
        """
        # Import différé pour éviter les imports circulaires
        if weaviate_client is None:
            from app.clients.weaviate_client import WeaviateClient
            self.weaviate_client = WeaviateClient()
        else:
            self.weaviate_client = weaviate_client
            
        if mistral_client is None:
            from app.clients.mistral_client import get_mistral_client
            self.mistral_client = get_mistral_client()
        else:
            self.mistral_client = mistral_client
            
        self.collection_name = collection_name or self.COLLECTION_NAME
        
        # Lire les configs depuis la DB
        config = get_search_config()
        
        logger.info(
            f"HybridRetriever initialisé - Collection: {self.collection_name}, "
            f"Alpha: {config['alpha']}, Top-K: {config['top_k']} (depuis DB)"
        )
    
    async def search(
        self,
        query: str,
        top_k: int = None,
        alpha: float = None,
        category_filter: Optional[str] = None,
        document_ids_filter: Optional[List[str]] = None,
        min_score: float = 0.0
    ) -> List[RetrievedChunk]:
        """
        Effectue une recherche hybride dans Weaviate.
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre de résultats à retourner (défaut: depuis DB)
            alpha: Ratio hybride (0=BM25, 1=vector, défaut: depuis DB)
            category_filter: Filtrer par catégorie (optionnel)
            document_ids_filter: Filtrer par IDs de documents (optionnel)
            min_score: Score minimum pour inclure un résultat (défaut: 0.0)
        
        Returns:
            Liste de RetrievedChunk triés par score décroissant
        
        Raises:
            ValueError: Si la query est vide
            Exception: Si erreur lors de la recherche
        """
        # Validation
        if not query or not query.strip():
            raise ValueError("La question ne peut pas être vide")
        
        query = query.strip()
        
        # Récupérer les configs depuis la DB si non spécifiées
        if top_k is None:
            top_k = get_search_top_k()
        if alpha is None:
            alpha = get_search_alpha()
        
        logger.info(f"Recherche hybride - Query: '{query[:50]}...', top_k={top_k}, alpha={alpha}")
        
        try:
            # Étape 1: Embedding de la question
            query_embedding = await self._embed_query(query)
            
            # Étape 2: Construction des filtres
            filters = self._build_filters(category_filter, document_ids_filter)
            
            # Étape 3: Recherche hybride dans Weaviate
            raw_results = await self._execute_hybrid_search(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                alpha=alpha,
                filters=filters
            )
            
            # Étape 4: Conversion et filtrage des résultats
            chunks = self._process_results(raw_results, min_score)
            
            logger.info(f"Recherche terminée - {len(chunks)} chunks trouvés")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche hybride: {str(e)}")
            raise
    
    async def search_with_embedding(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = None,
        alpha: float = None,
        category_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[RetrievedChunk]:
        """
        Recherche hybride avec un embedding déjà calculé.
        
        Utile quand l'embedding a déjà été calculé pour le cache L2.
        
        Args:
            query: Question de l'utilisateur
            query_embedding: Vecteur embedding de la question
            top_k: Nombre de résultats
            alpha: Ratio hybride
            category_filter: Filtre catégorie
            min_score: Score minimum
        
        Returns:
            Liste de RetrievedChunk
        """
        # Récupérer les configs depuis la DB si non spécifiées
        if top_k is None:
            top_k = get_search_top_k()
        if alpha is None:
            alpha = get_search_alpha()
        
        logger.info(f"Recherche avec embedding fourni - top_k={top_k}, alpha={alpha}")
        
        try:
            filters = self._build_filters(category_filter, None)
            
            raw_results = await self._execute_hybrid_search(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                alpha=alpha,
                filters=filters
            )
            
            return self._process_results(raw_results, min_score)
            
        except Exception as e:
            logger.error(f"Erreur recherche avec embedding: {str(e)}")
            raise
    
    async def _embed_query(self, query: str) -> List[float]:
        """
        Génère l'embedding de la question via Mistral.
        
        Args:
            query: Question à embedder
        
        Returns:
            Vecteur embedding (1024 dimensions)
        """
        logger.debug(f"Embedding de la question: '{query[:30]}...'")
        
        # Utiliser la méthode synchrone du client Mistral
        result = self.mistral_client.embed_texts([query])
        embedding = result.embeddings[0] if result.embeddings else []
        
        logger.debug(f"Embedding généré - {len(embedding)} dimensions")
        
        return embedding
    
    def _build_filters(
        self,
        category_filter: Optional[str],
        document_ids_filter: Optional[List[str]]
    ) -> Optional[dict]:
        """
        Construit les filtres Weaviate.
        
        Args:
            category_filter: Nom de la catégorie
            document_ids_filter: Liste d'IDs de documents
        
        Returns:
            Dictionnaire de filtres Weaviate ou None
        """
        conditions = []
        
        if category_filter:
            conditions.append({
                "path": ["category_name"],
                "operator": "Equal",
                "valueText": category_filter
            })
        
        if document_ids_filter:
            conditions.append({
                "path": ["document_id"],
                "operator": "ContainsAny",
                "valueTextArray": document_ids_filter
            })
        
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {
            "operator": "And",
            "operands": conditions
        }
    
    async def _execute_hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int,
        alpha: float,
        filters: Optional[dict]
    ) -> List[dict]:
        """
        Exécute la recherche hybride dans Weaviate.
        
        Args:
            query: Question (pour BM25)
            query_embedding: Vecteur (pour recherche vectorielle)
            top_k: Nombre de résultats
            alpha: Ratio hybride
            filters: Filtres optionnels
        
        Returns:
            Liste de résultats bruts de Weaviate
        """
        # Propriétés à récupérer
        properties = [
            "chunk_id",
            "document_id", 
            "document_title",
            "category_name",
            "content",
            "page_number",
            "chunk_index",
            "uploaded_by",
            "upload_date"
        ]
        
        # Appel à Weaviate
        results = await self.weaviate_client.hybrid_search(
            collection_name=self.collection_name,
            query=query,
            vector=query_embedding,
            alpha=alpha,
            limit=top_k,
            properties=properties,
            where_filter=filters,
            return_metadata=True
        )
        
        return results
    
    def _process_results(
        self,
        raw_results: List[dict],
        min_score: float
    ) -> List[RetrievedChunk]:
        """
        Convertit les résultats bruts en RetrievedChunk.
        
        Args:
            raw_results: Résultats de Weaviate
            min_score: Score minimum
        
        Returns:
            Liste de RetrievedChunk filtrés et triés
        """
        chunks = []
        
        for result in raw_results:
            # Extraction du score
            score = result.get("_additional", {}).get("score", 0.0)
            
            # Filtrage par score minimum
            if score < min_score:
                continue
            
            # Création du RetrievedChunk
            chunk = RetrievedChunk(
                chunk_id=result.get("chunk_id", ""),
                weaviate_id=result.get("_additional", {}).get("id", ""),
                document_id=result.get("document_id", ""),
                document_title=result.get("document_title", "Document sans titre"),
                category_name=result.get("category_name", ""),
                text=result.get("content", ""),
                page_number=result.get("page_number", 0),
                chunk_index=result.get("chunk_index", 0),
                score=float(score),
                score_bm25=result.get("_additional", {}).get("explainScore", {}).get("bm25", None),
                score_vector=result.get("_additional", {}).get("explainScore", {}).get("vector", None),
                metadata={
                    "uploaded_by": result.get("uploaded_by"),
                    "upload_date": result.get("upload_date")
                }
            )
            
            chunks.append(chunk)
        
        # Tri par score décroissant
        chunks.sort(key=lambda x: x.score, reverse=True)
        
        return chunks
    
    def get_config(self) -> dict:
        """Retourne la configuration actuelle du retriever (depuis DB)."""
        config = get_search_config()
        return {
            "collection_name": self.collection_name,
            "alpha": config["alpha"],
            "top_k": config["top_k"],
            "rerank_enabled": config["rerank_enabled"],
            "source": "database"
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """
    Retourne une instance singleton du HybridRetriever.
    
    Returns:
        Instance HybridRetriever
    """
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance


# =============================================================================
# FACTORY FUNCTION (pour compatibilité)
# =============================================================================

def create_retriever(
    alpha: float = None,
    top_k: int = None
) -> HybridRetriever:
    """
    Factory function pour créer un HybridRetriever.
    
    Note: Les valeurs alpha et top_k sont ignorées car elles sont
    maintenant lues dynamiquement depuis la DB à chaque recherche.
    
    Args:
        alpha: Ignoré (utilise DB)
        top_k: Ignoré (utilise DB)
    
    Returns:
        Instance de HybridRetriever configurée
    """
    if alpha is not None or top_k is not None:
        logger.warning(
            "Les paramètres alpha/top_k passés à create_retriever() sont ignorés. "
            "Les valeurs sont lues depuis la base de données."
        )
    
    return HybridRetriever()