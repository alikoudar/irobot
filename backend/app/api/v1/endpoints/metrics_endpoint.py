"""
Endpoint /metrics pour exposer les métriques Prometheus.

Ce fichier doit être importé dans app/main.py pour exposer les métriques.
"""

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
    CollectorRegistry,
    REGISTRY
)

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics")
async def metrics():
    """
    Endpoint Prometheus pour exposer les métriques.
    
    Returns:
        Response: Métriques au format Prometheus
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# ==================== UTILISATION ====================
# 
# Dans app/main.py, ajouter :
# 
# from app.api.v1.endpoints import metrics_endpoint
# 
# app.include_router(metrics_endpoint.router)
# 
# Les métriques seront alors disponibles sur http://localhost:8000/metrics
#