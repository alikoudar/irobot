"""Periodic tasks - Placeholder for Sprint 5."""
import logging
from datetime import datetime

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.periodic_tasks.cleanup_expired_cache")
def cleanup_expired_cache():
    """
    Nettoie les entrées de cache expirées.
    
    Cette task sera implémentée dans le Sprint 5 - Phase 4.
    Scheduled: Tous les jours (86400s)
    """
    logger.info("Cleanup expired cache task called (not yet implemented)")
    # TODO: Implémenter dans Sprint 5
    pass


@celery_app.task(name="app.workers.periodic_tasks.update_exchange_rate")
def update_exchange_rate():
    """
    Met à jour le taux de change USD -> XAF.
    
    Cette task sera implémentée dans le Sprint 5 - Phase 4.
    Scheduled: Tous les jours (86400s)
    """
    logger.info("Update exchange rate task called (not yet implemented)")
    # TODO: Implémenter dans Sprint 5
    pass


@celery_app.task(name="app.workers.periodic_tasks.cleanup_old_logs")
def cleanup_old_logs():
    """
    Nettoie les logs de plus de 90 jours.
    
    Cette task sera implémentée dans le Sprint 5 - Phase 4.
    Scheduled: Tous les jours (86400s)
    """
    logger.info("Cleanup old logs task called (not yet implemented)")
    # TODO: Implémenter dans Sprint 5
    pass