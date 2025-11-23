"""
Tâches périodiques Celery.

Ces tâches s'exécutent automatiquement selon le schedule défini dans celery_app.py:
- update_exchange_rate: Tous les jours à minuit
- cleanup_expired_cache: Tous les jours à 3h
- cleanup_old_logs: Tous les jours à 4h
"""
import logging
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# URL de l'API Exchange Rate (v6 avec pair)
EXCHANGE_RATE_API_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"

# Timeout pour les requêtes HTTP
HTTP_TIMEOUT = 15.0

# Durée de rétention des logs (jours)
LOG_RETENTION_DAYS = 90

# Durée de rétention du cache expiré (heures)
CACHE_CLEANUP_HOURS = 24


# =============================================================================
# UPDATE EXCHANGE RATE
# =============================================================================

@celery_app.task(
    name="app.workers.periodic_tasks.update_exchange_rate",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def update_exchange_rate(self) -> Dict[str, Any]:
    """
    Met à jour le taux de change USD/XAF depuis l'API externe.
    
    Appelle l'API exchangerate-api.com et sauvegarde le taux dans la DB.
    En cas d'échec, utilise le dernier taux connu.
    
    Schedule: Tous les jours (86400 secondes)
    
    Returns:
        Dict avec le résultat de la mise à jour
    """
    from app.models.exchange_rate import ExchangeRate
    from app.services.config_service import get_config_service
    
    db = SessionLocal()
    
    try:
        # Vérifier si l'API est activée
        config_service = get_config_service()
        api_enabled = config_service.get_value(
            "exchange_rate.api_enabled", 
            db, 
            default=True
        )
        
        if not api_enabled:
            logger.info("Mise à jour du taux de change désactivée dans la config")
            return {
                "status": "skipped",
                "reason": "API disabled in config"
            }
        
        # Récupérer la clé API
        api_key = settings.EXCHANGE_RATE_API_KEY
        
        if not api_key:
            logger.warning("EXCHANGE_RATE_API_KEY non configurée")
            return {
                "status": "error",
                "reason": "API key not configured"
            }
        
        # Construire l'URL
        url = EXCHANGE_RATE_API_URL.format(
            api_key=api_key,
            from_currency="USD",
            to_currency="XAF"
        )
        
        # Appeler l'API
        logger.info("Appel API Exchange Rate...")
        
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        # Vérifier le résultat
        if data.get("result") != "success":
            error_type = data.get("error-type", "unknown")
            logger.error(f"API Exchange Rate erreur: {error_type}")
            raise Exception(f"API error: {error_type}")
        
        # Extraire le taux
        rate = data.get("conversion_rate")
        if not rate:
            raise Exception("Taux de conversion non trouvé dans la réponse")
        
        # Parser la date de mise à jour
        time_last_update = data.get("time_last_update_utc")
        if time_last_update:
            try:
                # Format: "Sun, 23 Nov 2025 00:00:01 +0000"
                fetched_at = datetime.strptime(
                    time_last_update,
                    "%a, %d %b %Y %H:%M:%S %z"
                ).replace(tzinfo=None)
            except ValueError:
                fetched_at = datetime.utcnow()
        else:
            fetched_at = datetime.utcnow()
        
        # Sauvegarder en base
        exchange_rate = ExchangeRate(
            currency_from="USD",
            currency_to="XAF",
            rate=Decimal(str(rate)),
            fetched_at=fetched_at
        )
        db.add(exchange_rate)
        db.commit()
        
        logger.info(f"Taux USD/XAF mis à jour: {rate}")
        
        return {
            "status": "success",
            "rate": rate,
            "currency_from": "USD",
            "currency_to": "XAF",
            "fetched_at": fetched_at.isoformat(),
            "api_update_time": time_last_update
        }
        
    except httpx.TimeoutException:
        logger.error("Timeout lors de l'appel API Exchange Rate")
        return {
            "status": "error",
            "reason": "API timeout"
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP {e.response.status_code}")
        return {
            "status": "error",
            "reason": f"HTTP {e.response.status_code}"
        }
    except Exception as e:
        logger.error(f"Erreur mise à jour taux de change: {e}")
        
        # Retry si possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "status": "error",
            "reason": str(e)
        }
    finally:
        db.close()


# =============================================================================
# CLEANUP EXPIRED CACHE
# =============================================================================

@celery_app.task(name="app.workers.periodic_tasks.cleanup_expired_cache")
def cleanup_expired_cache() -> Dict[str, Any]:
    """
    Nettoie les entrées de cache expirées dans la table query_cache.
    
    Supprime les entrées dont expires_at < now().
    
    Schedule: Tous les jours (86400 secondes)
    
    Returns:
        Dict avec le nombre d'entrées supprimées
    """
    from app.models.query_cache import QueryCache
    
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Compter avant suppression
        expired_count = db.query(QueryCache).filter(
            QueryCache.expires_at < now
        ).count()
        
        if expired_count == 0:
            logger.info("Aucune entrée de cache expirée à nettoyer")
            return {
                "status": "success",
                "deleted_count": 0
            }
        
        # Supprimer les entrées expirées
        db.query(QueryCache).filter(
            QueryCache.expires_at < now
        ).delete(synchronize_session=False)
        
        db.commit()
        
        logger.info(f"Cache nettoyé: {expired_count} entrées expirées supprimées")
        
        return {
            "status": "success",
            "deleted_count": expired_count,
            "cleanup_time": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur nettoyage cache: {e}")
        db.rollback()
        return {
            "status": "error",
            "reason": str(e)
        }
    finally:
        db.close()


# =============================================================================
# CLEANUP OLD LOGS
# =============================================================================

@celery_app.task(name="app.workers.periodic_tasks.cleanup_old_logs")
def cleanup_old_logs() -> Dict[str, Any]:
    """
    Nettoie les anciens logs de la table audit_logs et token_usage.
    
    Supprime les entrées de plus de 90 jours (configurable).
    
    Schedule: Tous les jours (86400 secondes)
    
    Returns:
        Dict avec les statistiques de nettoyage
    """
    from app.models.audit_log import AuditLog
    from app.models.token_usage import TokenUsage
    
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=LOG_RETENTION_DAYS)
        
        results = {
            "status": "success",
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": LOG_RETENTION_DAYS,
            "deleted": {}
        }
        
        # Nettoyer audit_logs
        try:
            audit_count = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).count()
            
            if audit_count > 0:
                db.query(AuditLog).filter(
                    AuditLog.created_at < cutoff_date
                ).delete(synchronize_session=False)
                results["deleted"]["audit_logs"] = audit_count
                logger.info(f"Supprimé {audit_count} audit_logs anciens")
        except Exception as e:
            logger.warning(f"Erreur nettoyage audit_logs: {e}")
            results["deleted"]["audit_logs"] = f"error: {e}"
        
        # Nettoyer token_usage (garder plus longtemps pour analytics)
        # On garde 180 jours pour token_usage
        token_cutoff = datetime.utcnow() - timedelta(days=180)
        
        try:
            token_count = db.query(TokenUsage).filter(
                TokenUsage.created_at < token_cutoff
            ).count()
            
            if token_count > 0:
                db.query(TokenUsage).filter(
                    TokenUsage.created_at < token_cutoff
                ).delete(synchronize_session=False)
                results["deleted"]["token_usage"] = token_count
                logger.info(f"Supprimé {token_count} token_usage anciens")
        except Exception as e:
            logger.warning(f"Erreur nettoyage token_usage: {e}")
            results["deleted"]["token_usage"] = f"error: {e}"
        
        db.commit()
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur nettoyage logs: {e}")
        db.rollback()
        return {
            "status": "error",
            "reason": str(e)
        }
    finally:
        db.close()


# =============================================================================
# HEALTH CHECK TASK
# =============================================================================

@celery_app.task(name="app.workers.periodic_tasks.health_check")
def health_check() -> Dict[str, Any]:
    """
    Vérifie la santé des services (DB, Redis, Weaviate).
    
    Peut être utilisé pour le monitoring.
    
    Returns:
        Dict avec le status de chaque service
    """
    import redis
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        results["services"]["postgresql"] = "healthy"
    except Exception as e:
        results["services"]["postgresql"] = f"unhealthy: {e}"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        results["services"]["redis"] = "healthy"
    except Exception as e:
        results["services"]["redis"] = f"unhealthy: {e}"
    
    # Check Weaviate
    try:
        import httpx
        response = httpx.get(f"{settings.WEAVIATE_URL}/v1/.well-known/ready", timeout=5)
        if response.status_code == 200:
            results["services"]["weaviate"] = "healthy"
        else:
            results["services"]["weaviate"] = f"unhealthy: HTTP {response.status_code}"
    except Exception as e:
        results["services"]["weaviate"] = f"unhealthy: {e}"
    
    # Status global
    all_healthy = all(
        v == "healthy" 
        for v in results["services"].values()
    )
    results["status"] = "healthy" if all_healthy else "degraded"
    
    return results