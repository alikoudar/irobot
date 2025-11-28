# -*- coding: utf-8 -*-
"""
Endpoints API Dashboard - Sprint 10 Phase 1

Expose les endpoints pour le dashboard admin :
- GET /dashboard/overview : Vue d'ensemble complète
- GET /dashboard/top-documents : Top documents
- GET /dashboard/activity-timeline : Timeline d'activité
- GET /dashboard/user-activity : Activité utilisateurs
- GET /dashboard/export : Export CSV/JSON

Auteur: IroBot Team
Date: 2025-11-27
Sprint: 10 - Phase 1
"""

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.dashboard import (
    DashboardOverview,
    TopDocumentsResponse,
    ActivityTimelineResponse,
    UserActivityResponse
)
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# =============================================================================
# GET OVERVIEW
# =============================================================================

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    start_date: Optional[datetime] = Query(
        default=None,
        description="Date de début (par défaut: 30 jours avant)"
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Date de fin (par défaut: maintenant)"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère la vue d'ensemble du dashboard admin.
    
    **Permissions**: Admin uniquement
    
    **Retourne**:
    - Statistiques utilisateurs (total, actifs, nouveaux, inactifs)
    - Statistiques documents (total, complétés, en traitement, échoués, chunks)
    - Statistiques conversations
    - Statistiques messages (total, user, assistant)
    - Statistiques cache (hits, misses, hit rate, tokens/cost saved)
    - Statistiques tokens par opération (embedding, reranking, génération)
    - Statistiques feedbacks (satisfaction, taux de feedback)
    - Plage de dates analysée
    """
    try:
        stats = DashboardService.get_overview_stats(db, start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération stats dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )


# =============================================================================
# GET TOP DOCUMENTS
# =============================================================================

@router.get("/top-documents", response_model=TopDocumentsResponse)
async def get_top_documents(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Nombre de documents à retourner"
    ),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Date de début (optionnel)"
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Date de fin (optionnel)"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère les top N documents les plus consultés.
    
    **Permissions**: Admin uniquement
    
    **Paramètres**:
    - `limit`: Nombre de documents (1-50)
    - `start_date`: Filtrer par date début (optionnel)
    - `end_date`: Filtrer par date fin (optionnel)
    
    **Retourne**:
    Liste des documents avec :
    - ID document
    - Titre
    - Catégorie
    - Nombre d'utilisations
    - Nombre de chunks
    """
    try:
        docs = DashboardService.get_top_documents(db, limit, start_date, end_date)
        return {
            "documents": docs,
            "total": len(docs)
        }
    except Exception as e:
        logger.error(f"Erreur récupération top documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des top documents"
        )


# =============================================================================
# GET ACTIVITY TIMELINE
# =============================================================================

@router.get("/activity-timeline", response_model=ActivityTimelineResponse)
async def get_activity_timeline(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Nombre de jours à analyser"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère la timeline d'activité journalière.
    
    **Permissions**: Admin uniquement
    
    **Paramètres**:
    - `days`: Nombre de jours à analyser (1-365)
    
    **Retourne**:
    Timeline avec pour chaque jour :
    - Date
    - Nombre de messages
    - Nombre de documents traités
    """
    try:
        timeline = DashboardService.get_activity_timeline(db, days)
        return {
            "timeline": timeline,
            "days": days
        }
    except Exception as e:
        logger.error(f"Erreur récupération timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de la timeline"
        )


# =============================================================================
# GET USER ACTIVITY
# =============================================================================

@router.get("/user-activity", response_model=UserActivityResponse)
async def get_user_activity(
    start_date: Optional[datetime] = Query(
        default=None,
        description="Date de début (par défaut: 30 jours avant)"
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Date de fin (par défaut: maintenant)"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Nombre d'utilisateurs à retourner"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques d'activité par utilisateur.
    
    **Permissions**: Admin uniquement
    
    **Paramètres**:
    - `start_date`: Date de début (par défaut: 30 jours avant)
    - `end_date`: Date de fin (par défaut: maintenant)
    - `limit`: Nombre d'utilisateurs (1-100)
    
    **Retourne**:
    Liste des utilisateurs les plus actifs avec :
    - ID utilisateur
    - Matricule
    - Nom complet
    - Nombre de messages envoyés
    """
    try:
        # Dates par défaut
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        users = DashboardService.get_user_activity_stats(db, start_date, end_date, limit)
        return {
            "users": users,
            "total": len(users)
        }
    except Exception as e:
        logger.error(f"Erreur récupération user activity: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'activité utilisateurs"
        )


# =============================================================================
# EXPORT STATS
# =============================================================================

@router.get("/export")
async def export_dashboard_stats(
    format: str = Query(
        default="csv",
        regex="^(csv|json)$",
        description="Format d'export (csv ou json)"
    ),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Date de début (optionnel)"
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Date de fin (optionnel)"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Exporte les statistiques du dashboard.
    
    **Permissions**: Admin uniquement
    
    **Paramètres**:
    - `format`: Format d'export (csv ou json)
    - `start_date`: Date de début (optionnel)
    - `end_date`: Date de fin (optionnel)
    
    **Formats disponibles**:
    - `csv`: Export CSV avec métriques principales
    - `json`: Export JSON complet
    """
    try:
        stats = DashboardService.get_overview_stats(db, start_date, end_date)
        
        if format == "json":
            return stats
        
        elif format == "csv":
            # Créer CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow(["Métrique", "Valeur"])
            
            # Users
            writer.writerow(["=== UTILISATEURS ===", ""])
            writer.writerow(["Utilisateurs Totaux", stats["users"]["total"]])
            writer.writerow(["Utilisateurs Actifs", stats["users"]["active"]])
            writer.writerow(["Nouveaux Utilisateurs", stats["users"]["new"]])
            writer.writerow(["Utilisateurs Inactifs", stats["users"]["inactive"]])
            
            # Documents
            writer.writerow(["", ""])
            writer.writerow(["=== DOCUMENTS ===", ""])
            writer.writerow(["Documents Totaux", stats["documents"]["total"]])
            writer.writerow(["Documents Complétés", stats["documents"]["completed"]])
            writer.writerow(["Documents En Traitement", stats["documents"]["processing"]])
            writer.writerow(["Documents Échoués", stats["documents"]["failed"]])
            writer.writerow(["Total Chunks", stats["documents"]["total_chunks"]])
            
            # Conversations & Messages
            writer.writerow(["", ""])
            writer.writerow(["=== CONVERSATIONS & MESSAGES ===", ""])
            writer.writerow(["Conversations Totales", stats["conversations"]["total"]])
            writer.writerow(["Messages Totaux", stats["messages"]["total"]])
            writer.writerow(["Messages Utilisateurs", stats["messages"]["user_messages"]])
            writer.writerow(["Messages Assistant", stats["messages"]["assistant_messages"]])
            
            # Cache
            writer.writerow(["", ""])
            writer.writerow(["=== CACHE ===", ""])
            writer.writerow(["Total Requêtes", stats["cache"]["total_requests"]])
            writer.writerow(["Cache Hits", stats["cache"]["cache_hits"]])
            writer.writerow(["Cache Misses", stats["cache"]["cache_misses"]])
            writer.writerow(["Taux de Hit", f"{stats['cache']['hit_rate']}%"])
            writer.writerow(["Tokens Économisés", stats["cache"]["tokens_saved"]])
            writer.writerow(["Coût Économisé USD", f"${stats['cache']['cost_saved_usd']}"])
            writer.writerow(["Coût Économisé XAF", f"{stats['cache']['cost_saved_xaf']} FCFA"])
            
            # Tokens
            writer.writerow(["", ""])
            writer.writerow(["=== TOKENS & COÛTS ===", ""])
            writer.writerow(["Total Tokens", stats["tokens"]["total"]["total_tokens"]])
            writer.writerow(["Coût Total USD", f"${stats['tokens']['total']['total_cost_usd']}"])
            writer.writerow(["Coût Total XAF", f"{stats['tokens']['total']['total_cost_xaf']} FCFA"])
            
            # Tokens par opération
            for operation in ["embedding", "reranking", "title_generation", "response_generation"]:
                if operation in stats["tokens"]:
                    op_stats = stats["tokens"][operation]
                    writer.writerow([f"Tokens {operation}", op_stats["total_tokens"]])
                    writer.writerow([f"Coût {operation} USD", f"${op_stats['total_cost_usd']}"])
            
            # Feedbacks
            writer.writerow(["", ""])
            writer.writerow(["=== FEEDBACKS ===", ""])
            writer.writerow(["Total Feedbacks", stats["feedbacks"]["total_feedbacks"]])
            writer.writerow(["Thumbs Up", stats["feedbacks"]["thumbs_up"]])
            writer.writerow(["Thumbs Down", stats["feedbacks"]["thumbs_down"]])
            writer.writerow(["Avec Commentaires", stats["feedbacks"]["with_comments"]])
            writer.writerow(["Taux de Satisfaction", f"{stats['feedbacks']['satisfaction_rate']}%"])
            writer.writerow(["Taux de Feedback", f"{stats['feedbacks']['feedback_rate']}%"])
            
            # Date Range
            writer.writerow(["", ""])
            writer.writerow(["=== PÉRIODE ANALYSÉE ===", ""])
            writer.writerow(["Date Début", stats["date_range"]["start"]])
            writer.writerow(["Date Fin", stats["date_range"]["end"]])
            
            # Retourner CSV
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard_stats_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
    
    except Exception as e:
        logger.error(f"Erreur export stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export des statistiques"
        )