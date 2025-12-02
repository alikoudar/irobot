# -*- coding: utf-8 -*-
"""
Client Weaviate pour l'indexation et la recherche vectorielle.

Ce client gère toutes les interactions avec la base Weaviate :
- Création/gestion de la collection
- Insertion batch de vecteurs
- Recherche hybride (BM25 + semantic)
- Suppression de documents

Sprint 5 - Corrigé Sprint 7 : Ajout méthode hybrid_search async
SPRINT 13 - MONITORING: Ajout des métriques Prometheus pour toutes les opérations
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from uuid import UUID

import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.classes.query import MetadataQuery, Filter
from weaviate.classes.data import DataObject
from weaviate.util import generate_uuid5

from app.core.config import settings

# SPRINT 13 - Monitoring : Import des métriques Prometheus
from app.core.metrics import (
    record_weaviate_query,
    record_weaviate_batch_operation,
    update_weaviate_objects_total,
    record_weaviate_error,
)

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
    
    SPRINT 13: Toutes les opérations sont maintenant instrumentées avec Prometheus.
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
    
    def is_healthy(self) -> bool:
        """Vérifie si Weaviate est accessible."""
        try:
            return self.client.is_ready()
        except Exception as e:
            logger.error(f"Weaviate non accessible: {e}")
            # SPRINT 13 - Monitoring : Enregistrer l'erreur
            record_weaviate_error("connection_error")
            return False
    
    def collection_exists(self, name: str = None) -> bool:
        """Vérifie si une collection existe."""
        coll_name = name or COLLECTION_NAME
        try:
            return self.client.collections.exists(coll_name)
        except Exception as e:
            logger.error(f"Erreur vérification collection: {e}")
            record_weaviate_error("collection_check_error")
            return False
    
    def create_collection(self, name: str = None) -> bool:
        """
        Crée la collection pour les chunks de documents.
        
        Args:
            name: Nom de la collection (optionnel)
            
        Returns:
            True si création réussie ou collection existe déjà
        """
        coll_name = name or COLLECTION_NAME
        
        try:
            if self.collection_exists(coll_name):
                logger.info(f"Collection {coll_name} existe déjà")
                return True
            
            self.client.collections.create(
                name=coll_name,
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                ),
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT),
                    Property(name="document_id", data_type=DataType.TEXT),
                    Property(name="document_title", data_type=DataType.TEXT),
                    Property(name="category_name", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="page_number", data_type=DataType.INT),
                    Property(name="chunk_index", data_type=DataType.INT),
                    Property(name="uploaded_by", data_type=DataType.TEXT),
                    Property(name="upload_date", data_type=DataType.TEXT),
                    Property(name="filename", data_type=DataType.TEXT),
                ]
            )
            
            logger.info(f"Collection {coll_name} créée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur création collection: {e}")
            record_weaviate_error("collection_creation_error")
            return False
    
    def batch_insert(
        self,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]],
        collection_name: str = None
    ) -> IndexingResult:
        """
        Insère des chunks en batch dans Weaviate.
        
        SPRINT 13: Enregistre les métriques Prometheus :
        - irobot_weaviate_batch_operations_total
        - irobot_weaviate_objects_total (mis à jour)
        
        Args:
            chunks: Liste de chunks avec leurs propriétés
            vectors: Liste des vecteurs correspondants
            collection_name: Nom de la collection
            
        Returns:
            IndexingResult avec le résumé de l'opération
        """
        coll_name = collection_name or COLLECTION_NAME
        start_time = time.time()
        
        success_count = 0
        error_count = 0
        weaviate_ids = []
        errors = []
        
        try:
            collection = self.client.collections.get(coll_name)
            
            with collection.batch.dynamic() as batch:
                for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                    try:
                        # Générer un UUID déterministe
                        weaviate_id = generate_uuid5(chunk.get("chunk_id", str(i)))
                        
                        # Préparer les propriétés
                        properties = {
                            "chunk_id": chunk.get("chunk_id", ""),
                            "document_id": chunk.get("document_id", ""),
                            "document_title": chunk.get("document_title", ""),
                            "category_name": chunk.get("category_name", ""),
                            "content": chunk.get("content", chunk.get("text", "")),
                            "text": chunk.get("text", chunk.get("content", "")),
                            "page_number": chunk.get("page_number", 0),
                            "chunk_index": chunk.get("chunk_index", i),
                            "uploaded_by": chunk.get("uploaded_by", ""),
                            "upload_date": chunk.get("upload_date", ""),
                            "filename": chunk.get("filename", ""),
                        }
                        
                        batch.add_object(
                            properties=properties,
                            vector=vector,
                            uuid=weaviate_id
                        )
                        
                        success_count += 1
                        weaviate_ids.append(str(weaviate_id))
                        
                    except Exception as e:
                        error_count += 1
                        errors.append({
                            "chunk_index": i,
                            "error": str(e)
                        })
                        logger.error(f"Erreur insertion chunk {i}: {e}")
            
            processing_time = time.time() - start_time
            
            # SPRINT 13 - Monitoring : Enregistrer les métriques batch
            if success_count > 0:
                record_weaviate_batch_operation(
                    operation="insert",
                    status="success",
                    count=success_count
                )
            
            if error_count > 0:
                record_weaviate_batch_operation(
                    operation="insert",
                    status="failure",
                    count=error_count
                )
                record_weaviate_error("batch_insert_error")
            
            # SPRINT 13 - Monitoring : Mettre à jour le nombre total d'objets
            # (sera appelé périodiquement par un job séparé)
            
            logger.info(
                f"Batch insert: {success_count} succès, {error_count} erreurs, "
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
            logger.error(f"Erreur batch insert: {e}")
            record_weaviate_error("batch_insert_fatal_error")
            
            return IndexingResult(
                success_count=0,
                error_count=len(chunks),
                weaviate_ids=[],
                processing_time_seconds=time.time() - start_time,
                errors=[{"error": str(e)}]
            )
    
    async def hybrid_search(
        self,
        collection_name: str,
        query: str,
        vector: List[float],
        alpha: float = 0.75,
        limit: int = 10,
        properties: Optional[List[str]] = None,
        where_filter: Optional[dict] = None,
        return_metadata: bool = True
    ) -> List[dict]:
        """
        Recherche hybride dans Weaviate (BM25 + semantic).
        
        SPRINT 13: Enregistre les métriques Prometheus :
        - irobot_weaviate_query_duration_seconds
        
        Args:
            collection_name: Nom de la collection
            query: Texte de la requête (pour BM25)
            vector: Vecteur de la requête (pour recherche semantic)
            alpha: Poids semantic vs BM25 (0=BM25, 1=semantic)
            limit: Nombre maximum de résultats
            properties: Propriétés à retourner
            where_filter: Filtres optionnels
            return_metadata: Retourner les métadonnées (score, distance)
            
        Returns:
            Liste de résultats (format dict attendu par retriever)
        """
        # SPRINT 13 - Monitoring : Mesurer la durée
        start_time = time.time()
        
        try:
            collection = self.client.collections.get(collection_name)
            
            # Construire le filtre Weaviate
            filters = self._build_filter(where_filter) if where_filter else None
            
            # Exécuter la recherche hybride
            if filters:
                response = collection.query.hybrid(
                    query=query,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    filters=filters,
                    return_metadata=MetadataQuery(score=True, distance=True) if return_metadata else None
                )
            else:
                response = collection.query.hybrid(
                    query=query,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    return_metadata=MetadataQuery(score=True, distance=True) if return_metadata else None
                )
            
            # Convertir les résultats au format attendu par retriever
            results = []
            for obj in response.objects:
                # Calculer le score (0-1, plus haut = meilleur)
                score = obj.metadata.score if obj.metadata and hasattr(obj.metadata, 'score') else 0.0
                
                result = {}
                
                # Copier toutes les propriétés au niveau racine
                for key, value in obj.properties.items():
                    result[key] = value
                
                # Ajouter _additional pour le score (format attendu par retriever)
                result["_additional"] = {
                    "id": str(obj.uuid),
                    "score": score,
                    "distance": obj.metadata.distance if obj.metadata and hasattr(obj.metadata, 'distance') else None,
                }
                    
                results.append(result)
            
            # SPRINT 13 - Monitoring : Enregistrer la durée de la recherche
            duration = time.time() - start_time
            record_weaviate_query(
                operation="search",
                duration=duration
            )
            
            logger.debug(
                f"Recherche hybride: {len(results)} résultats pour '{query[:50]}...', "
                f"{duration:.3f}s"
            )
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Erreur recherche hybride: {e}")
            
            # SPRINT 13 - Monitoring : Enregistrer l'erreur et la durée
            record_weaviate_error("search_error")
            record_weaviate_query(
                operation="search",
                duration=duration
            )
            
            return []
    
    def _build_filter(self, where_filter: dict):
        """
        Convertit un filtre dict en filtre Weaviate.
        
        Args:
            where_filter: Dictionnaire de filtre
            
        Returns:
            Filtre Weaviate ou None
        """
        try:
            if not where_filter:
                return None
            
            # Cas simple : un seul filtre
            if "path" in where_filter:
                path = where_filter["path"][0] if isinstance(where_filter["path"], list) else where_filter["path"]
                operator = where_filter.get("operator", "Equal")
                
                if operator == "Equal":
                    value = where_filter.get("valueText") or where_filter.get("valueString")
                    return Filter.by_property(path).equal(value)
                elif operator == "ContainsAny":
                    values = where_filter.get("valueTextArray") or where_filter.get("valueStringArray")
                    return Filter.by_property(path).contains_any(values)
                elif operator == "GreaterThan":
                    value = where_filter.get("valueNumber") or where_filter.get("valueInt")
                    return Filter.by_property(path).greater_than(value)
                elif operator == "LessThan":
                    value = where_filter.get("valueNumber") or where_filter.get("valueInt")
                    return Filter.by_property(path).less_than(value)
            
            # Cas combiné : And/Or
            if "operator" in where_filter and where_filter["operator"] in ["And", "Or"]:
                operands = where_filter.get("operands", [])
                if not operands:
                    return None
                
                filters = [self._build_filter(op) for op in operands if op]
                filters = [f for f in filters if f is not None]
                
                if not filters:
                    return None
                
                if where_filter["operator"] == "And":
                    result = filters[0]
                    for f in filters[1:]:
                        result = result & f
                    return result
                else:  # Or
                    result = filters[0]
                    for f in filters[1:]:
                        result = result | f
                    return result
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur construction filtre: {e}")
            return None
    
    def search_simple(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        alpha: float = 0.75
    ) -> List[SearchResult]:
        """
        Recherche hybride simplifiée (synchrone).
        
        Args:
            query: Texte de la requête
            query_vector: Vecteur de la requête
            top_k: Nombre de résultats
            alpha: Poids semantic vs BM25 (0=BM25, 1=semantic)
            
        Returns:
            Liste de SearchResult
        """
        # SPRINT 13 - Monitoring : Mesurer la durée
        start_time = time.time()
        
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
                    content=obj.properties.get("content", obj.properties.get("text", "")),
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
            
            # SPRINT 13 - Monitoring : Enregistrer la durée
            duration = time.time() - start_time
            record_weaviate_query(
                operation="search",
                duration=duration
            )
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Erreur recherche hybride: {e}")
            
            # SPRINT 13 - Monitoring
            record_weaviate_error("search_error")
            record_weaviate_query(
                operation="search",
                duration=duration
            )
            
            return []
    
    def delete_document_chunks(
        self,
        document_id: str,
        collection_name: str = None
    ) -> int:
        """
        Supprime tous les chunks d'un document.
        
        SPRINT 13: Enregistre les métriques Prometheus :
        - irobot_weaviate_query_duration_seconds (pour delete)
        - irobot_weaviate_objects_total (mis à jour)
        
        Args:
            document_id: ID du document
            collection_name: Nom de la collection
            
        Returns:
            Nombre de chunks supprimés
        """
        coll_name = collection_name or COLLECTION_NAME
        
        # SPRINT 13 - Monitoring : Mesurer la durée
        start_time = time.time()
        
        try:
            collection = self.client.collections.get(coll_name)
            
            # Supprimer par filtre
            result = collection.data.delete_many(
                where=Filter.by_property("document_id").equal(document_id)
            )
            
            deleted_count = result.successful if hasattr(result, 'successful') else 0
            
            # SPRINT 13 - Monitoring : Enregistrer la durée de l'opération
            duration = time.time() - start_time
            record_weaviate_query(
                operation="delete",
                duration=duration
            )
            
            logger.info(
                f"Supprimé {deleted_count} chunks pour document {document_id}, "
                f"{duration:.3f}s"
            )
            
            return deleted_count
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Erreur suppression chunks: {e}")
            
            # SPRINT 13 - Monitoring
            record_weaviate_error("delete_error")
            record_weaviate_query(
                operation="delete",
                duration=duration
            )
            
            return 0
    
    def get_document_chunk_count(
        self,
        document_id: str,
        collection_name: str = None
    ) -> int:
        """
        Compte les chunks d'un document.
        
        Args:
            document_id: ID du document
            collection_name: Nom de la collection
            
        Returns:
            Nombre de chunks
        """
        coll_name = collection_name or COLLECTION_NAME
        
        try:
            collection = self.client.collections.get(coll_name)
            
            result = collection.aggregate.over_all(
                filters=Filter.by_property("document_id").equal(document_id),
                total_count=True
            )
            
            return result.total_count if result else 0
            
        except Exception as e:
            logger.error(f"Erreur comptage chunks: {e}")
            record_weaviate_error("count_error")
            return 0
    
    def get_total_objects_count(self, collection_name: str = None) -> int:
        """
        Retourne le nombre total d'objets dans une collection.
        
        SPRINT 13: Nouvelle méthode pour les métriques Prometheus.
        À appeler périodiquement pour mettre à jour irobot_weaviate_objects_total.
        
        Args:
            collection_name: Nom de la collection
            
        Returns:
            Nombre total d'objets
        """
        coll_name = collection_name or COLLECTION_NAME
        
        try:
            collection = self.client.collections.get(coll_name)
            
            result = collection.aggregate.over_all(
                total_count=True
            )
            
            count = result.total_count if result else 0
            
            # SPRINT 13 - Monitoring : Mettre à jour la métrique
            update_weaviate_objects_total(
                class_name=coll_name,
                count=count
            )
            
            return count
            
        except Exception as e:
            logger.error(f"Erreur comptage total objets: {e}")
            record_weaviate_error("total_count_error")
            return 0


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