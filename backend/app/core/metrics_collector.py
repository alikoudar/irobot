"""
Metrics Collector - Collecte périodique des métriques infrastructure.

Cette tâche Celery Beat s'exécute toutes les 30 secondes pour collecter :
- Métriques Redis (memory, clients, keys)
- Métriques PostgreSQL (connexions, taille DB, transactions)
- Métriques Weaviate (nombre d'objets)
- Métriques Celery (queue length, workers actifs)

SPRINT 13 - MONITORING: Job périodique pour mise à jour des gauges Prometheus
"""
import logging
import redis
from typing import Dict, Any
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal

# Import des fonctions de mise à jour des métriques
from app.core.metrics import (
    update_redis_memory_used,
    update_redis_memory_max,
    update_redis_connected_clients,
    update_redis_keys_total,
    update_postgres_connections_total,
    update_postgres_connections_active,
    update_postgres_database_size,
    update_postgres_transactions_total,
    update_celery_queue_length,
    update_celery_workers_active,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Intervalle de collecte (secondes)
COLLECTION_INTERVAL = 30

# Timeout pour les connexions
CONNECTION_TIMEOUT = 5


# =============================================================================
# MAIN COLLECTOR TASK
# =============================================================================

@celery_app.task(
    name="app.core.metrics_collector.collect_infrastructure_metrics",
    bind=True
)
def collect_infrastructure_metrics(self) -> Dict[str, Any]:
    """
    Collecte les métriques d'infrastructure et met à jour les gauges Prometheus.
    
    S'exécute toutes les 30 secondes via Celery Beat.
    
    Returns:
        Dict avec les statistiques de collecte
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "collected": {},
        "errors": {}
    }
    
    # Collecter Redis
    try:
        redis_metrics = collect_redis_metrics()
        results["collected"]["redis"] = redis_metrics
    except Exception as e:
        logger.error(f"Erreur collecte métriques Redis: {e}")
        results["errors"]["redis"] = str(e)
    
    # Collecter PostgreSQL
    try:
        postgres_metrics = collect_postgres_metrics()
        results["collected"]["postgres"] = postgres_metrics
    except Exception as e:
        logger.error(f"Erreur collecte métriques PostgreSQL: {e}")
        results["errors"]["postgres"] = str(e)
    
    # Collecter Weaviate
    try:
        weaviate_metrics = collect_weaviate_metrics()
        results["collected"]["weaviate"] = weaviate_metrics
    except Exception as e:
        logger.error(f"Erreur collecte métriques Weaviate: {e}")
        results["errors"]["weaviate"] = str(e)
    
    # Collecter Celery
    try:
        celery_metrics = collect_celery_metrics()
        results["collected"]["celery"] = celery_metrics
    except Exception as e:
        logger.error(f"Erreur collecte métriques Celery: {e}")
        results["errors"]["celery"] = str(e)
    
    # Log résumé
    total_collected = len(results["collected"])
    total_errors = len(results["errors"])
    
    if total_errors == 0:
        logger.debug(f"Métriques collectées avec succès: {total_collected} sources")
    else:
        logger.warning(
            f"Métriques collectées: {total_collected} sources, "
            f"{total_errors} erreurs"
        )
    
    return results


# =============================================================================
# REDIS METRICS COLLECTOR
# =============================================================================

def collect_redis_metrics() -> Dict[str, Any]:
    """
    Collecte les métriques Redis via la commande INFO.
    
    Returns:
        Dict avec les métriques Redis collectées
    """
    try:
        # Connexion à Redis
        r = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=CONNECTION_TIMEOUT,
            socket_timeout=CONNECTION_TIMEOUT
        )
        
        # Récupérer les informations
        info = r.info()
        
        # Memory
        memory_used = info.get('used_memory', 0)
        memory_max = info.get('maxmemory', 0)
        
        # Si maxmemory = 0, utiliser used_memory_rss comme approximation
        if memory_max == 0:
            memory_max = info.get('used_memory_rss', memory_used * 2)
        
        # Clients
        connected_clients = info.get('connected_clients', 0)
        
        # Keys (somme de tous les db)
        total_keys = 0
        for key, value in info.items():
            if key.startswith('db'):
                # Format: db0={'keys': 123, 'expires': 45}
                if isinstance(value, dict):
                    total_keys += value.get('keys', 0)
        
        # Mettre à jour les métriques Prometheus
        update_redis_memory_used(memory_used)
        update_redis_memory_max(memory_max)
        update_redis_connected_clients(connected_clients)
        update_redis_keys_total(total_keys)
        
        logger.debug(
            f"Redis: Memory={memory_used}/{memory_max} bytes, "
            f"Clients={connected_clients}, Keys={total_keys}"
        )
        
        return {
            "memory_used_bytes": memory_used,
            "memory_max_bytes": memory_max,
            "connected_clients": connected_clients,
            "keys_total": total_keys,
            "status": "success"
        }
        
    except redis.ConnectionError as e:
        logger.error(f"Impossible de se connecter à Redis: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la collecte Redis: {e}")
        raise


# =============================================================================
# POSTGRESQL METRICS COLLECTOR
# =============================================================================

def collect_postgres_metrics() -> Dict[str, Any]:
    """
    Collecte les métriques PostgreSQL via pg_stat_database.
    
    Returns:
        Dict avec les métriques PostgreSQL collectées
    """
    db = SessionLocal()
    
    try:
        # Récupérer le nom de la base de données
        db_name = settings.POSTGRES_DB
        
        # Requête pour les statistiques de la base de données
        query = """
        SELECT
            numbackends as connections_total,
            xact_commit + xact_rollback as transactions_total,
            pg_database_size(datname) as database_size_bytes
        FROM pg_stat_database
        WHERE datname = :db_name
        """
        
        result = db.execute(query, {"db_name": db_name}).fetchone()
        
        if result:
            connections_total = result[0] or 0
            transactions_total = result[1] or 0
            database_size = result[2] or 0
            
            # Requête pour les connexions actives
            active_query = """
            SELECT COUNT(*) as active_connections
            FROM pg_stat_activity
            WHERE state = 'active' AND datname = :db_name
            """
            
            active_result = db.execute(active_query, {"db_name": db_name}).fetchone()
            connections_active = active_result[0] if active_result else 0
            
            # Mettre à jour les métriques Prometheus
            update_postgres_connections_total(connections_total)
            update_postgres_connections_active(connections_active)
            update_postgres_database_size(database_size)
            update_postgres_transactions_total(transactions_total)
            
            logger.debug(
                f"PostgreSQL: Connections={connections_active}/{connections_total}, "
                f"Size={database_size} bytes, Transactions={transactions_total}"
            )
            
            return {
                "connections_total": connections_total,
                "connections_active": connections_active,
                "database_size_bytes": database_size,
                "transactions_total": transactions_total,
                "status": "success"
            }
        else:
            logger.warning(f"Aucune statistique trouvée pour la base {db_name}")
            return {
                "status": "no_data",
                "database": db_name
            }
            
    except Exception as e:
        logger.error(f"Erreur lors de la collecte PostgreSQL: {e}")
        raise
    finally:
        db.close()


# =============================================================================
# WEAVIATE METRICS COLLECTOR
# =============================================================================

def collect_weaviate_metrics() -> Dict[str, Any]:
    """
    Collecte les métriques Weaviate (nombre d'objets).
    
    Returns:
        Dict avec les métriques Weaviate collectées
    """
    try:
        from app.clients.weaviate_client import get_weaviate_client
        
        weaviate_client = get_weaviate_client()
        
        try:
            # Appeler la méthode qui met à jour automatiquement la métrique
            # (définie dans weaviate_client.py - Étape 4.2)
            total_objects = weaviate_client.get_total_objects_count()
            
            logger.debug(f"Weaviate: Total objects={total_objects}")
            
            return {
                "total_objects": total_objects,
                "collection": "DocumentChunk",
                "status": "success"
            }
            
        finally:
            weaviate_client.close()
            
    except Exception as e:
        logger.error(f"Erreur lors de la collecte Weaviate: {e}")
        raise


# =============================================================================
# CELERY METRICS COLLECTOR
# =============================================================================

def collect_celery_metrics() -> Dict[str, Any]:
    """
    Collecte les métriques Celery (queue length, workers actifs).
    
    Returns:
        Dict avec les métriques Celery collectées
    """
    try:
        from celery import current_app
        
        # Récupérer l'instance Celery
        app = current_app
        
        # Récupérer les statistiques des workers
        inspect = app.control.inspect()
        
        # Workers actifs
        stats = inspect.stats()
        active_workers = len(stats) if stats else 0
        
        update_celery_workers_active(active_workers)
        
        # Queue lengths
        # Note: Celery ne fournit pas directement la longueur des queues
        # On peut l'obtenir via Redis (broker)
        queue_lengths = {}
        
        try:
            r = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=CONNECTION_TIMEOUT
            )
            
            # Les queues Celery dans Redis ont le format: celery (default), chunking, embedding, indexing
            queues = ["celery", "chunking", "embedding", "indexing"]
            
            for queue in queues:
                # Dans Redis, les messages sont dans des listes avec la clé queue_name
                queue_key = queue
                length = r.llen(queue_key)
                queue_lengths[queue] = length
                
                # Mettre à jour la métrique
                update_celery_queue_length(queue, length)
        
        except Exception as e:
            logger.warning(f"Impossible de récupérer les longueurs de queue: {e}")
        
        logger.debug(
            f"Celery: Workers={active_workers}, "
            f"Queues={queue_lengths}"
        )
        
        return {
            "workers_active": active_workers,
            "queue_lengths": queue_lengths,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la collecte Celery: {e}")
        raise


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def test_metrics_collection() -> Dict[str, Any]:
    """
    Fonction helper pour tester la collecte des métriques manuellement.
    
    Utile pour le debugging.
    
    Returns:
        Dict avec les résultats de tous les collecteurs
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {}
    }
    
    # Test Redis
    try:
        results["tests"]["redis"] = collect_redis_metrics()
    except Exception as e:
        results["tests"]["redis"] = {"error": str(e)}
    
    # Test PostgreSQL
    try:
        results["tests"]["postgres"] = collect_postgres_metrics()
    except Exception as e:
        results["tests"]["postgres"] = {"error": str(e)}
    
    # Test Weaviate
    try:
        results["tests"]["weaviate"] = collect_weaviate_metrics()
    except Exception as e:
        results["tests"]["weaviate"] = {"error": str(e)}
    
    # Test Celery
    try:
        results["tests"]["celery"] = collect_celery_metrics()
    except Exception as e:
        results["tests"]["celery"] = {"error": str(e)}
    
    return results