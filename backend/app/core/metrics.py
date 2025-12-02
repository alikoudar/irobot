"""
Module de métriques Prometheus pour IroBot
Définit toutes les métriques custom utilisées dans les dashboards Grafana

Sprint 13 - Monitoring & Observabilité
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Optional

# =============================================================================
# MÉTRIQUES HTTP & API
# =============================================================================

# Compteur de requêtes HTTP
http_requests_total = Counter(
    'irobot_http_requests_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)

# Durée des requêtes HTTP
http_request_duration_seconds = Histogram(
    'irobot_http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# =============================================================================
# MÉTRIQUES CACHE
# =============================================================================

# Taux de hit du cache
cache_hit_rate = Gauge(
    'irobot_cache_hit_rate',
    'Taux de hit du cache (0-1)'
)

# Nombre d'entrées dans le cache
cache_entries_total = Gauge(
    'irobot_cache_entries_total',
    'Nombre total d\'entrées dans le cache'
)

# Compteur de hits/miss
cache_operations_total = Counter(
    'irobot_cache_operations_total',
    'Opérations de cache (hit/miss)',
    ['operation', 'level']  # operation: hit/miss, level: level1/level2
)

# =============================================================================
# MÉTRIQUES DOCUMENTS
# =============================================================================

# Total de documents indexés
documents_total = Gauge(
    'irobot_documents_total',
    'Nombre total de documents indexés'
)

# Documents par catégorie
documents_by_category = Gauge(
    'irobot_documents_by_category',
    'Nombre de documents par catégorie',
    ['category']
)

# Traitement de documents
document_processing_total = Counter(
    'irobot_document_processing_total',
    'Total de documents traités',
    ['status']  # completed, failed, processing
)

# Durée du traitement de documents
document_processing_duration_seconds = Histogram(
    'irobot_document_processing_duration_seconds',
    'Durée du traitement de documents en secondes',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800)
)

# Documents en échec
document_processing_failed_total = Counter(
    'irobot_document_processing_failed_total',
    'Total de documents en échec'
)

# =============================================================================
# MÉTRIQUES RAG PIPELINE
# =============================================================================

# Requêtes de recherche
search_requests_total = Counter(
    'irobot_search_requests_total',
    'Total des requêtes de recherche',
    ['search_type']  # bm25, semantic, hybrid
)

# Durée de recherche
search_duration_seconds = Histogram(
    'irobot_search_duration_seconds',
    'Durée de recherche en secondes',
    ['search_type'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Requêtes d'embedding
embedding_requests_total = Counter(
    'irobot_embedding_requests_total',
    'Total des requêtes d\'embedding',
    ['model']  # mistral-embed
)

# Durée d'embedding
embedding_duration_seconds = Histogram(
    'irobot_embedding_duration_seconds',
    'Durée de génération d\'embeddings en secondes',
    ['model'],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Requêtes de reranking
rerank_requests_total = Counter(
    'irobot_rerank_requests_total',
    'Total des requêtes de reranking',
    ['model']
)

# Durée de reranking
rerank_duration_seconds = Histogram(
    'irobot_rerank_duration_seconds',
    'Durée de reranking en secondes',
    ['model'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# =============================================================================
# MÉTRIQUES LLM
# =============================================================================

# Tokens consommés
llm_tokens_total = Counter(
    'irobot_llm_tokens_total',
    'Total de tokens consommés',
    ['operation', 'model']  # operation: input/output, model: mistral-small/medium/large
)

# Coût LLM en USD
llm_cost_usd_total = Counter(
    'irobot_llm_cost_usd_total',
    'Coût total LLM en USD',
    ['operation', 'model']
)

# Durée de génération LLM
llm_generation_duration_seconds = Histogram(
    'irobot_llm_generation_duration_seconds',
    'Durée de génération LLM en secondes',
    ['model'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0)
)

# Requêtes LLM
llm_requests_total = Counter(
    'irobot_llm_requests_total',
    'Total des requêtes LLM',
    ['operation', 'model']  # operation: chat, embedding, rerank
)

# =============================================================================
# MÉTRIQUES CELERY WORKERS
# =============================================================================

# Longueur des queues Celery
celery_queue_length = Gauge(
    'irobot_celery_queue_length',
    'Nombre de tâches en attente dans les queues Celery',
    ['queue']  # processing, chunking, embedding, indexing
)

# Tâches Celery par état
celery_tasks_total = Counter(
    'irobot_celery_tasks_total',
    'Total des tâches Celery',
    ['queue', 'status']  # status: success, failure
)

# Durée des tâches Celery
celery_task_duration_seconds = Histogram(
    'irobot_celery_task_duration_seconds',
    'Durée des tâches Celery en secondes',
    ['queue'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

# Tâches Celery en échec
celery_task_failed_total = Counter(
    'irobot_celery_task_failed_total',
    'Total des tâches Celery en échec'
)

# Workers Celery actifs
celery_workers_active = Gauge(
    'irobot_celery_workers_active',
    'Nombre de workers Celery actifs',
    ['queue']
)

# =============================================================================
# MÉTRIQUES UTILISATEURS
# =============================================================================

# Utilisateurs actifs
users_active_total = Gauge(
    'irobot_users_active_total',
    'Nombre d\'utilisateurs actifs (sessions actives dans les dernières 24h)'
)

# Utilisateurs par rôle
users_by_role = Gauge(
    'irobot_users_by_role',
    'Nombre d\'utilisateurs par rôle',
    ['role']  # admin, manager, user
)

# Connexions utilisateurs
user_logins_total = Counter(
    'irobot_user_logins_total',
    'Total des connexions utilisateurs',
    ['status']  # success, failed
)

# =============================================================================
# MÉTRIQUES WEAVIATE (VECTOR DATABASE)
# =============================================================================

# Nombre total d'objets dans Weaviate
weaviate_objects_total = Gauge(
    'irobot_weaviate_objects_total',
    'Nombre total d\'objets/vecteurs dans Weaviate',
    ['class_name']  # Document, Chunk, etc.
)

# Connexions actives à Weaviate
weaviate_connections_active = Gauge(
    'irobot_weaviate_connections_active',
    'Nombre de connexions actives à Weaviate'
)

# Durée des requêtes vectorielles Weaviate
weaviate_query_duration_seconds = Histogram(
    'irobot_weaviate_query_duration_seconds',
    'Durée des requêtes vectorielles Weaviate en secondes',
    ['operation'],  # search, insert, update, delete
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Opérations batch Weaviate
weaviate_batch_operations_total = Counter(
    'irobot_weaviate_batch_operations_total',
    'Total des opérations batch sur Weaviate',
    ['operation', 'status']  # operation: insert/update/delete, status: success/failure
)

# Erreurs Weaviate
weaviate_errors_total = Counter(
    'irobot_weaviate_errors_total',
    'Total des erreurs Weaviate',
    ['error_type']
)

# =============================================================================
# MÉTRIQUES REDIS (CACHE & BROKER CELERY)
# =============================================================================

# Clients connectés à Redis
redis_connected_clients = Gauge(
    'irobot_redis_connected_clients',
    'Nombre de clients connectés à Redis'
)

# Mémoire utilisée par Redis
redis_used_memory_bytes = Gauge(
    'irobot_redis_used_memory_bytes',
    'Mémoire utilisée par Redis en bytes'
)

# Mémoire max Redis
redis_max_memory_bytes = Gauge(
    'irobot_redis_max_memory_bytes',
    'Mémoire maximum configurée pour Redis en bytes'
)

# Commandes traitées par Redis
redis_commands_processed_total = Counter(
    'irobot_redis_commands_processed_total',
    'Total des commandes traitées par Redis',
    ['command']  # get, set, del, etc.
)

# Nombre de keys dans Redis
redis_keyspace_keys_total = Gauge(
    'irobot_redis_keyspace_keys_total',
    'Nombre total de keys dans Redis',
    ['db']  # db0, db1, etc.
)

# Hit/Miss ratio Redis
redis_keyspace_hits_total = Counter(
    'irobot_redis_keyspace_hits_total',
    'Total des hits sur le keyspace Redis'
)

redis_keyspace_misses_total = Counter(
    'irobot_redis_keyspace_misses_total',
    'Total des misses sur le keyspace Redis'
)

# Durée des commandes Redis
redis_command_duration_seconds = Histogram(
    'irobot_redis_command_duration_seconds',
    'Durée des commandes Redis en secondes',
    ['command'],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

# =============================================================================
# MÉTRIQUES POSTGRESQL (BASE DE DONNÉES PRINCIPALE)
# =============================================================================

# Connexions actives à PostgreSQL
postgres_connections_active = Gauge(
    'irobot_postgres_connections_active',
    'Nombre de connexions actives à PostgreSQL'
)

# Connexions maximum PostgreSQL
postgres_connections_max = Gauge(
    'irobot_postgres_connections_max',
    'Nombre maximum de connexions PostgreSQL configurées'
)

# Queries par seconde
postgres_queries_total = Counter(
    'irobot_postgres_queries_total',
    'Total des queries exécutées sur PostgreSQL',
    ['query_type']  # select, insert, update, delete
)

# Durée des queries PostgreSQL
postgres_query_duration_seconds = Histogram(
    'irobot_postgres_query_duration_seconds',
    'Durée des queries PostgreSQL en secondes',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

# Transactions PostgreSQL
postgres_transactions_total = Counter(
    'irobot_postgres_transactions_total',
    'Total des transactions PostgreSQL',
    ['status']  # commit, rollback
)

# Taille des tables principales
postgres_table_size_bytes = Gauge(
    'irobot_postgres_table_size_bytes',
    'Taille des tables PostgreSQL en bytes',
    ['table_name']  # users, documents, categories, etc.
)

# Dead tuples (pour vacuum monitoring)
postgres_dead_tuples = Gauge(
    'irobot_postgres_dead_tuples',
    'Nombre de dead tuples dans PostgreSQL',
    ['table_name']
)

# Locks PostgreSQL
postgres_locks_total = Gauge(
    'irobot_postgres_locks_total',
    'Nombre de locks actifs dans PostgreSQL',
    ['lock_type']  # AccessShareLock, RowExclusiveLock, etc.
)

# Cache hit ratio PostgreSQL
postgres_cache_hit_ratio = Gauge(
    'irobot_postgres_cache_hit_ratio',
    'Ratio de cache hit PostgreSQL (0-1)'
)

# =============================================================================
# MÉTRIQUES SYSTÈME
# =============================================================================

# Informations sur l'application
app_info = Info(
    'irobot_app',
    'Informations sur l\'application IroBot'
)

# Version de l'application
app_version = Gauge(
    'irobot_app_version',
    'Version de l\'application',
    ['version', 'environment']
)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def initialize_metrics():
    """
    Initialise les métriques avec des valeurs par défaut
    Appelé au démarrage de l'application
    """
    # Informations applicatives
    app_info.info({
        'name': 'IroBot',
        'description': 'RAG Chatbot pour BEAC',
        'version': '1.0.0'
    })
    
    # Version
    app_version.labels(version='1.0.0', environment='development').set(1)
    
    # Initialiser les gauges à 0
    cache_hit_rate.set(0)
    documents_total.set(0)
    users_active_total.set(0)
    
    # Initialiser les queues Celery à 0
    for queue in ['processing', 'chunking', 'embedding', 'indexing']:
        celery_queue_length.labels(queue=queue).set(0)
        celery_workers_active.labels(queue=queue).set(0)
    
    # Initialiser les métriques Weaviate
    weaviate_connections_active.set(0)
    for class_name in ['Document', 'Chunk']:
        weaviate_objects_total.labels(class_name=class_name).set(0)
    
    # Initialiser les métriques Redis
    redis_connected_clients.set(0)
    redis_used_memory_bytes.set(0)
    redis_max_memory_bytes.set(0)
    redis_keyspace_keys_total.labels(db='db0').set(0)
    
    # Initialiser les métriques PostgreSQL
    postgres_connections_active.set(0)
    postgres_connections_max.set(100)  # Valeur par défaut
    postgres_cache_hit_ratio.set(0)


def update_cache_hit_rate(rate: float):
    """
    Met à jour le taux de hit du cache
    
    Args:
        rate: Taux de hit du cache (0.0 à 1.0)
    """
    cache_hit_rate.set(rate)


def update_cache_entries_total(count: int):
    """
    Met à jour le nombre total d'entrées dans le cache
    
    Args:
        count: Nombre total d'entrées dans le cache
    """
    cache_entries_total.set(count)


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """
    Enregistre une requête HTTP
    
    Args:
        method: Méthode HTTP (GET, POST, etc.)
        endpoint: Endpoint appelé
        status_code: Code de statut HTTP
        duration: Durée de la requête en secondes
    """
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def record_cache_operation(operation: str, level: str):
    """
    Enregistre une opération de cache
    
    Args:
        operation: Type d'opération (hit, miss)
        level: Niveau de cache (level1, level2)
    """
    cache_operations_total.labels(
        operation=operation,
        level=level
    ).inc()


def record_document_processing(status: str, duration: Optional[float] = None):
    """
    Enregistre le traitement d'un document
    
    Args:
        status: Statut du traitement (completed, failed, processing)
        duration: Durée du traitement en secondes (optionnel)
    """
    document_processing_total.labels(status=status).inc()
    
    if status == 'failed':
        document_processing_failed_total.inc()
    
    if duration is not None:
        document_processing_duration_seconds.observe(duration)


def record_search_request(search_type: str, duration: float):
    """
    Enregistre une requête de recherche
    
    Args:
        search_type: Type de recherche (bm25, semantic, hybrid)
        duration: Durée de la recherche en secondes
    """
    search_requests_total.labels(search_type=search_type).inc()
    search_duration_seconds.labels(search_type=search_type).observe(duration)


def record_embedding_request(model: str, duration: float):
    """
    Enregistre une requête d'embedding
    
    Args:
        model: Modèle utilisé
        duration: Durée en secondes
    """
    embedding_requests_total.labels(model=model).inc()
    embedding_duration_seconds.labels(model=model).observe(duration)


def record_rerank_request(model: str, duration: float):
    """
    Enregistre une requête de reranking
    
    Args:
        model: Modèle utilisé
        duration: Durée en secondes
    """
    rerank_requests_total.labels(model=model).inc()
    rerank_duration_seconds.labels(model=model).observe(duration)


def record_llm_request(operation: str, model: str, input_tokens: int, 
                       output_tokens: int, cost_usd: float, duration: float):
    """
    Enregistre une requête LLM complète
    
    Args:
        operation: Type d'opération (chat, embedding, rerank)
        model: Modèle utilisé
        input_tokens: Tokens en entrée
        output_tokens: Tokens en sortie
        cost_usd: Coût en USD
        duration: Durée en secondes
    """
    llm_requests_total.labels(operation=operation, model=model).inc()
    
    llm_tokens_total.labels(operation='input', model=model).inc(input_tokens)
    llm_tokens_total.labels(operation='output', model=model).inc(output_tokens)
    
    llm_cost_usd_total.labels(operation=operation, model=model).inc(cost_usd)
    
    llm_generation_duration_seconds.labels(model=model).observe(duration)


def record_celery_task(queue: str, duration: float, status: str):
    """
    Enregistre une tâche Celery
    
    Args:
        queue: Queue Celery (processing, chunking, embedding, indexing)
        duration: Durée de la tâche en secondes
        status: État de la tâche (success, failure)
    """
    celery_tasks_total.labels(queue=queue, status=status).inc()
    
    if status == 'failure':
        celery_task_failed_total.inc()
    
    celery_task_duration_seconds.labels(queue=queue).observe(duration)


def update_celery_queue_length(queue: str, length: int):
    """
    Met à jour la longueur d'une queue Celery
    
    Args:
        queue: Nom de la queue
        length: Nombre de tâches en attente
    """
    celery_queue_length.labels(queue=queue).set(length)


def update_celery_workers_active(queue: str, count: int):
    """
    Met à jour le nombre de workers actifs
    
    Args:
        queue: Nom de la queue
        count: Nombre de workers actifs
    """
    celery_workers_active.labels(queue=queue).set(count)


def update_documents_total(count: int):
    """
    Met à jour le nombre total de documents
    
    Args:
        count: Nombre total de documents
    """
    documents_total.set(count)


def update_documents_by_category(category: str, count: int):
    """
    Met à jour le nombre de documents par catégorie
    
    Args:
        category: Nom de la catégorie
        count: Nombre de documents
    """
    documents_by_category.labels(category=category).set(count)


def update_users_active_total(count: int):
    """
    Met à jour le nombre d'utilisateurs actifs
    
    Args:
        count: Nombre d'utilisateurs actifs
    """
    users_active_total.set(count)


def update_users_by_role(role: str, count: int):
    """
    Met à jour le nombre d'utilisateurs par rôle
    
    Args:
        role: Rôle (admin, manager, user)
        count: Nombre d'utilisateurs
    """
    users_by_role.labels(role=role).set(count)


def record_user_login(status: str):
    """
    Enregistre une connexion utilisateur
    
    Args:
        status: Statut (success, failed)
    """
    user_logins_total.labels(status=status).inc()


# =============================================================================
# FONCTIONS UTILITAIRES WEAVIATE
# =============================================================================

def update_weaviate_objects_total(class_name: str, count: int):
    """
    Met à jour le nombre total d'objets dans Weaviate
    
    Args:
        class_name: Nom de la classe Weaviate (Document, Chunk, etc.)
        count: Nombre d'objets
    """
    weaviate_objects_total.labels(class_name=class_name).set(count)


def update_weaviate_connections_active(count: int):
    """
    Met à jour le nombre de connexions actives à Weaviate
    
    Args:
        count: Nombre de connexions actives
    """
    weaviate_connections_active.set(count)


def record_weaviate_query(operation: str, duration: float):
    """
    Enregistre une requête Weaviate
    
    Args:
        operation: Type d'opération (search, insert, update, delete)
        duration: Durée en secondes
    """
    weaviate_query_duration_seconds.labels(operation=operation).observe(duration)


def record_weaviate_batch_operation(operation: str, status: str, count: int = 1):
    """
    Enregistre une opération batch Weaviate
    
    Args:
        operation: Type d'opération (insert, update, delete)
        status: Statut (success, failure)
        count: Nombre d'opérations
    """
    weaviate_batch_operations_total.labels(
        operation=operation,
        status=status
    ).inc(count)


def record_weaviate_error(error_type: str):
    """
    Enregistre une erreur Weaviate
    
    Args:
        error_type: Type d'erreur
    """
    weaviate_errors_total.labels(error_type=error_type).inc()


# =============================================================================
# FONCTIONS UTILITAIRES REDIS
# =============================================================================

def update_redis_metrics(info: dict):
    """
    Met à jour les métriques Redis à partir du résultat de INFO
    
    Args:
        info: Dictionnaire retourné par Redis INFO command
    """
    # Clients connectés
    if 'connected_clients' in info:
        redis_connected_clients.set(info['connected_clients'])
    
    # Mémoire
    if 'used_memory' in info:
        redis_used_memory_bytes.set(info['used_memory'])
    if 'maxmemory' in info:
        redis_max_memory_bytes.set(info['maxmemory'])
    
    # Keyspace hits/misses
    if 'keyspace_hits' in info:
        redis_keyspace_hits_total.inc(info['keyspace_hits'])
    if 'keyspace_misses' in info:
        redis_keyspace_misses_total.inc(info['keyspace_misses'])


def update_redis_keyspace_keys(db: str, count: int):
    """
    Met à jour le nombre de keys dans une database Redis
    
    Args:
        db: Nom de la database (db0, db1, etc.)
        count: Nombre de keys
    """
    redis_keyspace_keys_total.labels(db=db).set(count)


def record_redis_command(command: str, duration: float):
    """
    Enregistre une commande Redis
    
    Args:
        command: Nom de la commande (GET, SET, DEL, etc.)
        duration: Durée en secondes
    """
    redis_commands_processed_total.labels(command=command).inc()
    redis_command_duration_seconds.labels(command=command).observe(duration)


# =============================================================================
# FONCTIONS UTILITAIRES POSTGRESQL
# =============================================================================

def update_postgres_connections(active: int, max_connections: int):
    """
    Met à jour les métriques de connexions PostgreSQL
    
    Args:
        active: Nombre de connexions actives
        max_connections: Nombre maximum de connexions configurées
    """
    postgres_connections_active.set(active)
    postgres_connections_max.set(max_connections)


def record_postgres_query(query_type: str, duration: float):
    """
    Enregistre une query PostgreSQL
    
    Args:
        query_type: Type de query (select, insert, update, delete)
        duration: Durée en secondes
    """
    postgres_queries_total.labels(query_type=query_type).inc()
    postgres_query_duration_seconds.labels(query_type=query_type).observe(duration)


def record_postgres_transaction(status: str):
    """
    Enregistre une transaction PostgreSQL
    
    Args:
        status: Statut (commit, rollback)
    """
    postgres_transactions_total.labels(status=status).inc()


def update_postgres_table_size(table_name: str, size_bytes: int):
    """
    Met à jour la taille d'une table PostgreSQL
    
    Args:
        table_name: Nom de la table
        size_bytes: Taille en bytes
    """
    postgres_table_size_bytes.labels(table_name=table_name).set(size_bytes)


def update_postgres_dead_tuples(table_name: str, count: int):
    """
    Met à jour le nombre de dead tuples pour une table
    
    Args:
        table_name: Nom de la table
        count: Nombre de dead tuples
    """
    postgres_dead_tuples.labels(table_name=table_name).set(count)


def update_postgres_locks(lock_type: str, count: int):
    """
    Met à jour le nombre de locks PostgreSQL
    
    Args:
        lock_type: Type de lock
        count: Nombre de locks
    """
    postgres_locks_total.labels(lock_type=lock_type).set(count)


def update_postgres_cache_hit_ratio(ratio: float):
    """
    Met à jour le ratio de cache hit PostgreSQL
    
    Args:
        ratio: Ratio entre 0 et 1
    """
    postgres_cache_hit_ratio.set(ratio)