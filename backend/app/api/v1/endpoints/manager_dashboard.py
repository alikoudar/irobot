# app/api/v1/endpoints/manager_dashboard.py
"""
Endpoints API pour le dashboard manager.
Accessible par les rôles Admin et Manager.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.services.manager_dashboard_service import ManagerDashboardService
from app.schemas.manager_dashboard import (
    ManagerDashboardOverviewResponse,
    ManagerTopDocumentsResponse,
    ManagerDocumentsTimelineResponse
)
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager/dashboard", tags=["Manager Dashboard"])


def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    """Vérifie que l'utilisateur est Admin ou Manager."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et managers"
        )
    return current_user


@router.get(
    "/stats",
    response_model=ManagerDashboardOverviewResponse,
    summary="Statistiques dashboard manager",
    description="Récupère les statistiques complètes du dashboard manager (sans coûts, sans feedbacks)"
)
async def get_manager_dashboard_stats(
    start_date: Optional[datetime] = Query(
        None,
        description="Date de début (ISO format). Par défaut: 30 jours avant maintenant"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Date de fin (ISO format). Par défaut: maintenant"
    ),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques du dashboard manager.
    
    **Permissions**: Admin, Manager
    
    **Statistiques incluses**:
    - Documents uploadés (total, complétés, en cours, échoués)
    - Total chunks créés
    - Messages générés utilisant les documents
    - Documents par catégorie
    
    **Note**: Les coûts et feedbacks ne sont PAS affichés (contrairement au dashboard admin)
    """
    try:
        logger.info(f"📊 GET /manager/dashboard/stats - User: {current_user.matricule}")
        
        stats = ManagerDashboardService.get_manager_stats(
            db,
            current_user.id,
            start_date,
            end_date
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération stats manager: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )


@router.get(
    "/top-documents",
    response_model=ManagerTopDocumentsResponse,
    summary="Top documents du manager",
    description="Récupère les documents les plus utilisés du manager"
)
async def get_manager_top_documents(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Nombre maximum de documents à retourner (1-50)"
    ),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Récupère les top documents du manager triés par usage.
    
    **Permissions**: Admin, Manager
    
    **Informations par document**:
    - ID et titre du document
    - Catégorie
    - Nombre d'utilisations (usage_count)
    - Nombre total de chunks
    - Date d'upload
    
    **Tri**: Par usage_count décroissant
    """
    try:
        logger.info(f"🔝 GET /manager/dashboard/top-documents - User: {current_user.matricule}, Limit: {limit}")
        
        docs = ManagerDashboardService.get_manager_top_documents(
            db,
            current_user.id,
            limit
        )
        
        return {"documents": docs}
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération top documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des top documents: {str(e)}"
        )


@router.get(
    "/documents-timeline",
    response_model=ManagerDocumentsTimelineResponse,
    summary="Timeline des documents",
    description="Récupère la timeline des documents uploadés par le manager"
)
async def get_manager_documents_timeline(
    days: int = Query(
        30,
        ge=7,
        le=90,
        description="Nombre de jours à inclure (7-90)"
    ),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Récupère la timeline des documents uploadés par le manager.
    
    **Permissions**: Admin, Manager
    
    **Informations**:
    - Date
    - Nombre de documents uploadés ce jour
    
    **Période**: Configurable de 7 à 90 jours
    """
    try:
        logger.info(f"📅 GET /manager/dashboard/documents-timeline - User: {current_user.matricule}, Days: {days}")
        
        timeline = ManagerDashboardService.get_manager_documents_timeline(
            db,
            current_user.id,
            days
        )
        
        return {"timeline": timeline}
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération timeline documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de la timeline: {str(e)}"
        )