"""
Middleware de métriques Prometheus pour FastAPI
Capture automatiquement toutes les requêtes HTTP et enregistre les métriques

Sprint 13 - Monitoring & Observabilité
"""

import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.metrics import record_http_request


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware FastAPI qui capture toutes les requêtes HTTP et enregistre
    les métriques Prometheus automatiquement.
    
    Métriques collectées :
    - irobot_http_requests_total (Counter)
    - irobot_http_request_duration_seconds (Histogram)
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialise le middleware
        
        Args:
            app: Application FastAPI
        """
        super().__init__(app)
        
        # Endpoints à exclure du monitoring (pour éviter le bruit)
        self.excluded_paths = {
            '/metrics',      # Endpoint Prometheus lui-même
            '/v1/metrics',   # Endpoint Prometheus
            '/health',       # Health check
            '/v1/health',    # Health check
            '/docs',         # Swagger UI
            '/redoc',        # ReDoc
            '/openapi.json', # OpenAPI schema
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercepte chaque requête HTTP, mesure sa durée et enregistre les métriques
        
        Args:
            request: Requête HTTP entrante
            call_next: Fonction pour passer au middleware suivant
            
        Returns:
            Response: Réponse HTTP
        """
        # Extraire le path de la requête
        path = request.url.path
        
        # Exclure certains endpoints du monitoring
        if path in self.excluded_paths:
            return await call_next(request)
        
        # Normaliser le path pour regrouper les routes dynamiques
        # Exemple: /v1/documents/123 -> /v1/documents/{id}
        normalized_path = self._normalize_path(path)
        
        # Extraire la méthode HTTP
        method = request.method
        
        # Mesurer le temps de début
        start_time = time.time()
        
        # Initialiser le status code à 500 par défaut (en cas d'erreur)
        status_code = 500
        
        try:
            # Appeler le handler suivant (route, autre middleware, etc.)
            response = await call_next(request)
            
            # Extraire le status code de la réponse
            status_code = response.status_code
            
            return response
            
        except Exception as e:
            # En cas d'erreur, le status sera 500
            status_code = 500
            raise  # Re-lever l'exception pour que FastAPI la gère
            
        finally:
            # Mesurer la durée totale (même en cas d'erreur)
            duration = time.time() - start_time
            
            # Enregistrer les métriques Prometheus
            record_http_request(
                method=method,
                endpoint=normalized_path,
                status_code=status_code,
                duration=duration
            )
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalise le path pour regrouper les routes dynamiques
        
        Exemples:
        - /v1/documents/123 -> /v1/documents/{id}
        - /v1/users/456/chats/789 -> /v1/users/{id}/chats/{id}
        - /v1/categories/abc -> /v1/categories/{id}
        
        Args:
            path: Path original de la requête
            
        Returns:
            str: Path normalisé
        """
        # Découper le path en segments
        segments = path.split('/')
        normalized_segments = []
        
        for i, segment in enumerate(segments):
            if not segment:
                # Segment vide (début ou fin du path)
                continue
            
            # Détecter les IDs (UUID, nombres, etc.)
            if self._is_dynamic_segment(segment, i, segments):
                normalized_segments.append('{id}')
            else:
                normalized_segments.append(segment)
        
        # Reconstruire le path normalisé
        normalized_path = '/' + '/'.join(normalized_segments)
        
        return normalized_path
    
    def _is_dynamic_segment(self, segment: str, index: int, segments: list) -> bool:
        """
        Détecte si un segment est dynamique (ID, UUID, etc.)
        
        Args:
            segment: Segment à analyser
            index: Index du segment dans la liste
            segments: Liste complète des segments
            
        Returns:
            bool: True si le segment est dynamique
        """
        # Segments qui sont toujours des IDs dynamiques
        # (viennent après certains mots-clés)
        if index > 0:
            previous_segment = segments[index - 1]
            
            # Liste des segments qui sont suivis d'IDs
            id_indicators = {
                'documents', 'users', 'categories', 'chats', 
                'messages', 'feedbacks', 'sessions'
            }
            
            if previous_segment in id_indicators:
                return True
        
        # Détecter les UUIDs (format: 8-4-4-4-12)
        if len(segment) == 36 and segment.count('-') == 4:
            return True
        
        # Détecter les nombres (IDs numériques)
        if segment.isdigit():
            return True
        
        # Détecter les hash/IDs alphanumériques longs (> 16 caractères)
        if len(segment) > 16 and segment.isalnum():
            return True
        
        return False


# =============================================================================
# AUTRES MIDDLEWARES UTILITAIRES
# =============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui ajoute un Request ID unique à chaque requête
    Utile pour tracer les requêtes dans les logs
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Ajoute un X-Request-ID header à chaque requête
        
        Args:
            request: Requête HTTP
            call_next: Handler suivant
            
        Returns:
            Response: Réponse HTTP avec X-Request-ID
        """
        import uuid
        
        # Générer un Request ID unique
        request_id = str(uuid.uuid4())
        
        # Ajouter à l'état de la requête pour accès dans les routes
        request.state.request_id = request_id
        
        # Appeler le handler suivant
        response = await call_next(request)
        
        # Ajouter le Request ID dans les headers de la réponse
        response.headers['X-Request-ID'] = request_id
        
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui ajoute le temps de traitement dans les headers
    Utile pour le debugging
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Ajoute un X-Process-Time header avec la durée de traitement
        
        Args:
            request: Requête HTTP
            call_next: Handler suivant
            
        Returns:
            Response: Réponse HTTP avec X-Process-Time
        """
        start_time = time.time()
        
        # Appeler le handler suivant
        response = await call_next(request)
        
        # Calculer la durée
        process_time = time.time() - start_time
        
        # Ajouter dans les headers (en millisecondes)
        response.headers['X-Process-Time'] = f'{process_time * 1000:.2f}ms'
        
        return response


# =============================================================================
# UTILITAIRES POUR TESTS
# =============================================================================

def get_current_request_id(request: Request) -> str:
    """
    Récupère le Request ID de la requête courante
    
    Args:
        request: Requête FastAPI
        
    Returns:
        str: Request ID ou None si non disponible
    """
    return getattr(request.state, 'request_id', None)