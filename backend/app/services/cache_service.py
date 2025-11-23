# -*- coding: utf-8 -*-
"""
CacheService - Service de gestion du cache des requêtes RAG.

Ce service gère le cache à 2 niveaux pour les requêtes du chatbot :
- Niveau 1 (L1) : Correspondance exacte via hash SHA-256
- Niveau 2 (L2) : Similarité sémantique via cosine similarity (> 0.95)

Les configurations (TTL, seuil similarité) sont lues depuis la DB via ConfigService.

Sprint 6 - Phase 3 : Cache Service
"""

import logging
import hashlib
import math
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.session import SessionLocal
from app.models.query_cache import QueryCache
from app.models.cache_document_map import CacheDocumentMap
from app.models.cache_statistics import CacheStatistics

# Configuration du logger
logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT (fallback si DB non disponible)
# =============================================================================

DEFAULT_CACHE_TTL_DAYS = 7
DEFAULT_SIMILARITY_THRESHOLD = 0.95
DEFAULT_EMBEDDING_DIMENSION = 1024


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_cache_config() -> Dict[str, Any]:
    """
    Récupère la configuration du cache depuis la DB.
    
    Returns:
        Dict avec ttl_days, similarity_threshold
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            # TTL en secondes dans la config, on le convertit en jours
            ttl_seconds = service.get_value("cache.query_ttl_seconds", db, default=3600)
            ttl_days = ttl_seconds / 86400 if ttl_seconds else DEFAULT_CACHE_TTL_DAYS
            
            return {
                "ttl_days": ttl_days if ttl_days >= 1 else DEFAULT_CACHE_TTL_DAYS,
                "similarity_threshold": service.get_value(
                    "cache.similarity_threshold", 
                    db, 
                    default=DEFAULT_SIMILARITY_THRESHOLD
                ),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config cache: {e}")
        return {
            "ttl_days": DEFAULT_CACHE_TTL_DAYS,
            "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
        }


def get_cache_ttl_days() -> int:
    """Récupère le TTL du cache en jours."""
    config = get_cache_config()
    return int(config.get("ttl_days", DEFAULT_CACHE_TTL_DAYS))


def get_similarity_threshold() -> float:
    """Récupère le seuil de similarité pour le cache L2."""
    config = get_cache_config()
    return config.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD)


# =============================================================================
# UTILITAIRES MATHÉMATIQUES
# =============================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosine entre deux vecteurs.
    
    Args:
        vec1: Premier vecteur
        vec2: Deuxième vecteur
    
    Returns:
        Similarité cosine entre 0 et 1
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def compute_query_hash(query: str) -> str:
    """
    Calcule le hash SHA-256 d'une requête.
    
    Args:
        query: Texte de la requête
    
    Returns:
        Hash SHA-256 de 64 caractères
    """
    # Normalisation : lowercase, strip, collapse whitespace
    normalized = " ".join(query.lower().strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# =============================================================================
# CACHE SERVICE
# =============================================================================

class CacheService:
    """
    Service de gestion du cache des requêtes RAG.
    
    Implémente un cache à 2 niveaux :
    - L1 : Correspondance exacte (hash SHA-256)
    - L2 : Similarité sémantique (cosine > seuil configurable)
    
    Les configurations sont lues depuis la DB via ConfigService.
    """
    
    def __init__(self):
        """Initialise le CacheService."""
        config = get_cache_config()
        logger.info(
            f"CacheService initialisé - TTL: {config['ttl_days']} jours, "
            f"Seuil similarité: {config['similarity_threshold']} (depuis DB)"
        )
    
    def _validate_document_ids(
        self,
        document_ids: List[str],
        db: Session
    ) -> List[str]:
        """
        Valide les document_ids en vérifiant qu'ils existent dans la table documents.
        
        Args:
            document_ids: Liste des IDs de documents à valider
            db: Session de base de données
        
        Returns:
            Liste des IDs de documents valides (qui existent dans la DB)
        """
        if not document_ids:
            return []
        
        from uuid import UUID
        from app.models.document import Document
        
        valid_ids = []
        
        for doc_id in document_ids:
            # Ignorer les IDs vides
            if not doc_id:
                continue
            
            try:
                # Tenter de convertir en UUID
                uuid_obj = UUID(str(doc_id))
                
                # Vérifier si le document existe
                exists = db.query(Document.id).filter(
                    Document.id == uuid_obj
                ).first()
                
                if exists:
                    valid_ids.append(str(uuid_obj))
                else:
                    logger.debug(f"Document ID non trouvé dans DB, ignoré: {doc_id}")
                    
            except (ValueError, AttributeError) as e:
                logger.debug(f"Document ID invalide (pas un UUID), ignoré: {doc_id}")
                continue
        
        logger.debug(f"Document IDs validés: {len(valid_ids)}/{len(document_ids)}")
        
        return valid_ids
    
    # =========================================================================
    # CACHE LEVEL 1 - CORRESPONDANCE EXACTE
    # =========================================================================
    
    def check_cache_level1(
        self,
        query: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Vérifie le cache de niveau 1 (correspondance exacte).
        
        Recherche une correspondance exacte via le hash SHA-256 de la requête.
        Si trouvé : incrémente hit_count, réinitialise TTL, retourne la réponse.
        
        Args:
            query: Texte de la requête utilisateur
            db: Session de base de données
        
        Returns:
            Dict avec response, sources, cache_level si trouvé, None sinon
        """
        query_hash = compute_query_hash(query)
        
        logger.debug(f"Cache L1 - Recherche hash: {query_hash[:16]}...")
        
        # Recherche dans la DB
        cache_entry = db.query(QueryCache).filter(
            and_(
                QueryCache.query_hash == query_hash,
                QueryCache.expires_at > datetime.utcnow()
            )
        ).first()
        
        if cache_entry is None:
            logger.debug("Cache L1 - Miss")
            return None
        
        # Hit trouvé
        logger.info(f"Cache L1 - Hit! (id={cache_entry.id}, hits={cache_entry.hit_count})")
        
        # Mettre à jour les statistiques
        cache_entry.increment_hit()
        cache_entry.reset_ttl(days=get_cache_ttl_days())
        db.commit()
        
        # Enregistrer dans les statistiques journalières
        self._record_cache_hit(
            db=db,
            tokens=cache_entry.token_count,
            cost_usd=float(cache_entry.cost_saved_usd),
            cost_xaf=float(cache_entry.cost_saved_xaf)
        )
        
        return {
            "cache_id": str(cache_entry.id),
            "response": cache_entry.response,
            "sources": cache_entry.sources,
            "cache_level": 1,
            "hit_count": cache_entry.hit_count,
            "token_count": cache_entry.token_count,
            "query_text": cache_entry.query_text
        }
    
    # =========================================================================
    # CACHE LEVEL 2 - SIMILARITÉ SÉMANTIQUE
    # =========================================================================
    
    def check_cache_level2(
        self,
        query: str,
        query_embedding: List[float],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Vérifie le cache de niveau 2 (similarité sémantique).
        
        Recherche une requête similaire via cosine similarity sur les embeddings.
        Seuil configurable (défaut: 0.95 = 95% de similarité).
        Si trouvé : incrémente hit_count, réinitialise TTL, retourne la réponse.
        
        Args:
            query: Texte de la requête utilisateur
            query_embedding: Vecteur embedding de la requête
            db: Session de base de données
        
        Returns:
            Dict avec response, sources, cache_level, similarity si trouvé, None sinon
        """
        if not query_embedding:
            logger.warning("Cache L2 - Embedding vide, skip")
            return None
        
        threshold = get_similarity_threshold()
        logger.debug(f"Cache L2 - Recherche similarité > {threshold}")
        
        # Récupérer tous les caches non expirés avec embedding
        cache_entries = db.query(QueryCache).filter(
            and_(
                QueryCache.query_embedding.isnot(None),
                QueryCache.expires_at > datetime.utcnow()
            )
        ).all()
        
        if not cache_entries:
            logger.debug("Cache L2 - Aucun cache avec embedding disponible")
            return None
        
        # Rechercher la meilleure correspondance
        best_match = None
        best_similarity = 0.0
        
        for entry in cache_entries:
            if not entry.query_embedding:
                continue
            
            similarity = cosine_similarity(query_embedding, entry.query_embedding)
            
            if similarity > threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        if best_match is None:
            logger.debug(f"Cache L2 - Miss (meilleure similarité: {best_similarity:.4f})")
            return None
        
        # Hit trouvé
        logger.info(
            f"Cache L2 - Hit! (id={best_match.id}, similarity={best_similarity:.4f}, "
            f"hits={best_match.hit_count})"
        )
        
        # Mettre à jour les statistiques
        best_match.increment_hit()
        best_match.reset_ttl(days=get_cache_ttl_days())
        db.commit()
        
        # Enregistrer dans les statistiques journalières
        self._record_cache_hit(
            db=db,
            tokens=best_match.token_count,
            cost_usd=float(best_match.cost_saved_usd),
            cost_xaf=float(best_match.cost_saved_xaf)
        )
        
        return {
            "cache_id": str(best_match.id),
            "response": best_match.response,
            "sources": best_match.sources,
            "cache_level": 2,
            "similarity": round(best_similarity, 4),
            "hit_count": best_match.hit_count,
            "token_count": best_match.token_count,
            "query_text": best_match.query_text,
            "original_query": best_match.query_text
        }
    
    # =========================================================================
    # VÉRIFICATION COMBINÉE (L1 + L2)
    # =========================================================================
    
    def check_cache(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Vérifie le cache à tous les niveaux (L1 puis L2).
        
        Args:
            query: Texte de la requête
            query_embedding: Embedding de la requête (optionnel pour L2)
            db: Session de base de données
        
        Returns:
            Résultat du cache si trouvé, None sinon
        """
        # Essayer L1 d'abord (plus rapide)
        result = self.check_cache_level1(query, db)
        if result:
            return result
        
        # Essayer L2 si embedding disponible
        if query_embedding:
            result = self.check_cache_level2(query, query_embedding, db)
            if result:
                return result
        
        # Enregistrer le miss
        self._record_cache_miss(db)
        
        return None
    
    # =========================================================================
    # SAUVEGARDE DANS LE CACHE
    # =========================================================================
    
    def save_to_cache(
        self,
        query: str,
        query_embedding: List[float],
        response: str,
        sources: List[Dict[str, Any]],
        document_ids: List[str],
        tokens: int,
        cost_usd: float,
        cost_xaf: float,
        db: Session
    ) -> QueryCache:
        """
        Sauvegarde une requête et sa réponse dans le cache.
        
        Args:
            query: Texte de la requête utilisateur
            query_embedding: Vecteur embedding de la requête
            response: Réponse générée par le LLM
            sources: Liste des sources utilisées
            document_ids: Liste des IDs de documents utilisés
            tokens: Nombre de tokens de la réponse
            cost_usd: Coût en USD
            cost_xaf: Coût en XAF
            db: Session de base de données
        
        Returns:
            L'objet QueryCache créé
        """
        query_hash = compute_query_hash(query)
        ttl_days = get_cache_ttl_days()
        
        logger.info(f"Sauvegarde cache - Hash: {query_hash[:16]}..., TTL: {ttl_days} jours")
        
        # Valider les document_ids avant insertion pour éviter FK violation
        valid_document_ids = self._validate_document_ids(document_ids, db)
        
        # Vérifier si un cache existe déjà pour ce hash
        existing = db.query(QueryCache).filter(
            QueryCache.query_hash == query_hash
        ).first()
        
        if existing:
            # Mettre à jour le cache existant
            logger.info(f"Cache existant trouvé (id={existing.id}), mise à jour")
            existing.response = response
            existing.sources = sources
            existing.query_embedding = query_embedding
            existing.token_count = tokens
            existing.cost_saved_usd = Decimal(str(cost_usd))
            existing.cost_saved_xaf = Decimal(str(cost_xaf))
            existing.reset_ttl(days=ttl_days)
            
            # Supprimer les anciens mappings et créer les nouveaux
            db.query(CacheDocumentMap).filter(
                CacheDocumentMap.cache_id == existing.id
            ).delete()
            
            for doc_id in valid_document_ids:
                mapping = CacheDocumentMap(
                    cache_id=existing.id,
                    document_id=doc_id
                )
                db.add(mapping)
            
            db.commit()
            db.refresh(existing)
            return existing
        
        # Créer une nouvelle entrée
        cache_entry = QueryCache(
            query_text=query,
            query_hash=query_hash,
            query_embedding=query_embedding,
            response=response,
            sources=sources,
            token_count=tokens,
            cost_saved_usd=Decimal(str(cost_usd)),
            cost_saved_xaf=Decimal(str(cost_xaf)),
            expires_at=datetime.utcnow() + timedelta(days=ttl_days)
        )
        
        db.add(cache_entry)
        db.flush()  # Pour obtenir l'ID
        
        # Créer les mappings document avec les IDs validés
        for doc_id in valid_document_ids:
            mapping = CacheDocumentMap(
                cache_id=cache_entry.id,
                document_id=doc_id
            )
            db.add(mapping)
        
        db.commit()
        db.refresh(cache_entry)
        
        logger.info(f"Cache créé - id={cache_entry.id}, documents={len(valid_document_ids)}")
        
        return cache_entry
    
    # =========================================================================
    # INVALIDATION DU CACHE
    # =========================================================================
    
    def invalidate_cache_for_document(
        self,
        document_id: str,
        db: Session
    ) -> int:
        """
        Invalide tous les caches utilisant un document spécifique.
        
        Appelé lors de la modification ou suppression d'un document pour
        garantir que les réponses obsolètes ne sont plus servies.
        
        Args:
            document_id: ID du document modifié/supprimé
            db: Session de base de données
        
        Returns:
            Nombre de caches invalidés
        """
        logger.info(f"Invalidation cache pour document: {document_id}")
        
        # Trouver tous les mappings pour ce document
        mappings = db.query(CacheDocumentMap).filter(
            CacheDocumentMap.document_id == document_id
        ).all()
        
        if not mappings:
            logger.debug("Aucun cache à invalider pour ce document")
            return 0
        
        # Extraire les cache_ids uniques
        cache_ids = list(set(m.cache_id for m in mappings))
        
        # Supprimer les entrées de cache (cascade supprime les mappings)
        deleted_count = db.query(QueryCache).filter(
            QueryCache.id.in_(cache_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        logger.info(f"Caches invalidés: {deleted_count}")
        
        return deleted_count
    
    def invalidate_expired_cache(self, db: Session) -> int:
        """
        Supprime tous les caches expirés.
        
        À appeler périodiquement via Celery Beat.
        
        Args:
            db: Session de base de données
        
        Returns:
            Nombre de caches supprimés
        """
        logger.info("Nettoyage des caches expirés")
        
        deleted_count = db.query(QueryCache).filter(
            QueryCache.expires_at < datetime.utcnow()
        ).delete(synchronize_session=False)
        
        db.commit()
        
        logger.info(f"Caches expirés supprimés: {deleted_count}")
        
        return deleted_count
    
    def invalidate_all_cache(self, db: Session) -> int:
        """
        Supprime tous les caches (reset complet).
        
        À utiliser avec précaution, généralement pour maintenance.
        
        Args:
            db: Session de base de données
        
        Returns:
            Nombre de caches supprimés
        """
        logger.warning("Invalidation complète du cache!")
        
        deleted_count = db.query(QueryCache).delete(synchronize_session=False)
        db.commit()
        
        logger.info(f"Tous les caches supprimés: {deleted_count}")
        
        return deleted_count
    
    # =========================================================================
    # STATISTIQUES
    # =========================================================================
    
    def _record_cache_hit(
        self,
        db: Session,
        tokens: int,
        cost_usd: float,
        cost_xaf: float
    ) -> None:
        """Enregistre un hit dans les statistiques journalières."""
        today = date.today()
        
        stats = db.query(CacheStatistics).filter(
            CacheStatistics.date == today
        ).first()
        
        if stats is None:
            stats = CacheStatistics(date=today)
            db.add(stats)
        
        stats.increment_hit(tokens=tokens, cost_usd=cost_usd, cost_xaf=cost_xaf)
        db.commit()
    
    def _record_cache_miss(self, db: Session) -> None:
        """Enregistre un miss dans les statistiques journalières."""
        today = date.today()
        
        stats = db.query(CacheStatistics).filter(
            CacheStatistics.date == today
        ).first()
        
        if stats is None:
            stats = CacheStatistics(date=today)
            db.add(stats)
        
        stats.increment_miss()
        db.commit()
    
    def get_statistics(
        self,
        db: Session,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques de cache sur une période.
        
        Args:
            db: Session de base de données
            days: Nombre de jours à inclure
        
        Returns:
            Dict avec les statistiques agrégées
        """
        start_date = date.today() - timedelta(days=days - 1)
        
        stats_list = db.query(CacheStatistics).filter(
            CacheStatistics.date >= start_date
        ).order_by(CacheStatistics.date.desc()).all()
        
        return CacheStatistics.get_summary(stats_list)
    
    def get_today_statistics(self, db: Session) -> Optional[CacheStatistics]:
        """
        Récupère les statistiques du jour.
        
        Args:
            db: Session de base de données
        
        Returns:
            CacheStatistics du jour ou None
        """
        return db.query(CacheStatistics).filter(
            CacheStatistics.date == date.today()
        ).first()
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du cache."""
        config = get_cache_config()
        return {
            "ttl_days": config["ttl_days"],
            "similarity_threshold": config["similarity_threshold"],
            "source": "database"
        }
    
    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================
    
    def get_cache_entry(
        self,
        cache_id: str,
        db: Session
    ) -> Optional[QueryCache]:
        """Récupère une entrée de cache par son ID."""
        return db.query(QueryCache).filter(
            QueryCache.id == cache_id
        ).first()
    
    def get_cache_count(self, db: Session) -> int:
        """Retourne le nombre total d'entrées dans le cache."""
        return db.query(QueryCache).count()
    
    def get_active_cache_count(self, db: Session) -> int:
        """Retourne le nombre d'entrées de cache non expirées."""
        return db.query(QueryCache).filter(
            QueryCache.expires_at > datetime.utcnow()
        ).count()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Retourne une instance singleton du CacheService.
    
    Returns:
        Instance CacheService
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_cache(
    query: str,
    query_embedding: Optional[List[float]],
    db: Session
) -> Optional[Dict[str, Any]]:
    """
    Raccourci pour vérifier le cache.
    
    Args:
        query: Texte de la requête
        query_embedding: Embedding de la requête
        db: Session de base de données
    
    Returns:
        Résultat du cache si trouvé
    """
    return get_cache_service().check_cache(query, query_embedding, db)


def save_to_cache(
    query: str,
    query_embedding: List[float],
    response: str,
    sources: List[Dict[str, Any]],
    document_ids: List[str],
    tokens: int,
    cost_usd: float,
    cost_xaf: float,
    db: Session
) -> QueryCache:
    """
    Raccourci pour sauvegarder dans le cache.
    """
    return get_cache_service().save_to_cache(
        query=query,
        query_embedding=query_embedding,
        response=response,
        sources=sources,
        document_ids=document_ids,
        tokens=tokens,
        cost_usd=cost_usd,
        cost_xaf=cost_xaf,
        db=db
    )


def invalidate_cache_for_document(document_id: str, db: Session) -> int:
    """Raccourci pour invalider le cache d'un document."""
    return get_cache_service().invalidate_cache_for_document(document_id, db)