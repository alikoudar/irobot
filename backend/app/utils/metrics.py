"""
Module de métriques Prometheus pour IroBot.

Ce module fournit des métriques custom pour monitorer :
- Requêtes HTTP
- Pipeline RAG (documents, embeddings, recherche, génération)
- Cache
- Tokens LLM et coûts
- Celery workers
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable

# ==================== MÉTRIQUES HTTP ====================

http_requests_total = Counter(
    'irobot_http_requests_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'irobot_http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# ==================== MÉTRIQUES CACHE ====================

cache_hit_rate = Gauge(
    'irobot_cache_hit_rate',
    'Taux de hit du cache (0-1)'
)

cache_hits_total = Counter(
    'irobot_cache_hits_total',
    'Total des hits de cache',
    ['cache_level']  # L1 (exact) ou L2 (semantic)
)

cache_misses_total = Counter(
    'irobot_cache_misses_total',
    'Total des misses de cache'
)

cache_tokens_saved = Counter(
    'irobot_cache_tokens_saved_total',
    'Tokens économisés grâce au cache'
)

cache_cost_saved_usd = Counter(
    'irobot_cache_cost_saved_usd_total',
    'Coût économisé en USD grâce au cache'
)

# ==================== MÉTRIQUES DOCUMENTS ====================

documents_total = Gauge(
    'irobot_documents_total',
    'Nombre total de documents'
)

document_processing_total = Counter(
    'irobot_document_processing_total',
    'Total des documents traités',
    ['status']  # pending, processing, completed, failed
)

document_processing_duration_seconds = Histogram(
    'irobot_document_processing_duration_seconds',
    'Durée du traitement de documents en secondes',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

chunks_created_total = Counter(
    'irobot_chunks_created_total',
    'Total des chunks créés'
)

# ==================== MÉTRIQUES RAG PIPELINE ====================

embedding_requests_total = Counter(
    'irobot_embedding_requests_total',
    'Total des requêtes d\'embedding',
    ['model']
)

embedding_duration_seconds = Histogram(
    'irobot_embedding_duration_seconds',
    'Durée des embeddings en secondes',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

search_requests_total = Counter(
    'irobot_search_requests_total',
    'Total des recherches',
    ['search_type']  # hybrid, semantic, bm25
)

search_duration_seconds = Histogram(
    'irobot_search_duration_seconds',
    'Durée des recherches en secondes',
    ['search_type'],
    buckets=(0.05, 0.1, 0.5, 1.0, 2.0)
)

rerank_requests_total = Counter(
    'irobot_rerank_requests_total',
    'Total des requêtes de reranking'
)

rerank_duration_seconds = Histogram(
    'irobot_rerank_duration_seconds',
    'Durée du reranking en secondes',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

# ==================== MÉTRIQUES LLM ====================

llm_generation_requests_total = Counter(
    'irobot_llm_generation_requests_total',
    'Total des générations LLM',
    ['model', 'operation']  # operation: chat, title, ocr
)

llm_generation_duration_seconds = Histogram(
    'irobot_llm_generation_duration_seconds',
    'Durée des générations LLM en secondes',
    ['model', 'operation'],
    buckets=(1, 2, 5, 10, 20, 30, 60)
)

llm_tokens_total = Counter(
    'irobot_llm_tokens_total',
    'Total des tokens consommés',
    ['model', 'operation', 'token_type']  # token_type: prompt, completion
)

llm_cost_usd_total = Counter(
    'irobot_llm_cost_usd_total',
    'Coût total en USD',
    ['model', 'operation']
)

llm_cost_xaf_total = Counter(
    'irobot_llm_cost_xaf_total',
    'Coût total en XAF',
    ['model', 'operation']
)

# ==================== MÉTRIQUES CELERY ====================

celery_tasks_total = Counter(
    'irobot_celery_tasks_total',
    'Total des tâches Celery',
    ['queue', 'state']  # state: pending, started, success, failure, retry
)

celery_task_duration_seconds = Histogram(
    'irobot_celery_task_duration_seconds',
    'Durée des tâches Celery en secondes',
    ['queue', 'task_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

celery_queue_length = Gauge(
    'irobot_celery_queue_length',
    'Longueur des queues Celery',
    ['queue']
)

# ==================== MÉTRIQUES UTILISATEURS ====================

users_total = Gauge(
    'irobot_users_total',
    'Nombre total d\'utilisateurs'
)

users_active_total = Gauge(
    'irobot_users_active_total',
    'Nombre d\'utilisateurs actifs'
)

conversations_total = Gauge(
    'irobot_conversations_total',
    'Nombre total de conversations'
)

messages_total = Gauge(
    'irobot_messages_total',
    'Nombre total de messages'
)

feedbacks_total = Counter(
    'irobot_feedbacks_total',
    'Total des feedbacks',
    ['rating']  # thumbs_up, thumbs_down
)

# ==================== MÉTADONNÉES SYSTÈME ====================

system_info = Info(
    'irobot_system',
    'Informations système IroBot'
)

# Initialiser les informations système
system_info.info({
    'version': '1.0.0',
    'environment': 'development',
    'project': 'IroBot - BEAC RAG Chatbot'
})


# ==================== DÉCORATEURS UTILITAIRES ====================

def track_http_request(endpoint: str):
    """
    Décorateur pour tracker les requêtes HTTP.
    
    Usage:
        @track_http_request('/api/chat')
        async def chat_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 200
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                
                # Métriques
                http_requests_total.labels(
                    method='POST',  # ou extraire de la requête
                    endpoint=endpoint,
                    status=status
                ).inc()
                
                http_request_duration_seconds.labels(
                    method='POST',
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator


def track_document_processing():
    """
    Décorateur pour tracker le traitement de documents.
    
    Usage:
        @track_document_processing()
        async def process_document(document_id):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'completed'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = 'failed'
                raise
            finally:
                duration = time.time() - start_time
                
                document_processing_total.labels(status=status).inc()
                document_processing_duration_seconds.observe(duration)
        
        return wrapper
    return decorator


def track_llm_generation(model: str, operation: str):
    """
    Décorateur pour tracker les générations LLM.
    
    Usage:
        @track_llm_generation('mistral-medium', 'chat')
        async def generate_response(prompt):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Extraire les tokens du résultat si disponible
                if isinstance(result, dict):
                    prompt_tokens = result.get('prompt_tokens', 0)
                    completion_tokens = result.get('completion_tokens', 0)
                    cost_usd = result.get('cost_usd', 0)
                    cost_xaf = result.get('cost_xaf', 0)
                    
                    # Métriques tokens
                    if prompt_tokens:
                        llm_tokens_total.labels(
                            model=model,
                            operation=operation,
                            token_type='prompt'
                        ).inc(prompt_tokens)
                    
                    if completion_tokens:
                        llm_tokens_total.labels(
                            model=model,
                            operation=operation,
                            token_type='completion'
                        ).inc(completion_tokens)
                    
                    # Métriques coût
                    if cost_usd:
                        llm_cost_usd_total.labels(
                            model=model,
                            operation=operation
                        ).inc(cost_usd)
                    
                    if cost_xaf:
                        llm_cost_xaf_total.labels(
                            model=model,
                            operation=operation
                        ).inc(cost_xaf)
                
                return result
            finally:
                duration = time.time() - start_time
                
                llm_generation_requests_total.labels(
                    model=model,
                    operation=operation
                ).inc()
                
                llm_generation_duration_seconds.labels(
                    model=model,
                    operation=operation
                ).observe(duration)
        
        return wrapper
    return decorator


def update_cache_metrics(hit: bool, level: str = None, tokens_saved: int = 0, cost_saved_usd: float = 0):
    """
    Met à jour les métriques du cache.
    
    Args:
        hit: True si cache hit, False sinon
        level: 'L1' ou 'L2' si hit
        tokens_saved: Nombre de tokens économisés
        cost_saved_usd: Coût économisé en USD
    """
    if hit:
        cache_hits_total.labels(cache_level=level or 'unknown').inc()
        
        if tokens_saved:
            cache_tokens_saved.inc(tokens_saved)
        
        if cost_saved_usd:
            cache_cost_saved_usd.inc(cost_saved_usd)
    else:
        cache_misses_total.inc()
    
    # Calculer et mettre à jour le taux de hit
    total_hits = sum([
        cache_hits_total.labels(cache_level='L1')._value.get(),
        cache_hits_total.labels(cache_level='L2')._value.get()
    ])
    total_misses = cache_misses_total._value.get()
    total_requests = total_hits + total_misses
    
    if total_requests > 0:
        hit_rate = total_hits / total_requests
        cache_hit_rate.set(hit_rate)


def update_celery_queue_length(queue: str, length: int):
    """
    Met à jour la longueur d'une queue Celery.
    
    Args:
        queue: Nom de la queue
        length: Longueur actuelle
    """
    celery_queue_length.labels(queue=queue).set(length)


# ==================== EXPORT ====================

__all__ = [
    # Métriques
    'http_requests_total',
    'http_request_duration_seconds',
    'cache_hit_rate',
    'cache_hits_total',
    'cache_misses_total',
    'cache_tokens_saved',
    'cache_cost_saved_usd',
    'documents_total',
    'document_processing_total',
    'document_processing_duration_seconds',
    'chunks_created_total',
    'embedding_requests_total',
    'embedding_duration_seconds',
    'search_requests_total',
    'search_duration_seconds',
    'rerank_requests_total',
    'rerank_duration_seconds',
    'llm_generation_requests_total',
    'llm_generation_duration_seconds',
    'llm_tokens_total',
    'llm_cost_usd_total',
    'llm_cost_xaf_total',
    'celery_tasks_total',
    'celery_task_duration_seconds',
    'celery_queue_length',
    'users_total',
    'users_active_total',
    'conversations_total',
    'messages_total',
    'feedbacks_total',
    'system_info',
    
    # Utilitaires
    'track_http_request',
    'track_document_processing',
    'track_llm_generation',
    'update_cache_metrics',
    'update_celery_queue_length',
]