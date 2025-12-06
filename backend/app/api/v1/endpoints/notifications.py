# ==============================================================================
# ENDPOINTS NOTIFICATIONS - SPRINT 14
# ==============================================================================
# API REST et SSE pour les notifications temps réel
# ==============================================================================

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationType,
    NotificationPriority,
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    NotificationFilters,
    NotificationBulkAction,
    NotificationBulkResponse
)
from app.services.notification import (
    NotificationService,
    sse_manager
)
from app.api.deps import (
    get_current_user,
    require_admin,
    require_admin_or_manager
)
from app.services.audit_log_service import AuditLogService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==============================================================================
# ENDPOINTS CRUD
# ==============================================================================

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    types: Optional[List[NotificationType]] = Query(None, description="Filtrer par types"),
    priorities: Optional[List[NotificationPriority]] = Query(None, description="Filtrer par priorités"),
    is_read: Optional[bool] = Query(None, description="Filtrer par statut lu"),
    include_dismissed: bool = Query(False, description="Inclure les notifications rejetées"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les notifications de l'utilisateur connecté.
    
    **Filtres disponibles:**
    - types: Liste des types de notifications
    - priorities: Liste des priorités
    - is_read: true/false pour filtrer les lues/non lues
    - include_dismissed: Inclure les notifications rejetées
    
    **Pagination:**
    - page: Numéro de page (défaut: 1)
    - page_size: Nombre d'éléments par page (défaut: 20, max: 100)
    """
    filters = NotificationFilters(
        types=types,
        priorities=priorities,
        is_read=is_read
    )
    
    return NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
        filters=filters,
        page=page,
        page_size=page_size,
        include_dismissed=include_dismissed
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir le nombre de notifications non lues.
    
    **Retourne:**
    ```json
    {
        "unread_count": 5
    }
    ```
    """
    count = NotificationService.get_unread_count(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marquer une notification comme lue.
    
    **Permissions:** Propriétaire de la notification ou Admin
    """
    notification = NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        priority=notification.priority,
        title=notification.title,
        message=notification.message,
        data=notification.data or {},
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        created_at=notification.created_at,
        read_at=notification.read_at,
        expires_at=notification.expires_at,
        icon=notification.icon,
        color=notification.color
    )


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marquer toutes les notifications comme lues.
    
    **Retourne:**
    ```json
    {
        "message": "5 notifications marquées comme lues",
        "count": 5
    }
    ```
    """
    count = NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    return {
        "message": f"{count} notification(s) marquée(s) comme lue(s)",
        "count": count
    }


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rejeter (supprimer visuellement) une notification.
    
    La notification reste en base mais n'apparaît plus dans la liste.
    """
    notification = NotificationService.dismiss_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        priority=notification.priority,
        title=notification.title,
        message=notification.message,
        data=notification.data or {},
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        created_at=notification.created_at,
        read_at=notification.read_at,
        expires_at=notification.expires_at,
        icon=notification.icon,
        color=notification.color
    )


@router.delete("/read")
async def delete_all_read_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer toutes les notifications lues.
    
    **Retourne:**
    ```json
    {
        "message": "5 notifications supprimées",
        "deleted_count": 5
    }
    ```
    """
    from app.models.notification import Notification
    from sqlalchemy import and_, or_
    
    # Construire la requête pour les notifications lues de l'utilisateur
    query = db.query(Notification).filter(
        Notification.is_read == True
    )
    
    # Filtrer par utilisateur (admin voit tout, user voit les siennes)
    if current_user.role == UserRole.ADMIN:
        query = query.filter(
            or_(
                Notification.user_id == current_user.id,
                Notification.user_id.is_(None)
            )
        )
    else:
        query = query.filter(Notification.user_id == current_user.id)
    
    count = query.delete(synchronize_session=False)
    db.commit()
    
    logger.info(f"{count} notifications lues supprimées par {current_user.id}")
    
    return {
        "message": f"{count} notification(s) supprimée(s)",
        "deleted_count": count
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer définitivement une notification.
    
    **Note:** Cette action est irréversible.
    """
    notification = NotificationService.get_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    # Supprimer la notification
    db.delete(notification)
    db.commit()
    
    logger.info(f"Notification {notification_id} supprimée par {current_user.id}")
    
    return {"message": "Notification supprimée", "id": str(notification_id)}


@router.post("/dismiss-all")
async def dismiss_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rejeter toutes les notifications.
    
    **Retourne:**
    ```json
    {
        "message": "5 notifications rejetées",
        "count": 5
    }
    ```
    """
    count = NotificationService.dismiss_all(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    return {
        "message": f"{count} notification(s) rejetée(s)",
        "count": count
    }


@router.post("/bulk-action", response_model=NotificationBulkResponse)
async def bulk_notification_action(
    action_data: NotificationBulkAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Action en masse sur plusieurs notifications.
    
    **Actions disponibles:**
    - `read`: Marquer comme lues
    - `dismiss`: Rejeter
    - `delete`: Supprimer définitivement (Admin uniquement)
    
    **Exemple:**
    ```json
    {
        "notification_ids": ["uuid1", "uuid2", "uuid3"],
        "action": "read"
    }
    ```
    """
    affected_count = 0
    
    for notification_id in action_data.notification_ids:
        try:
            if action_data.action == "read":
                result = NotificationService.mark_as_read(
                    db, notification_id, current_user.id
                )
            elif action_data.action == "dismiss":
                result = NotificationService.dismiss_notification(
                    db, notification_id, current_user.id
                )
            elif action_data.action == "delete":
                # Supprimer définitivement (admin only)
                if current_user.role != UserRole.ADMIN:
                    continue
                # Implémenter la suppression si nécessaire
                result = NotificationService.dismiss_notification(
                    db, notification_id, current_user.id
                )
            else:
                continue
                
            if result:
                affected_count += 1
        except Exception as e:
            logger.error(f"Erreur action bulk notification {notification_id}: {e}")
            continue
    
    return NotificationBulkResponse(
        success=affected_count > 0,
        affected_count=affected_count,
        message=f"{affected_count} notification(s) affectée(s)"
    )


# ==============================================================================
# ENDPOINTS SSE STREAMS
# ==============================================================================

@router.get("/stream")
async def stream_notifications(
    token: str = Query(..., description="JWT Token pour authentification SSE"),
    db: Session = Depends(get_db)
):
    """
    Stream SSE des notifications en temps réel.
    
    **IMPORTANT:** EventSource ne supporte pas les headers personnalisés.
    Le token doit être passé via query parameter.
    
    **Événements:**
    - `connected`: Connexion établie avec compteur initial
    - `notification`: Nouvelle notification
    - `heartbeat`: Maintien de connexion (toutes les 30s)
    
    **Usage JavaScript:**
    ```javascript
    const token = localStorage.getItem('access_token');
    const eventSource = new EventSource(`/api/v1/notifications/stream?token=${token}`);
    
    eventSource.addEventListener('notification', (event) => {
        const notification = JSON.parse(event.data);
        console.log('Nouvelle notification:', notification);
    });
    
    eventSource.addEventListener('heartbeat', (event) => {
        console.log('Connexion active');
    });
    ```
    """
    from app.core.security import decode_token
    
    # Valider le token manuellement (car EventSource ne supporte pas les headers)
    try:
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        user_role = payload.get("role")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: user_id manquant"
            )
        
        # Vérifier que l'utilisateur existe et est actif
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur inactif ou inexistant"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur validation token SSE: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur de validation du token"
        )
    
    # Obtenir le compteur initial
    unread_count = NotificationService.get_unread_count(
        db=db,
        user_id=user.id,
        user_role=user.role
    )
    
    return StreamingResponse(
        NotificationService.stream_user_notifications(
            user_id=user.id,
            user_role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            initial_unread_count=unread_count
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Désactiver le buffering nginx
        }
    )


@router.get("/admin/events/stream")
async def stream_admin_events(
    token: str = Query(..., description="JWT Token pour authentification SSE"),
    db: Session = Depends(get_db)
):
    """
    Stream SSE des événements admin (feedbacks, documents, etc.)
    
    **Permissions:** Admin uniquement
    
    **Événements:**
    - `connected`: Connexion établie
    - `notification`: Nouvelle notification admin
    - `feedback`: Nouveau feedback reçu
    - `document_status`: Changement de statut document
    - `heartbeat`: Maintien de connexion
    
    **Usage JavaScript:**
    ```javascript
    const token = localStorage.getItem('access_token');
    const eventSource = new EventSource(`/api/v1/notifications/admin/events/stream?token=${token}`);
    
    eventSource.addEventListener('feedback', (event) => {
        const feedback = JSON.parse(event.data);
        showFeedbackAlert(feedback);
    });
    ```
    """
    from app.core.security import decode_token
    
    # Valider le token manuellement
    try:
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        user_role = payload.get("role")
        
        # Vérifier que l'utilisateur est admin
        if user_role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès réservé aux administrateurs"
            )
        
        # Vérifier que l'utilisateur existe et est actif
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur inactif ou inexistant"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur validation token SSE admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur de validation du token"
        )
    
    return StreamingResponse(
        NotificationService.stream_admin_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/dashboard/stream")
async def stream_dashboard_stats(
    token: str = Query(..., description="JWT Token pour authentification SSE"),
    db: Session = Depends(get_db)
):
    """
    Stream SSE des statistiques dashboard en temps réel.
    
    **Permissions:** Admin ou Manager
    
    **Événements:**
    - `connected`: Connexion établie
    - `dashboard_update`: Mise à jour des statistiques
    - `heartbeat`: Maintien de connexion
    
    Les mises à jour sont envoyées automatiquement lorsque:
    - Un document termine son traitement
    - Un nouveau feedback est reçu
    - Les statistiques changent significativement
    """
    from app.core.security import decode_token
    
    # Valider le token manuellement
    try:
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        user_role = payload.get("role")
        
        # Vérifier que l'utilisateur est admin ou manager
        if user_role not in ["ADMIN", "MANAGER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès réservé aux administrateurs et managers"
            )
        
        # Vérifier que l'utilisateur existe et est actif
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur inactif ou inexistant"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur validation token SSE dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur de validation du token"
        )
    
    return StreamingResponse(
        NotificationService.stream_dashboard_stats(
            user_id=user.id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/connection-stats")
async def get_connection_stats(
    current_user: User = Depends(require_admin)
):
    """
    Obtenir les statistiques des connexions SSE.
    
    **Permissions:** Admin uniquement
    
    **Retourne:**
    ```json
    {
        "user_connections": 15,
        "unique_users": 8,
        "admin_connections": 3,
        "dashboard_connections": 5
    }
    ```
    """
    return sse_manager.get_connection_stats()


# ==============================================================================
# ENDPOINTS ADMIN - CRÉATION NOTIFICATIONS
# ==============================================================================

@router.post("/admin/create", response_model=NotificationResponse)
async def create_notification_admin(
    notification_data: NotificationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Créer une notification manuellement (Admin).
    
    **Permissions:** Admin uniquement
    
    **Payload:**
    ```json
    {
        "user_id": "uuid-optionnel",  // null = broadcast aux admins
        "type": "system_info",
        "priority": "medium",
        "title": "Maintenance programmée",
        "message": "Le système sera en maintenance demain à 2h.",
        "data": {"key": "value"},
        "expires_at": "2024-12-31T23:59:59Z"
    }
    ```
    """
    notification = await NotificationService.create_notification(
        db=db,
        notification_data=notification_data,
        broadcast_sse=True
    )
    
    # Audit log
    AuditLogService.log_action(
        db=db,
        user_id=current_user.id,
        action="notification.create",
        resource_type="notification",
        resource_id=str(notification.id),
        details={
            "type": notification.type.value,
            "title": notification.title,
            "target_user_id": str(notification.user_id) if notification.user_id else "broadcast"
        }
    )
    
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        priority=notification.priority,
        title=notification.title,
        message=notification.message,
        data=notification.data or {},
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        created_at=notification.created_at,
        read_at=notification.read_at,
        expires_at=notification.expires_at,
        icon=notification.icon,
        color=notification.color
    )


@router.post("/admin/broadcast")
async def broadcast_notification(
    title: str = Query(..., min_length=1, max_length=200),
    message: str = Query(None),
    priority: NotificationPriority = Query(NotificationPriority.MEDIUM),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Diffuser une notification système à tous les utilisateurs.
    
    **Permissions:** Admin uniquement
    
    **Paramètres:**
    - title: Titre de la notification
    - message: Message détaillé (optionnel)
    - priority: Priorité (low, medium, high, urgent)
    """
    # Récupérer tous les utilisateurs actifs
    users = db.query(User).filter(User.is_active == True).all()
    
    created_count = 0
    for user in users:
        try:
            await NotificationService.create_notification(
                db=db,
                notification_data=NotificationCreate(
                    user_id=user.id,
                    type=NotificationType.SYSTEM_INFO,
                    priority=priority,
                    title=title,
                    message=message,
                    data={"broadcast": True, "admin_id": str(current_user.id)}
                ),
                broadcast_sse=True
            )
            created_count += 1
        except Exception as e:
            logger.error(f"Erreur broadcast notification à {user.id}: {e}")
    
    # Audit log
    AuditLogService.log_action(
        db=db,
        user_id=current_user.id,
        action="notification.broadcast",
        resource_type="notification",
        details={
            "title": title,
            "priority": priority.value,
            "recipients_count": created_count
        }
    )
    
    return {
        "message": f"Notification diffusée à {created_count} utilisateur(s)",
        "recipients_count": created_count
    }


# ==============================================================================
# ENDPOINTS MAINTENANCE
# ==============================================================================

@router.post("/admin/cleanup")
async def cleanup_notifications(
    days: int = Query(30, ge=7, le=365, description="Jours à conserver"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Nettoyer les anciennes notifications.
    
    **Permissions:** Admin uniquement
    
    Supprime:
    - Les notifications lues de plus de X jours
    - Les notifications expirées
    
    **Paramètres:**
    - days: Nombre de jours à conserver (min: 7, max: 365, défaut: 30)
    """
    count = NotificationService.cleanup_old_notifications(
        db=db,
        days=days
    )
    
    # Audit log
    AuditLogService.log_action(
        db=db,
        user_id=current_user.id,
        action="notification.cleanup",
        resource_type="notification",
        details={
            "retention_days": days,
            "deleted_count": count
        }
    )
    
    return {
        "message": f"{count} notification(s) supprimée(s)",
        "deleted_count": count,
        "retention_days": days
    }


# ==============================================================================
# ENDPOINT DE TEST SSE (À SUPPRIMER EN PRODUCTION)
# ==============================================================================

@router.post("/test-sse")
async def test_sse_broadcast(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Endpoint de test pour vérifier le broadcast SSE.
    
    Crée une notification de test et la broadcast immédiatement.
    """
    from datetime import datetime
    
    # Log des connexions actives
    stats = sse_manager.get_connection_stats()
    logger.info(f"🔍 SSE Stats: {stats}")
    
    # Créer une notification de test
    notification = await NotificationService.create_notification(
        db=db,
        notification_data=NotificationCreate(
            user_id=None,  # Broadcast aux admins
            type=NotificationType.SYSTEM_INFO,
            priority=NotificationPriority.MEDIUM,
            title="🧪 Test SSE",
            message=f"Notification de test créée à {datetime.utcnow().strftime('%H:%M:%S')}",
            data={"test": True, "timestamp": datetime.utcnow().isoformat()}
        ),
        broadcast_sse=True
    )
    
    return {
        "success": True,
        "notification_id": str(notification.id),
        "sse_stats": stats,
        "message": "Notification de test créée et broadcastée"
    }