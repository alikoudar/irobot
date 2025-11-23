"""
Configuration du Celery Beat Schedule.

À ajouter dans celery_app.py ou à importer.
"""
from celery.schedules import crontab


# =============================================================================
# BEAT SCHEDULE - TÂCHES PÉRIODIQUES
# =============================================================================

CELERY_BEAT_SCHEDULE = {
    # Mise à jour du taux de change tous les jours à 1h du matin (UTC)
    "update-exchange-rate-daily": {
        "task": "app.workers.periodic_tasks.update_exchange_rate",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "default"},
    },
    
    # Nettoyage du cache expiré tous les jours à 3h du matin
    "cleanup-expired-cache-daily": {
        "task": "app.workers.periodic_tasks.cleanup_expired_cache",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },
    
    # Nettoyage des vieux logs tous les jours à 4h du matin
    "cleanup-old-logs-daily": {
        "task": "app.workers.periodic_tasks.cleanup_old_logs",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "default"},
    },
    
    # Health check toutes les 5 minutes (optionnel, pour monitoring)
    "health-check-5min": {
        "task": "app.workers.periodic_tasks.health_check",
        "schedule": 300.0,  # 5 minutes en secondes
        "options": {"queue": "default"},
    },
}


# =============================================================================
# INSTRUCTIONS D'INTÉGRATION
# =============================================================================
"""
Pour intégrer ce schedule dans celery_app.py, ajouter:

from app.workers.celery_beat_schedule import CELERY_BEAT_SCHEDULE

celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
celery_app.conf.timezone = 'UTC'

Ou directement dans la configuration de l'app:

celery_app.conf.update(
    beat_schedule=CELERY_BEAT_SCHEDULE,
    timezone='UTC',
)

Pour lancer le beat scheduler:

    celery -A app.core.celery_app beat --loglevel=info

Ou avec le worker (pour dev):

    celery -A app.core.celery_app worker --beat --loglevel=info
"""