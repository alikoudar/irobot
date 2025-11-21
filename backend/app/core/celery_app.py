"""Celery application configuration."""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "irobot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.processing_tasks",
        "app.workers.chunking_tasks",
        "app.workers.embedding_tasks",
        "app.workers.indexing_tasks",
        "app.workers.periodic_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.processing_tasks.*": {"queue": "processing"},
        "app.workers.chunking_tasks.*": {"queue": "chunking"},
        "app.workers.embedding_tasks.*": {"queue": "embedding"},
        "app.workers.indexing_tasks.*": {"queue": "indexing"},
    },
    beat_schedule={
        "cleanup-expired-cache-daily": {
            "task": "app.workers.periodic_tasks.cleanup_expired_cache",
            "schedule": 86400.0,  # 24 hours
        },
        "update-exchange-rate-daily": {
            "task": "app.workers.periodic_tasks.update_exchange_rate",
            "schedule": 86400.0,  # 24 hours
        },
        "cleanup-old-logs": {
            "task": "app.workers.periodic_tasks.cleanup_old_logs",
            "schedule": 86400.0,  # 24 hours
        },
    },
)