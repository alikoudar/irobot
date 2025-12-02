"""API v1 router - Regroupe tous les endpoints de l'API."""
from fastapi import APIRouter
from app.api.v1.endpoints import (auth, 
                                  users, 
                                  categories, 
                                  documents,
                                  chat,
                                  feedbacks,
                                  dashboard,
                                  manager_dashboard,
                                  config,
                                  metrics_endpoint)

# Créer le router principal v1
api_router = APIRouter()

# Inclure les routers des différents modules
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    categories.router, 
    tags=["Categories"]
)

api_router.include_router(
    documents.router,
    tags=["Documents"]
)

api_router.include_router(
    chat.router,
    tags=["Chat"]
)

api_router.include_router(
    feedbacks.router,
    tags=["Feedbacks"]
)

api_router.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

api_router.include_router(
    manager_dashboard.router,
    tags=["Manager Dashboard"]
)

api_router.include_router(
    config.router,
    tags=["Configuration"]
)

api_router.include_router(
    metrics_endpoint.router,
    tags=["Monitoring"]
)