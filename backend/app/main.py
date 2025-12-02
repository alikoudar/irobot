"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
import logging

# SPRINT 13 - Monitoring : Import des middlewares de métriques
from app.core.middleware import (
    PrometheusMetricsMiddleware,
    RequestIDMiddleware,
    ProcessTimeMiddleware
)
from app.core.metrics import initialize_metrics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="RAG Chatbot pour la BEAC - Système d'authentification et gestion des utilisateurs",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json",
    root_path="/api" if settings.APP_ENV == "production" else "",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# SPRINT 13 - Monitoring : Add Prometheus metrics middleware
# IMPORTANT: PrometheusMetricsMiddleware doit être ajouté en DERNIER
# pour capturer toutes les requêtes après les autres middlewares
app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)

# Include API v1 router
app.include_router(api_router, prefix="/v1")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    logger.info("API v1 routes mounted at /v1")
    
    # SPRINT 13 - Monitoring : Initialize Prometheus metrics
    logger.info("Initializing Prometheus metrics...")
    initialize_metrics()
    logger.info("Prometheus metrics initialized successfully")
    logger.info("Metrics endpoint available at /v1/metrics")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Bienvenue sur {settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else None,
        "api_v1": "/v1"
    }