"""
Service de configuration centralisé.

Ce service gère :
- Lecture des configurations depuis la table system_config
- Cache Redis pour éviter les requêtes DB répétées
- Mise à jour des configurations par l'admin
- Invalidation automatique du cache

Toutes les configurations du système sont centralisées ici.
"""
import logging
import json
from typing import Optional, Any, Dict, List
from datetime import datetime
from copy import deepcopy

from sqlalchemy.orm import Session
from sqlalchemy import and_
import redis

from app.models.system_config import SystemConfig
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CACHE
# =============================================================================

# Préfixe pour les clés Redis
CACHE_PREFIX = "irobot:config:"

# TTL par défaut du cache (5 minutes)
DEFAULT_CACHE_TTL = 1800


# =============================================================================
# CONFIG SERVICE
# =============================================================================

class ConfigService:
    """
    Service centralisé pour la gestion des configurations.
    
    Utilise un cache Redis pour optimiser les performances.
    Les configurations sont stockées dans la table system_config.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialise le service de configuration.
        
        Args:
            redis_client: Client Redis (créé automatiquement si non fourni)
        """
        if redis_client:
            self._redis = redis_client
        else:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis non disponible, cache désactivé: {e}")
                self._redis = None
    
    # =========================================================================
    # LECTURE DE CONFIGURATION
    # =========================================================================
    
    def get(
        self,
        key: str,
        db: Session,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """
        Récupère une valeur de configuration.
        
        Args:
            key: Clé de configuration (ex: "chunking.size")
            db: Session database
            default: Valeur par défaut si non trouvée
            use_cache: Utiliser le cache Redis
            
        Returns:
            Valeur de la configuration ou default
        """
        # Essayer le cache d'abord
        if use_cache and self._redis:
            cached = self._get_from_cache(key)
            if cached is not None:
                return cached
        
        # Lire depuis la DB
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config is None:
            logger.debug(f"Config '{key}' non trouvée, utilisation défaut: {default}")
            return default
        
        value = config.value
        
        # Mettre en cache
        if use_cache and self._redis:
            self._set_cache(key, value)
        
        return value
    
    def get_value(
        self,
        key: str,
        db: Session,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """
        Récupère la valeur "value" d'une configuration JSONB.
        
        Pratique quand la config est du type {"value": 100, "description": "..."}
        
        Args:
            key: Clé de configuration
            db: Session database
            default: Valeur par défaut
            use_cache: Utiliser le cache
            
        Returns:
            La valeur extraite ou default
        """
        config = self.get(key, db, default=None, use_cache=use_cache)
        
        if config is None:
            return default
        
        if isinstance(config, dict) and "value" in config:
            return config["value"]
        
        return config
    
    def get_pricing(
        self,
        model_key: str,
        db: Session
    ) -> Dict[str, float]:
        """
        Récupère les tarifs pour un modèle Mistral.
        
        Args:
            model_key: Clé du modèle (embed, small, medium, large, ocr)
            db: Session database
            
        Returns:
            Dict avec price_per_million_input, price_per_million_output
        """
        config = self.get(f"mistral.pricing.{model_key}", db, default={})
        
        return {
            "price_per_million_input": config.get("price_per_million_input", 0.0),
            "price_per_million_output": config.get("price_per_million_output", 0.0),
            "model": config.get("model", f"mistral-{model_key}"),
        }
    
    def get_model_config(
        self,
        model_type: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Récupère la configuration d'un modèle.
        
        Args:
            model_type: Type de modèle (embedding, reranking, generation, title_generation, ocr)
            db: Session database
            
        Returns:
            Dict avec la configuration du modèle
        """
        return self.get(f"models.{model_type}", db, default={})
    
    def get_all_by_category(
        self,
        category: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Récupère toutes les configurations d'une catégorie.
        
        Args:
            category: Catégorie (pricing, models, chunking, etc.)
            db: Session database
            
        Returns:
            Dict avec toutes les configs de la catégorie
        """
        configs = db.query(SystemConfig).filter(
            SystemConfig.category == category
        ).all()
        
        result = {}
        for config in configs:
            # Extraire la partie après le préfixe de catégorie
            short_key = config.key.replace(f"{category}.", "")
            result[short_key] = config.value
        
        return result
    
    def get_all(self, db: Session) -> Dict[str, Any]:
        """
        Récupère toutes les configurations.
        
        Args:
            db: Session database
            
        Returns:
            Dict avec toutes les configurations
        """
        configs = db.query(SystemConfig).all()
        return {config.key: config.value for config in configs}
    
    # =========================================================================
    # MISE À JOUR DE CONFIGURATION
    # =========================================================================
    
    def set(
        self,
        key: str,
        value: Any,
        db: Session,
        updated_by: Optional[str] = None,
        description: Optional[str] = None
    ) -> SystemConfig:
        """
        Met à jour une valeur de configuration.
        
        Args:
            key: Clé de configuration
            value: Nouvelle valeur (sera stockée en JSONB)
            db: Session database
            updated_by: ID de l'utilisateur qui fait la modification
            description: Nouvelle description (optionnel)
            
        Returns:
            L'objet SystemConfig mis à jour
        """
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config is None:
            # Créer la config si elle n'existe pas
            category = key.split(".")[0] if "." in key else "other"
            config = SystemConfig(
                key=key,
                value=value,
                description=description or f"Configuration {key}",
                category=category,
                updated_by=updated_by
            )
            db.add(config)
        else:
            config.value = value
            config.updated_at = datetime.utcnow()
            if updated_by:
                config.updated_by = updated_by
            if description:
                config.description = description
        
        db.commit()
        db.refresh(config)
        
        # Invalider le cache
        self._invalidate_cache(key)
        
        logger.info(f"Config '{key}' mise à jour par {updated_by}")
        
        return config
    
    def set_value(
        self,
        key: str,
        new_value: Any,
        db: Session,
        updated_by: Optional[str] = None
    ) -> SystemConfig:
        """
        Met à jour uniquement la valeur "value" d'une configuration JSONB.
        
        Préserve les autres champs comme "description", "unit", etc.
        
        Args:
            key: Clé de configuration
            new_value: Nouvelle valeur
            db: Session database
            updated_by: ID de l'utilisateur
            
        Returns:
            L'objet SystemConfig mis à jour
        """
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config is None:
            # Créer avec structure standard
            return self.set(key, {"value": new_value}, db, updated_by)
        
        # Mettre à jour uniquement "value" en préservant le reste
        current_value = deepcopy(config.value) if config.value else {}
        if isinstance(current_value, dict):
            current_value["value"] = new_value
        else:
            current_value = {"value": new_value}
        
        return self.set(key, current_value, db, updated_by)
    
    # =========================================================================
    # GESTION DU CACHE
    # =========================================================================
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Récupère une valeur depuis le cache Redis."""
        if not self._redis:
            return None
        
        try:
            cached = self._redis.get(f"{CACHE_PREFIX}{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Erreur cache get: {e}")
        
        return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        """Stocke une valeur dans le cache Redis."""
        if not self._redis:
            return
        
        try:
            self._redis.setex(
                f"{CACHE_PREFIX}{key}",
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.debug(f"Erreur cache set: {e}")
    
    def _invalidate_cache(self, key: str):
        """Invalide une entrée du cache."""
        if not self._redis:
            return
        
        try:
            self._redis.delete(f"{CACHE_PREFIX}{key}")
        except Exception as e:
            logger.debug(f"Erreur cache invalidate: {e}")
    
    def invalidate_all_cache(self):
        """Invalide tout le cache de configuration."""
        if not self._redis:
            return
        
        try:
            keys = self._redis.keys(f"{CACHE_PREFIX}*")
            if keys:
                self._redis.delete(*keys)
                logger.info(f"Cache config invalidé: {len(keys)} clés supprimées")
        except Exception as e:
            logger.debug(f"Erreur cache invalidate all: {e}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Retourne une instance singleton du ConfigService.
    
    Returns:
        Instance ConfigService
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_config(key: str, db: Session, default: Any = None) -> Any:
    """
    Raccourci pour récupérer une configuration.
    
    Args:
        key: Clé de configuration
        db: Session database
        default: Valeur par défaut
        
    Returns:
        Valeur de la configuration
    """
    return get_config_service().get(key, db, default)


def get_config_value(key: str, db: Session, default: Any = None) -> Any:
    """
    Raccourci pour récupérer la valeur "value" d'une configuration.
    
    Args:
        key: Clé de configuration
        db: Session database
        default: Valeur par défaut
        
    Returns:
        Valeur extraite
    """
    return get_config_service().get_value(key, db, default)


def get_embedding_config(db: Session) -> Dict[str, Any]:
    """
    Récupère la configuration complète pour l'embedding.
    
    Returns:
        Dict avec model, batch_size, dimension, pricing
    """
    service = get_config_service()
    
    model_config = service.get_model_config("embedding", db)
    pricing = service.get_pricing("embed", db)
    batch_size = service.get_value("embedding.batch_size", db, default=100)
    
    return {
        "model": model_config.get("model_name", "mistral-embed"),
        "dimension": model_config.get("dimension", 1024),
        "batch_size": batch_size,
        "price_per_million": pricing.get("price_per_million_input", 0.1),
    }


def get_chunking_config(db: Session) -> Dict[str, Any]:
    """
    Récupère la configuration complète pour le chunking.
    
    Returns:
        Dict avec chunk_size, overlap, min_size, max_size
    """
    service = get_config_service()
    
    return {
        "chunk_size": service.get_value("chunking.size", db, default=512),
        "overlap": service.get_value("chunking.overlap", db, default=51),
        "min_size": service.get_value("chunking.min_size", db, default=50),
        "max_size": service.get_value("chunking.max_size", db, default=1024),
    }


def get_generation_config(db: Session) -> Dict[str, Any]:
    """
    Récupère la configuration pour la génération LLM.
    
    Returns:
        Dict avec model, max_tokens, temperature, pricing
    """
    service = get_config_service()
    
    model_config = service.get_model_config("generation", db)
    pricing = service.get_pricing("medium", db)
    
    return {
        "model": model_config.get("model_name", "mistral-medium-latest"),
        "max_tokens": model_config.get("max_tokens", 2048),
        "temperature": model_config.get("temperature", 0.7),
        "price_per_million_input": pricing.get("price_per_million_input", 0.4),
        "price_per_million_output": pricing.get("price_per_million_output", 2.0),
    }


def get_search_config(db: Session) -> Dict[str, Any]:
    """
    Récupère la configuration pour la recherche.
    
    Returns:
        Dict avec top_k, alpha, rerank_enabled
    """
    service = get_config_service()
    
    return {
        "top_k": service.get_value("search.top_k", db, default=10),
        "alpha": service.get_value("search.hybrid_alpha", db, default=0.75),
        "rerank_enabled": service.get_value("search.rerank_enabled", db, default=True),
    }