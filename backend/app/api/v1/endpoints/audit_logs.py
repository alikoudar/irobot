# -*- coding: utf-8 -*-
"""
Endpoints API Audit Logs - Sprint 13 Complément

Expose les endpoints pour la consultation des logs d'audit :
- GET /audit-logs : Liste paginée avec filtrage
- GET /audit-logs/stats : Statistiques globales
- GET /audit-logs/activity : Activité par date
- GET /audit-logs/filters : Options de filtrage disponibles
- GET /audit-logs/{id} : Détail d'un log

Auteur: IroBot Team
Date: 2025-12-02
Sprint: 13 - Complément
"""

import logging
import math
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.schemas.audit_log import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogStats,
    AuditLogActivityResponse,
    AuditLogActivityByDate,
    AuditLogUserInfo,
    AuditActionEnum,
    EntityTypeEnum,
    AVAILABLE_ACTIONS,
    AVAILABLE_ENTITY_TYPES,
)
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


# =============================================================================
# GET ALL LOGS (PAGINATED + FILTERED)
# =============================================================================

@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    user_id: Optional[UUID] = Query(
        None,
        description="Filtrer par ID utilisateur"
    ),
    action: Optional[AuditActionEnum] = Query(
        None,
        description="Filtrer par type d'action"
    ),
    entity_type: Optional[EntityTypeEnum] = Query(
        None,
        description="Filtrer par type d'entité"
    ),
    start_date: Optional[date] = Query(
        None,
        description="Date de début (format: YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="Date de fin (format: YYYY-MM-DD)"
    ),
    search: Optional[str] = Query(
        None,
        max_length=100,
        description="Recherche textuelle dans les détails"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère la liste paginée des logs d'audit avec filtrage.

    **Permissions**: Admin uniquement.

    **Filtres disponibles**:
    - `user_id`: UUID de l'utilisateur
    - `action`: Type d'action (LOGIN_SUCCESS, USER_CREATED, CONFIG_UPDATE, etc.)
    - `entity_type`: Type d'entité (AUTH, USER, DOCUMENT, CATEGORY, CONFIG)
    - `start_date` / `end_date`: Période de filtrage
    - `search`: Recherche dans les détails JSON

    **Pagination**:
    - `page`: Numéro de page (défaut: 1)
    - `page_size`: Éléments par page (défaut: 20, max: 100)
    """
    try:
        # Convertir les enums en string pour le service
        action_str = action.value if action else None
        entity_type_str = entity_type.value if entity_type else None
        
        # Récupération des logs
        logs, total = AuditLogService.get_logs(
            db=db,
            page=page,
            page_size=page_size,
            user_id=user_id,
            action=action_str,
            entity_type=entity_type_str,
            start_date=start_date,
            end_date=end_date,
            search=search,
            include_user=True
        )
        
        # Calcul du nombre de pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        # Construction de la réponse
        items = []
        for log in logs:
            # Informations utilisateur si disponibles
            user_info = None
            if log.user:
                user_info = AuditLogUserInfo(
                    id=log.user.id,
                    matricule=log.user.matricule,
                    nom=log.user.nom,
                    prenom=log.user.prenom,
                    email=log.user.email
                )
            
            items.append(AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
                user=user_info
            ))
        
        # Filtres appliqués pour référence
        filters_applied = {}
        if user_id:
            filters_applied["user_id"] = str(user_id)
        if action:
            filters_applied["action"] = action.value
        if entity_type:
            filters_applied["entity_type"] = entity_type.value
        if start_date:
            filters_applied["start_date"] = str(start_date)
        if end_date:
            filters_applied["end_date"] = str(end_date)
        if search:
            filters_applied["search"] = search
        
        logger.info(
            f"📋 Logs d'audit récupérés: page={page}/{total_pages}, "
            f"total={total}, filtres={len(filters_applied)}"
        )
        
        return AuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            filters=filters_applied if filters_applied else None
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération logs d'audit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des logs d'audit"
        )


# =============================================================================
# GET LOG STATS
# =============================================================================

@router.get("/stats", response_model=AuditLogStats)
async def get_audit_log_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère les statistiques globales des logs d'audit.

    **Permissions**: Admin uniquement.

    **Retourne**:
    - Nombre total de logs
    - Logs aujourd'hui / cette semaine / ce mois
    - Répartition par action
    - Répartition par type d'entité
    - Date de dernière activité
    """
    try:
        stats = AuditLogService.get_stats(db)
        
        logger.info(
            f"📊 Statistiques logs récupérées: "
            f"total={stats['total_logs']}, today={stats['logs_today']}"
        )
        
        return AuditLogStats(**stats)
        
    except Exception as e:
        logger.error(f"❌ Erreur statistiques logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )


# =============================================================================
# GET ACTIVITY BY DATE
# =============================================================================

@router.get("/activity", response_model=AuditLogActivityResponse)
async def get_audit_log_activity(
    start_date: Optional[date] = Query(
        None,
        description="Date de début (défaut: 30 jours avant)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="Date de fin (défaut: aujourd'hui)"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère l'activité des logs par date sur une période.

    **Permissions**: Admin uniquement.

    **Paramètres**:
    - `start_date`: Date de début (défaut: 30 jours avant)
    - `end_date`: Date de fin (défaut: aujourd'hui)

    **Retourne**:
    - Liste de l'activité quotidienne (date + nombre de logs)
    """
    try:
        # Valeurs par défaut
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validation
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de début doit être antérieure à la date de fin"
            )
        
        # Limiter à 365 jours max
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La période ne peut pas dépasser 365 jours"
            )
        
        # Récupération de l'activité
        daily_activity = AuditLogService.get_activity_by_date(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        # Construction de la réponse
        total = sum(day["count"] for day in daily_activity)
        
        activity_items = [
            AuditLogActivityByDate(
                date=day["date"],
                count=day["count"]
            )
            for day in daily_activity
        ]
        
        logger.info(
            f"📈 Activité logs: {start_date} → {end_date}, "
            f"total={total}, jours={len(activity_items)}"
        )
        
        return AuditLogActivityResponse(
            start_date=start_date,
            end_date=end_date,
            total=total,
            daily_activity=activity_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur activité logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'activité"
        )


# =============================================================================
# GET FILTER OPTIONS
# =============================================================================

@router.get("/filters")
async def get_audit_log_filters(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère les options de filtrage disponibles.

    **Permissions**: Admin uniquement.

    **Retourne**:
    - Liste des actions avec labels
    - Liste des types d'entités avec labels
    """
    try:
        logger.info(
            f"🔍 Options filtrage: {len(AVAILABLE_ACTIONS)} actions, "
            f"{len(AVAILABLE_ENTITY_TYPES)} entity types"
        )
        
        return {
            "actions": AVAILABLE_ACTIONS,
            "entity_types": AVAILABLE_ENTITY_TYPES
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur options filtrage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des options de filtrage"
        )


# =============================================================================
# GET SINGLE LOG
# =============================================================================

@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère le détail d'un log d'audit.

    **Permissions**: Admin uniquement.

    **Paramètres**:
    - `log_id`: UUID du log d'audit
    """
    try:
        log = AuditLogService.get_log_by_id(
            db=db,
            log_id=log_id,
            include_user=True
        )
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log d'audit non trouvé"
            )
        
        # Informations utilisateur si disponibles
        user_info = None
        if log.user:
            user_info = AuditLogUserInfo(
                id=log.user.id,
                matricule=log.user.matricule,
                nom=log.user.nom,
                prenom=log.user.prenom,
                email=log.user.email
            )
        
        logger.info(f"📝 Log d'audit récupéré: {log_id}")
        
        return AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération log {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du log d'audit"
        )


# =============================================================================
# GET USER ACTIVITY
# =============================================================================

@router.get("/user/{user_id}", response_model=List[AuditLogResponse])
async def get_user_audit_logs(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère les dernières actions d'un utilisateur spécifique.

    **Permissions**: Admin uniquement.

    **Paramètres**:
    - `user_id`: UUID de l'utilisateur
    - `limit`: Nombre maximum de résultats (défaut: 50)
    """
    try:
        logs = AuditLogService.get_user_activity(
            db=db,
            user_id=user_id,
            limit=limit
        )
        
        items = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
                user=None  # Pas besoin de l'user ici, on le connaît déjà
            )
            for log in logs
        ]
        
        logger.info(
            f"📋 Activité utilisateur {user_id}: {len(items)} logs récupérés"
        )
        
        return items
        
    except Exception as e:
        logger.error(f"❌ Erreur activité utilisateur {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'activité utilisateur"
        )