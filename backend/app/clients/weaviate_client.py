"""
Client Weaviate pour l'indexation et la recherche vectorielle.

Ce client gère toutes les interactions avec la base Weaviate.
"""
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from uuid import UUID

import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.classes.query import MetadataQuery
from weaviate.classes.data import DataObject
from weaviate.util import generate_uuid5

from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Nom de la collection pour les chunks de documents
COLLECTION_NAME = "DocumentChunk"

# Configuration des vecteurs
VECTOR_DIMENSION = 1024  # Dimension mistral-embed


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class IndexingResult:
    """Résultat d'une opération d'indexation."""
    success_count: int
    error_count: int
    weaviate_ids: List[str]
    processing_time_seconds: float
    errors: List[Dict[str, Any]]


@dataclass
class SearchResult:
    """Résultat d'une recherche."""
    chunk_id: str
    weaviate_id: str
    content: str
    score: float
    distance: Optional[float]
    metadata: Dict[str, Any]


# =============================================================================
# WEAVIATE CLIENT
# =============================================================================

class WeaviateClient:
    """
    Client pour Weaviate.
    
    Gère :
    - Création/gestion de la collection
    - Insertion batch de vecteurs
    - Recherche hybride (BM25 + semantic)
    - Suppression de documents
    """
    
    def __init__(self, url: Optional[str] = None):
        """
        Initialise le client Weaviate.
        
        Args:
            url: URL Weaviate (utilise settings si non fournie)
        """
        self.url = url or settings.WEAVIATE_URL
        self._client: Optional[weaviate.WeaviateClient] = None
        
    @property
    def client(self) -> weaviate.WeaviateClient:
        """Retourne le client Weaviate (connexion lazy)."""
        if self._client is None:
            self._client = weaviate.connect_to_local(
                host=self.url.replace("http://", "").split(":")[0],
                port=int(self.url.split(":")[-1]) if ":" in self.url.split("/")[-1] else 8080
            )
        return self._client
    
    def close(self):
        """Ferme la connexion."""
        if self._client is not None:
            self._client.close()
            self._client = None
    
    # =========================================================================
    # COLLECTION MANAGEMENT
    # =========================================================================
    
    def create_collection(self, force_recreate: bool = False) -> bool:
        """
        Crée la collection DocumentChunk si elle n'existe pas.
        
        Args:
            force_recreate: Si True, supprime et recrée la collection
            
        Returns:
            True si créée, False si existait déjà
        """
        try:
            # Vérifier si la collection existe
            if self.client.collections.exists(COLLECTION_NAME):
                if force_recreate:
                    logger.warning(f"Suppression de la collection {COLLECTION_NAME}")
                    self.client.collections.delete(COLLECTION_NAME)
                else:
                    logger.info(f"Collection {COLLECTION_NAME} existe déjà")
                    return False
            
            # Créer la collection
            self.client.collections.create(
                name=COLLECTION_NAME,
                description="Chunks de documents pour le RAG BEAC",
                
                # Configuration vectorielle
                vectorizer_config=Configure.Vectorizer.none(),  # Vecteurs fournis
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    ef_construction=128,
                    max_connections=64,
                ),
                
                # Propriétés pour BM25
                properties=[
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="Contenu textuel du chunk",
                        tokenization=weaviate.classes.config.Tokenization.WORD,  # Pour BM25
                    ),
                    Property(
                        name="document_id",
                        data_type=DataType.TEXT,
                        description="UUID du document source",
                    ),
                    Property(
                        name="chunk_id",
                        data_type=DataType.TEXT,
                        description="UUID du chunk en base",
                    ),
                    Property(
                        name="chunk_index",
                        data_type=DataType.INT,
                        description="Index du chunk dans le document",
                    ),
                    Property(
                        name="document_title",
                        data_type=DataType.TEXT,
                        description="Titre du document",
                        tokenization=weaviate.classes.config.Tokenization.WORD,
                    ),
                    Property(
                        name="category_name",
                        data_type=DataType.TEXT,
                        description="Nom de la catégorie",
                    ),
                    Property(
                        name="page_number",
                        data_type=DataType.INT,
                        description="Numéro de page",
                    ),
                    Property(
                        name="filename",
                        data_type=DataType.TEXT,
                        description="Nom du fichier original",
                    ),
                    Property(
                        name="file_type",
                        data_type=DataType.TEXT,
                        description="Extension du fichier",
                    ),
                ],
                
                # Configuration de l'inverted index pour BM25
                inverted_index_config=Configure.inverted_index(
                    bm25_b=0.75,
                    bm25_k1=1.2,
                ),
            )
            
            logger.info(f"Collection {COLLECTION_NAME} créée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur création collection: {e}")
            raise
    
    def collection_exists(self) -> bool:
        """Vérifie si la collection existe."""
        return self.client.collections.exists(COLLECTION_NAME)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la collection."""
        try:
            collection = self.client.collections.get(COLLECTION_NAME)
            aggregate = collection.aggregate.over_all(total_count=True)
            
            return {
                "name": COLLECTION_NAME,
                "total_objects": aggregate.total_count,
            }
        except Exception as e:
            logger.error(f"Erreur stats collection: {e}")
            return {"name": COLLECTION_NAME, "total_objects": 0, "error": str(e)}
    
    # =========================================================================
    # INDEXING
    # =========================================================================
    
    def batch_insert(
        self,
        chunks_data: List[Dict[str, Any]]
    ) -> IndexingResult:
        """
        Insère un batch de chunks avec leurs vecteurs.
        
        Args:
            chunks_data: Liste de dicts avec:
                - chunk_id: UUID du chunk
                - content: Texte du chunk
                - vector: Liste de floats (embedding)
                - document_id: UUID du document
                - chunk_index: Index du chunk
                - document_title: Titre (optionnel)
                - category_name: Catégorie (optionnel)
                - page_number: Page (optionnel)
                - filename: Nom fichier (optionnel)
                - file_type: Extension (optionnel)
                
        Returns:
            IndexingResult avec statistiques
        """
        start_time = time.time()
        success_count = 0
        error_count = 0
        weaviate_ids = []
        errors = []
        
        try:
            # Assurer que la collection existe
            if not self.collection_exists():
                self.create_collection()
            
            collection = self.client.collections.get(COLLECTION_NAME)
            
            # Préparer les objets
            objects_to_insert = []
            for chunk in chunks_data:
                # Générer un UUID déterministe basé sur chunk_id
                weaviate_uuid = generate_uuid5(str(chunk["chunk_id"]))
                
                obj = DataObject(
                    properties={
                        "content": chunk["content"],
                        "document_id": str(chunk["document_id"]),
                        "chunk_id": str(chunk["chunk_id"]),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "document_title": chunk.get("document_title", ""),
                        "category_name": chunk.get("category_name", ""),
                        "page_number": chunk.get("page_number"),
                        "filename": chunk.get("filename", ""),
                        "file_type": chunk.get("file_type", ""),
                    },
                    vector=chunk["vector"],
                    uuid=weaviate_uuid,
                )
                objects_to_insert.append(obj)
                weaviate_ids.append(str(weaviate_uuid))
            
            # Insertion batch
            with collection.batch.dynamic() as batch:
                for obj in objects_to_insert:
                    batch.add_object(
                        properties=obj.properties,
                        vector=obj.vector,
                        uuid=obj.uuid,
                    )
            
            # Vérifier les erreurs (le batch dynamic gère automatiquement)
            success_count = len(objects_to_insert)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"Indexation batch réussie: {success_count} objets, "
                f"{processing_time:.2f}s"
            )
            
            return IndexingResult(
                success_count=success_count,
                error_count=error_count,
                weaviate_ids=weaviate_ids,
                processing_time_seconds=processing_time,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Erreur indexation batch: {e}")
            processing_time = time.time() - start_time
            return IndexingResult(
                success_count=success_count,
                error_count=len(chunks_data) - success_count,
                weaviate_ids=weaviate_ids,
                processing_time_seconds=processing_time,
                errors=[{"error": str(e)}]
            )
    
    # =========================================================================
    # DELETION
    # =========================================================================
    
    def delete_document_chunks(self, document_id: str) -> int:
        """
        Supprime tous les chunks d'un document.
        
        Args:
            document_id: UUID du document
            
        Returns:
            Nombre d'objets supprimés
        """
        try:
            collection = self.client.collections.get(COLLECTION_NAME)
            
            # Supprimer par filtre sur document_id
            result = collection.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("document_id").equal(str(document_id))
            )
            
            deleted_count = result.successful if hasattr(result, 'successful') else 0
            logger.info(f"Supprimé {deleted_count} chunks pour document {document_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erreur suppression chunks: {e}")
            return 0
    
    # =========================================================================
    # SEARCH (placeholder pour Sprint 6)
    # =========================================================================
    
    def hybrid_search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        alpha: float = 0.75
    ) -> List[SearchResult]:
        """
        Recherche hybride (BM25 + semantic).
        
        Sera implémentée complètement dans le Sprint 6.
        
        Args:
            query: Texte de la requête
            query_vector: Vecteur de la requête
            top_k: Nombre de résultats
            alpha: Poids semantic vs BM25 (0=BM25, 1=semantic)
            
        Returns:
            Liste de SearchResult
        """
        try:
            collection = self.client.collections.get(COLLECTION_NAME)
            
            # Recherche hybride
            response = collection.query.hybrid(
                query=query,
                vector=query_vector,
                alpha=alpha,
                limit=top_k,
                return_metadata=MetadataQuery(score=True, distance=True),
            )
            
            results = []
            for obj in response.objects:
                results.append(SearchResult(
                    chunk_id=obj.properties.get("chunk_id", ""),
                    weaviate_id=str(obj.uuid),
                    content=obj.properties.get("content", ""),
                    score=obj.metadata.score if obj.metadata else 0.0,
                    distance=obj.metadata.distance if obj.metadata else None,
                    metadata={
                        "document_id": obj.properties.get("document_id"),
                        "document_title": obj.properties.get("document_title"),
                        "chunk_index": obj.properties.get("chunk_index"),
                        "page_number": obj.properties.get("page_number"),
                        "filename": obj.properties.get("filename"),
                        "category_name": obj.properties.get("category_name"),
                    }
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            return []


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_weaviate_client: Optional[WeaviateClient] = None


def get_weaviate_client() -> WeaviateClient:
    """
    Retourne une instance singleton du client Weaviate.
    
    Returns:
        Instance WeaviateClient
    """
    global _weaviate_client
    if _weaviate_client is None:
        _weaviate_client = WeaviateClient()
    return _weaviate_client