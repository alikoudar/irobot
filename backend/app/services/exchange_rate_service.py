"""
Service de gestion des taux de change.

Ce service gère:
- Récupération du taux de change actuel depuis la DB
- Fallback sur le taux par défaut (config)
- Mise à jour depuis l'API externe (via periodic task)
- Cache Redis pour optimiser les performances
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc
import redis

from app.models.exchange_rate import ExchangeRate
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Préfixe pour les clés Redis
CACHE_PREFIX = "irobot:exchange_rate:"

# TTL du cache (1 heure)
CACHE_TTL = 3600

# Taux par défaut (utilisé si aucune donnée disponible)
DEFAULT_USD_XAF_RATE = Decimal("655.957")


# =============================================================================
# EXCHANGE RATE SERVICE
# =============================================================================

class ExchangeRateService:
    """
    Service centralisé pour la gestion des taux de change.
    
    Utilise un cache Redis pour optimiser les performances.
    Les taux sont stockés dans la table exchange_rates.
    """
    
    _redis_client: Optional[redis.Redis] = None
    
    @classmethod
    def _get_redis(cls) -> Optional[redis.Redis]:
        """Récupère le client Redis (lazy init)."""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.from_url(
                    settings.REDIS_URL, 
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis non disponible: {e}")
        return cls._redis_client
    
    # =========================================================================
    # LECTURE DU TAUX DE CHANGE
    # =========================================================================
    
    @classmethod
    def get_current_rate(
        cls,
        db: Session,
        currency_from: str = "USD",
        currency_to: str = "XAF",
        use_cache: bool = True
    ) -> Decimal:
        """
        Récupère le taux de change actuel.
        
        Ordre de priorité:
        1. Cache Redis
        2. Base de données (dernier taux)
        3. Taux par défaut depuis config
        
        Args:
            db: Session database
            currency_from: Devise source (défaut: USD)
            currency_to: Devise cible (défaut: XAF)
            use_cache: Utiliser le cache Redis
            
        Returns:
            Taux de change (Decimal)
        """
        cache_key = f"{currency_from}_{currency_to}"
        
        # 1. Essayer le cache
        if use_cache:
            cached_rate = cls._get_from_cache(cache_key)
            if cached_rate is not None:
                return Decimal(str(cached_rate))
        
        # 2. Chercher dans la DB
        rate_record = db.query(ExchangeRate).filter(
            ExchangeRate.currency_from == currency_from,
            ExchangeRate.currency_to == currency_to
        ).order_by(desc(ExchangeRate.fetched_at)).first()
        
        if rate_record:
            rate = rate_record.rate
            
            # Mettre en cache
            if use_cache:
                cls._set_cache(cache_key, float(rate))
            
            return rate
        
        # 3. Fallback sur le taux par défaut
        logger.warning(
            f"Aucun taux {currency_from}/{currency_to} trouvé, "
            f"utilisation du taux par défaut"
        )
        
        default_rate = cls._get_default_rate(db, currency_from, currency_to)
        return default_rate
    
    @classmethod
    def get_rate_for_calculation(cls, db: Session) -> float:
        """
        Raccourci pour récupérer le taux USD/XAF pour les calculs de coût.
        
        Retourne un float pour faciliter les calculs.
        
        Args:
            db: Session database
            
        Returns:
            Taux de change (float)
        """
        rate = cls.get_current_rate(db, "USD", "XAF")
        return float(rate)
    
    @classmethod
    def _get_default_rate(
        cls,
        db: Session,
        currency_from: str,
        currency_to: str
    ) -> Decimal:
        """
        Récupère le taux par défaut depuis la config système.
        
        Args:
            db: Session database
            currency_from: Devise source
            currency_to: Devise cible
            
        Returns:
            Taux par défaut (Decimal)
        """
        # Essayer de récupérer depuis system_config
        try:
            from app.services.config_service import get_config_value
            
            config_key = f"exchange_rate.default_{currency_from.lower()}_{currency_to.lower()}"
            default_value = get_config_value(config_key, db, default=None)
            
            if default_value is not None:
                return Decimal(str(default_value))
        except Exception as e:
            logger.debug(f"Impossible de lire la config: {e}")
        
        # Fallback hardcodé
        if currency_from == "USD" and currency_to == "XAF":
            return DEFAULT_USD_XAF_RATE
        
        # Autres paires non supportées
        logger.error(f"Paire {currency_from}/{currency_to} non supportée")
        return Decimal("1.0")
    
    # =========================================================================
    # INFORMATIONS DÉTAILLÉES
    # =========================================================================
    
    @classmethod
    def get_rate_info(
        cls,
        db: Session,
        currency_from: str = "USD",
        currency_to: str = "XAF"
    ) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur le taux de change.
        
        Args:
            db: Session database
            currency_from: Devise source
            currency_to: Devise cible
            
        Returns:
            Dict avec rate, fetched_at, source, etc.
        """
        rate_record = db.query(ExchangeRate).filter(
            ExchangeRate.currency_from == currency_from,
            ExchangeRate.currency_to == currency_to
        ).order_by(desc(ExchangeRate.fetched_at)).first()
        
        if rate_record:
            # Calculer l'âge du taux
            age_hours = None
            if rate_record.fetched_at:
                age = datetime.utcnow() - rate_record.fetched_at
                age_hours = age.total_seconds() / 3600
            
            return {
                "currency_from": currency_from,
                "currency_to": currency_to,
                "rate": float(rate_record.rate),
                "fetched_at": rate_record.fetched_at.isoformat() if rate_record.fetched_at else None,
                "age_hours": round(age_hours, 2) if age_hours else None,
                "source": "database",
                "is_stale": age_hours > 48 if age_hours else True,
            }
        
        # Pas de données en DB
        default_rate = cls._get_default_rate(db, currency_from, currency_to)
        return {
            "currency_from": currency_from,
            "currency_to": currency_to,
            "rate": float(default_rate),
            "fetched_at": None,
            "age_hours": None,
            "source": "default",
            "is_stale": True,
        }
    
    @classmethod
    def get_rate_history(
        cls,
        db: Session,
        currency_from: str = "USD",
        currency_to: str = "XAF",
        days: int = 30,
        limit: int = 100
    ) -> list:
        """
        Récupère l'historique des taux de change.
        
        Args:
            db: Session database
            currency_from: Devise source
            currency_to: Devise cible
            days: Nombre de jours d'historique
            limit: Nombre maximum d'entrées
            
        Returns:
            Liste des taux historiques
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        records = db.query(ExchangeRate).filter(
            ExchangeRate.currency_from == currency_from,
            ExchangeRate.currency_to == currency_to,
            ExchangeRate.fetched_at >= cutoff
        ).order_by(desc(ExchangeRate.fetched_at)).limit(limit).all()
        
        return [
            {
                "rate": float(r.rate),
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in records
        ]
    
    # =========================================================================
    # CONVERSION
    # =========================================================================
    
    @classmethod
    def convert(
        cls,
        db: Session,
        amount: float,
        currency_from: str = "USD",
        currency_to: str = "XAF"
    ) -> Dict[str, Any]:
        """
        Convertit un montant d'une devise à une autre.
        
        Args:
            db: Session database
            amount: Montant à convertir
            currency_from: Devise source
            currency_to: Devise cible
            
        Returns:
            Dict avec le montant converti et le taux utilisé
        """
        rate = cls.get_current_rate(db, currency_from, currency_to)
        converted = Decimal(str(amount)) * rate
        
        return {
            "amount_from": amount,
            "currency_from": currency_from,
            "amount_to": float(converted.quantize(Decimal("0.01"))),
            "currency_to": currency_to,
            "rate": float(rate),
        }
    
    # =========================================================================
    # GESTION DU CACHE
    # =========================================================================
    
    @classmethod
    def _get_from_cache(cls, key: str) -> Optional[float]:
        """Récupère un taux depuis le cache Redis."""
        redis_client = cls._get_redis()
        if not redis_client:
            return None
        
        try:
            cached = redis_client.get(f"{CACHE_PREFIX}{key}")
            if cached:
                return float(cached)
        except Exception as e:
            logger.debug(f"Erreur cache get: {e}")
        
        return None
    
    @classmethod
    def _set_cache(cls, key: str, rate: float, ttl: int = CACHE_TTL):
        """Stocke un taux dans le cache Redis."""
        redis_client = cls._get_redis()
        if not redis_client:
            return
        
        try:
            redis_client.setex(f"{CACHE_PREFIX}{key}", ttl, str(rate))
        except Exception as e:
            logger.debug(f"Erreur cache set: {e}")
    
    @classmethod
    def invalidate_cache(cls, currency_from: str = "USD", currency_to: str = "XAF"):
        """Invalide le cache pour une paire de devises."""
        redis_client = cls._get_redis()
        if not redis_client:
            return
        
        try:
            key = f"{CACHE_PREFIX}{currency_from}_{currency_to}"
            redis_client.delete(key)
            logger.info(f"Cache invalidé pour {currency_from}/{currency_to}")
        except Exception as e:
            logger.debug(f"Erreur cache invalidate: {e}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_usd_xaf_rate(db: Session) -> float:
    """
    Raccourci pour récupérer le taux USD/XAF.
    
    Args:
        db: Session database
        
    Returns:
        Taux de change (float)
    """
    return ExchangeRateService.get_rate_for_calculation(db)


def convert_usd_to_xaf(db: Session, amount_usd: float) -> float:
    """
    Convertit un montant USD en XAF.
    
    Args:
        db: Session database
        amount_usd: Montant en USD
        
    Returns:
        Montant en XAF
    """
    result = ExchangeRateService.convert(db, amount_usd, "USD", "XAF")
    return result["amount_to"]