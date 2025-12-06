# ==============================================================================
# SERVICE NOTIFICATION - SPRINT 14
# ==============================================================================
# Gestion complète des notifications et diffusion SSE
# ==============================================================================

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID
from collections import defaultdict

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationType,
    NotificationPriority
)
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationListResponse,
    NotificationResponse,
    DocumentStatusEvent,
    FeedbackEvent,
    DashboardStatsEvent
)
from app.services.audit_log_service import AuditLogService


logger = logging.getLogger(__name__)


# ==============================================================================
# SSE CONNECTION MANAGER
# ==============================================================================

class SSEConnectionManager:
    """
    Gestionnaire des connexions SSE.
    
    Maintient une liste des connexions actives par utilisateur
    et permet la diffusion d'événements en temps réel.
    """
    
    def __init__(self):
        # Connexions par user_id : {user_id: [(queue, role), ...]}
        self._connections: Dict[str, List[tuple]] = defaultdict(list)
        # Connexions admin globales (pour les événements broadcast via /admin/events/stream)
        self._admin_connections: List[asyncio.Queue] = []
        # Connexions dashboard (pour les stats temps réel)
        self._dashboard_connections: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        # Lock pour la thread-safety
        self._lock = asyncio.Lock()
    
    async def connect_user(self, user_id: str, user_role: str = "USER") -> asyncio.Queue:
        """
        Connecter un utilisateur au flux SSE.
        
        Args:
            user_id: ID de l'utilisateur
            user_role: Rôle de l'utilisateur (USER, MANAGER, ADMIN)
            
        Returns:
            Queue pour recevoir les événements
        """
        queue = asyncio.Queue()
        async with self._lock:
            self._connections[user_id].append((queue, user_role))
        logger.info(f"SSE: Utilisateur {user_id} ({user_role}) connecté (total: {len(self._connections[user_id])})")
        return queue
    
    async def disconnect_user(self, user_id: str, queue: asyncio.Queue) -> None:
        """
        Déconnecter un utilisateur du flux SSE.
        
        Args:
            user_id: ID de l'utilisateur
            queue: Queue à supprimer
        """
        async with self._lock:
            if user_id in self._connections:
                # Chercher la queue dans les tuples (queue, role)
                self._connections[user_id] = [
                    (q, r) for q, r in self._connections[user_id] if q != queue
                ]
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"SSE: Utilisateur {user_id} déconnecté")
    
    async def connect_admin(self) -> asyncio.Queue:
        """Connecter un admin au flux global."""
        queue = asyncio.Queue()
        async with self._lock:
            self._admin_connections.append(queue)
        logger.info(f"SSE: Admin connecté (total: {len(self._admin_connections)})")
        return queue
    
    async def disconnect_admin(self, queue: asyncio.Queue) -> None:
        """Déconnecter un admin du flux global."""
        async with self._lock:
            try:
                self._admin_connections.remove(queue)
            except ValueError:
                pass
        logger.info("SSE: Admin déconnecté")
    
    async def connect_dashboard(self, user_id: str) -> asyncio.Queue:
        """Connecter au flux dashboard."""
        queue = asyncio.Queue()
        async with self._lock:
            self._dashboard_connections[user_id].append(queue)
        return queue
    
    async def disconnect_dashboard(self, user_id: str, queue: asyncio.Queue) -> None:
        """Déconnecter du flux dashboard."""
        async with self._lock:
            if user_id in self._dashboard_connections:
                try:
                    self._dashboard_connections[user_id].remove(queue)
                    if not self._dashboard_connections[user_id]:
                        del self._dashboard_connections[user_id]
                except ValueError:
                    pass
    
    async def send_to_user(self, user_id: str, event: str, data: dict) -> int:
        """
        Envoyer un événement à un utilisateur spécifique.
        
        Args:
            user_id: ID de l'utilisateur
            event: Type d'événement
            data: Données de l'événement
            
        Returns:
            Nombre de connexions notifiées
        """
        message = {"event": event, "data": data}
        sent_count = 0
        
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for queue, role in connections:
                try:
                    await queue.put(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"SSE: Erreur envoi à {user_id}: {e}")
        
        return sent_count
    
    async def broadcast_to_admins(self, event: str, data: dict) -> int:
        """
        Diffuser un événement à tous les ADMINS connectés uniquement.
        
        Pour les notifications de gestion (utilisateurs, feedbacks, etc.)
        
        Args:
            event: Type d'événement
            data: Données de l'événement
            
        Returns:
            Nombre de connexions notifiées
        """
        message = {"event": event, "data": data}
        sent_count = 0
        
        async with self._lock:
            # Envoyer aux connexions /admin/events/stream
            for queue in self._admin_connections:
                try:
                    await queue.put(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"SSE: Erreur broadcast admin: {e}")
            
            # Envoyer aux connexions /stream des utilisateurs ADMIN seulement
            for user_id, connections in self._connections.items():
                for queue, role in connections:
                    if role == "ADMIN":
                        try:
                            await queue.put(message)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"SSE: Erreur broadcast à admin {user_id}: {e}")
        
        logger.info(f"SSE: Broadcast admin envoyé à {sent_count} connexion(s)")
        return sent_count
    
    async def broadcast_to_admins_and_managers(self, event: str, data: dict) -> int:
        """
        Diffuser un événement à tous les ADMINS et MANAGERS connectés.
        
        Pour les notifications de documents (traitement terminé, échec, etc.)
        
        Args:
            event: Type d'événement
            data: Données de l'événement
            
        Returns:
            Nombre de connexions notifiées
        """
        message = {"event": event, "data": data}
        sent_count = 0
        
        async with self._lock:
            # Envoyer aux connexions /admin/events/stream
            for queue in self._admin_connections:
                try:
                    await queue.put(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"SSE: Erreur broadcast: {e}")
            
            # Envoyer aux connexions /stream des ADMIN et MANAGER
            for user_id, connections in self._connections.items():
                for queue, role in connections:
                    if role in ("ADMIN", "MANAGER"):
                        try:
                            await queue.put(message)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"SSE: Erreur broadcast à {role} {user_id}: {e}")
        
        logger.info(f"SSE: Broadcast admin+manager envoyé à {sent_count} connexion(s)")
        return sent_count
    
    async def broadcast_dashboard_update(self, data: dict) -> int:
        """Diffuser une mise à jour dashboard à tous."""
        message = {"event": "dashboard_update", "data": data}
        sent_count = 0
        
        async with self._lock:
            for user_id, queues in self._dashboard_connections.items():
                for queue in queues:
                    try:
                        await queue.put(message)
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"SSE: Erreur dashboard update: {e}")
        
        return sent_count
    
    def get_connection_stats(self) -> dict:
        """Obtenir les statistiques de connexion."""
        admin_user_connections = sum(
            1 for connections in self._connections.values()
            for _, role in connections if role == "ADMIN"
        )
        return {
            "user_connections": sum(len(q) for q in self._connections.values()),
            "unique_users": len(self._connections),
            "admin_connections": len(self._admin_connections),
            "admin_user_connections": admin_user_connections,
            "dashboard_connections": sum(len(q) for q in self._dashboard_connections.values())
        }


# Instance globale du gestionnaire SSE
sse_manager = SSEConnectionManager()


# ==============================================================================
# NOTIFICATION SERVICE
# ==============================================================================

class NotificationService:
    """
    Service de gestion des notifications.
    
    Fournit toutes les opérations CRUD et la diffusion SSE.
    """
    
    # =========================================================================
    # CRÉATION
    # =========================================================================
    
    @staticmethod
    async def create_notification(
        db: Session,
        notification_data: NotificationCreate,
        broadcast_sse: bool = True
    ) -> Notification:
        """
        Créer une nouvelle notification.
        
        Args:
            db: Session de base de données
            notification_data: Données de la notification
            broadcast_sse: Envoyer via SSE immédiatement
            
        Returns:
            Notification créée
        """
        notification = Notification(
            user_id=notification_data.user_id,
            type=notification_data.type,
            priority=notification_data.priority,
            title=notification_data.title,
            message=notification_data.message,
            data=notification_data.data,
            expires_at=notification_data.expires_at
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        logger.info(
            f"Notification créée: {notification.id} "
            f"(type={notification.type.value}, user={notification.user_id})"
        )
        
        # Diffuser via SSE si demandé
        if broadcast_sse:
            await NotificationService._broadcast_notification(notification)
        
        return notification
    
    @staticmethod
    async def _broadcast_notification(notification: Notification) -> None:
        """Diffuser une notification via SSE."""
        # Utiliser NotificationResponse pour la sérialisation sûre
        try:
            response = NotificationResponse.model_validate(notification)
            event_data = response.model_dump(mode='json')
        except Exception as e:
            # Fallback sur to_dict() si le modèle l'implémente
            logger.warning(f"Fallback sur to_dict: {e}")
            if hasattr(notification, 'to_dict'):
                event_data = notification.to_dict()
            else:
                # Construction manuelle
                event_data = {
                    "id": str(notification.id),
                    "user_id": str(notification.user_id) if notification.user_id else None,
                    "type": notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
                    "priority": notification.priority.value if hasattr(notification.priority, 'value') else str(notification.priority),
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data,
                    "is_read": notification.is_read,
                    "is_dismissed": notification.is_dismissed,
                    "created_at": notification.created_at.isoformat() + 'Z' if notification.created_at else None,
                    "read_at": notification.read_at.isoformat() + 'Z' if notification.read_at else None,
                    "expires_at": notification.expires_at.isoformat() + 'Z' if notification.expires_at else None,
                    "icon": notification.icon if hasattr(notification, 'icon') else "Bell",
                    "color": notification.color if hasattr(notification, 'color') else "#3b82f6"
                }
        
        if notification.user_id:
            # Notification à un utilisateur spécifique
            sent = await sse_manager.send_to_user(
                str(notification.user_id),
                "notification",
                event_data
            )
            logger.info(f"SSE: Notification {notification.id} envoyée à user {notification.user_id} ({sent} connexion(s))")
        else:
            # Notification broadcast - déterminer les destinataires selon le type
            notification_type = notification.type.value if hasattr(notification.type, 'value') else str(notification.type)
            
            # Types de notifications pour documents → admins + managers
            document_types = ['DOCUMENT_COMPLETED', 'DOCUMENT_FAILED', 'DOCUMENT_UPLOADED']
            
            if notification_type in document_types:
                # Documents : broadcast aux admins ET managers
                sent = await sse_manager.broadcast_to_admins_and_managers("notification", event_data)
                logger.info(f"SSE: Notification {notification.id} broadcast aux admins+managers ({sent} connexion(s))")
            else:
                # Autres (utilisateurs, feedbacks, système) : admins uniquement
                sent = await sse_manager.broadcast_to_admins("notification", event_data)
                logger.info(f"SSE: Notification {notification.id} broadcast aux admins ({sent} connexion(s))")
    
    # =========================================================================
    # NOTIFICATIONS PRÉDÉFINIES
    # =========================================================================
    
    @staticmethod
    async def notify_document_uploaded(
        db: Session,
        document_id: UUID,
        filename: str,
        user_id: UUID,
        uploaded_by_name: str
    ) -> Notification:
        """Notification: document uploadé."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.DOCUMENT_UPLOADED,
                priority=NotificationPriority.LOW,
                title="Document uploadé",
                message=f'Le document "{filename}" a été uploadé avec succès.',
                data={
                    "document_id": str(document_id),
                    "filename": filename,
                    "uploaded_by": uploaded_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_document_completed(
        db: Session,
        document_id: UUID,
        filename: str,
        user_id: UUID,
        total_chunks: int,
        processing_time: float,
        broadcast_sse: bool = True
    ) -> Notification:
        """
        Notification: traitement document terminé.
        
        - Pour les USER : notification personnelle uniquement
        - Pour les ADMIN/MANAGER : broadcast uniquement (pas de doublon)
        
        Args:
            broadcast_sse: Si True, diffuse via SSE. Mettre à False depuis les workers Celery.
        """
        from app.models.user import User, UserRole
        
        # Récupérer le rôle de l'uploader
        uploader = db.query(User).filter(User.id == user_id).first()
        uploader_role = uploader.role if uploader else UserRole.USER
        
        notification = None
        
        # Si l'uploader est un USER, créer une notification personnelle
        if uploader_role == UserRole.USER:
            notification = await NotificationService.create_notification(
                db,
                NotificationCreate(
                    user_id=user_id,
                    type=NotificationType.DOCUMENT_COMPLETED,
                    priority=NotificationPriority.MEDIUM,
                    title="Traitement terminé",
                    message=f'Le document "{filename}" est maintenant disponible ({total_chunks} chunks).',
                    data={
                        "document_id": str(document_id),
                        "filename": filename,
                        "total_chunks": total_chunks,
                        "processing_time_seconds": processing_time
                    }
                ),
                broadcast_sse=broadcast_sse
            )
        
        # Broadcast aux admins/managers (une seule notification pour tous)
        broadcast_notif = await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins/managers
                type=NotificationType.DOCUMENT_COMPLETED,
                priority=NotificationPriority.LOW,
                title="Nouveau document disponible",
                message=f'Le document "{filename}" a été traité avec succès ({total_chunks} chunks).',
                data={
                    "document_id": str(document_id),
                    "filename": filename,
                    "total_chunks": total_chunks,
                    "processing_time_seconds": processing_time,
                    "uploaded_by": str(user_id)
                }
            ),
            broadcast_sse=broadcast_sse
        )
        
        # Retourner la notification personnelle si créée, sinon le broadcast
        return notification or broadcast_notif
    
    @staticmethod
    async def notify_document_failed(
        db: Session,
        document_id: UUID,
        filename: str,
        user_id: UUID,
        error_message: str,
        broadcast_sse: bool = True
    ) -> Notification:
        """
        Notification: échec traitement document.
        
        - Pour les USER : notification personnelle uniquement
        - Pour les ADMIN/MANAGER : broadcast uniquement (pas de doublon)
        
        Args:
            broadcast_sse: Si True, diffuse via SSE. Mettre à False depuis les workers Celery.
        """
        from app.models.user import User, UserRole
        
        # Récupérer le rôle de l'uploader
        uploader = db.query(User).filter(User.id == user_id).first()
        uploader_role = uploader.role if uploader else UserRole.USER
        
        notification = None
        
        # Si l'uploader est un USER, créer une notification personnelle
        if uploader_role == UserRole.USER:
            notification = await NotificationService.create_notification(
                db,
                NotificationCreate(
                    user_id=user_id,
                    type=NotificationType.DOCUMENT_FAILED,
                    priority=NotificationPriority.HIGH,
                    title="Échec du traitement",
                    message=f'Le traitement de "{filename}" a échoué: {error_message}',
                    data={
                        "document_id": str(document_id),
                        "filename": filename,
                        "error": error_message
                    }
                ),
                broadcast_sse=broadcast_sse
            )
        
        # Broadcast aux admins/managers
        broadcast_notif = await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins/managers
                type=NotificationType.DOCUMENT_FAILED,
                priority=NotificationPriority.MEDIUM,
                title="Échec traitement document",
                message=f'Le document "{filename}" a échoué: {error_message}',
                data={
                    "document_id": str(document_id),
                    "filename": filename,
                    "error": error_message,
                    "uploaded_by": str(user_id)
                }
            ),
            broadcast_sse=broadcast_sse
        )
        
        return notification or broadcast_notif
    
    @staticmethod
    async def notify_feedback_received(
        db: Session,
        feedback_id: UUID,
        message_id: UUID,
        user_name: str,
        rating: str,
        comment: Optional[str] = None
    ) -> Notification:
        """Notification: nouveau feedback (pour admins)."""
        icon = "👍" if rating == "THUMBS_UP" else "👎"
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.FEEDBACK_RECEIVED if rating == "THUMBS_UP" else NotificationType.FEEDBACK_NEGATIVE,
                priority=NotificationPriority.MEDIUM if rating == "THUMBS_UP" else NotificationPriority.HIGH,
                title=f"Nouveau feedback {icon}",
                message=f"{user_name} a donné un feedback {rating}" + (f": {comment}" if comment else ""),
                data={
                    "feedback_id": str(feedback_id),
                    "message_id": str(message_id),
                    "user_name": user_name,
                    "rating": rating,
                    "comment": comment
                }
            )
        )
    
    # =========================================================================
    # NOTIFICATIONS USERS
    # =========================================================================
    
    @staticmethod
    async def notify_user_created(
        db: Session,
        created_user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        role: str,
        created_by_name: str
    ) -> Notification:
        """Notification: nouvel utilisateur créé (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_CREATED,
                priority=NotificationPriority.LOW,
                title="Nouvel utilisateur créé",
                message=f"{created_by_name} a créé l'utilisateur {prenom} {nom} ({matricule}) avec le rôle {role}.",
                data={
                    "user_id": str(created_user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "role": role,
                    "created_by": created_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_user_updated(
        db: Session,
        updated_user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        updated_by_name: str,
        changes: Optional[Dict] = None
    ) -> Notification:
        """Notification: utilisateur modifié (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_UPDATED,
                priority=NotificationPriority.LOW,
                title="Utilisateur modifié",
                message=f"{updated_by_name} a modifié l'utilisateur {prenom} {nom} ({matricule}).",
                data={
                    "user_id": str(updated_user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "updated_by": updated_by_name,
                    "changes": changes or {}
                }
            )
        )
    
    @staticmethod
    async def notify_user_deleted(
        db: Session,
        deleted_user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        deleted_by_name: str
    ) -> Notification:
        """Notification: utilisateur supprimé (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_DELETED,
                priority=NotificationPriority.MEDIUM,
                title="Utilisateur supprimé",
                message=f"{deleted_by_name} a supprimé l'utilisateur {prenom} {nom} ({matricule}).",
                data={
                    "user_id": str(deleted_user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "deleted_by": deleted_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_user_activated(
        db: Session,
        user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        activated_by_name: str
    ) -> Notification:
        """Notification: utilisateur activé (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_ACTIVATED,
                priority=NotificationPriority.LOW,
                title="Utilisateur activé",
                message=f"{activated_by_name} a activé le compte de {prenom} {nom} ({matricule}).",
                data={
                    "user_id": str(user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "activated_by": activated_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_user_deactivated(
        db: Session,
        user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        deactivated_by_name: str
    ) -> Notification:
        """Notification: utilisateur désactivé (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_DEACTIVATED,
                priority=NotificationPriority.MEDIUM,
                title="Utilisateur désactivé",
                message=f"{deactivated_by_name} a désactivé le compte de {prenom} {nom} ({matricule}).",
                data={
                    "user_id": str(user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "deactivated_by": deactivated_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_user_password_reset(
        db: Session,
        user_id: UUID,
        matricule: str,
        nom: str,
        prenom: str,
        reset_by_name: str
    ) -> Notification:
        """Notification: mot de passe réinitialisé (pour admins)."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=None,  # Broadcast aux admins
                type=NotificationType.USER_PASSWORD_RESET,
                priority=NotificationPriority.MEDIUM,
                title="Mot de passe réinitialisé",
                message=f"{reset_by_name} a réinitialisé le mot de passe de {prenom} {nom} ({matricule}).",
                data={
                    "user_id": str(user_id),
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "reset_by": reset_by_name
                }
            )
        )
    
    @staticmethod
    async def notify_system(
        db: Session,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM_INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        user_id: Optional[UUID] = None,
        data: Optional[Dict] = None
    ) -> Notification:
        """Notification système générique."""
        return await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=notification_type,
                priority=priority,
                title=title,
                message=message,
                data=data or {}
            )
        )
    
    # =========================================================================
    # LECTURE
    # =========================================================================
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: UUID,
        user_role: UserRole,
        filters: Optional[NotificationFilters] = None,
        page: int = 1,
        page_size: int = 20,
        include_dismissed: bool = False
    ) -> NotificationListResponse:
        """
        Récupérer les notifications d'un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            user_role: Rôle de l'utilisateur
            filters: Filtres optionnels
            page: Numéro de page
            page_size: Taille de page
            include_dismissed: Inclure les notifications rejetées
            
        Returns:
            Liste paginée des notifications
        """
        query = db.query(Notification)
        
        # Filtre par utilisateur selon le rôle
        if user_role == UserRole.ADMIN:
            # Admin voit ses notifications + tous les broadcasts
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)
                )
            )
        elif user_role == UserRole.MANAGER:
            # Manager voit ses notifications + broadcasts documents
            # Types de notifications documents que les managers peuvent voir
            document_types = [
                NotificationType.DOCUMENT_COMPLETED,
                NotificationType.DOCUMENT_FAILED,
                NotificationType.DOCUMENT_UPLOADED
            ]
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    and_(
                        Notification.user_id.is_(None),
                        Notification.type.in_(document_types)
                    )
                )
            )
        else:
            # USER voit seulement ses notifications personnelles
            query = query.filter(Notification.user_id == user_id)
        
        # Exclure les rejetées sauf si demandé
        if not include_dismissed:
            query = query.filter(Notification.is_dismissed == False)
        
        # Exclure les expirées
        query = query.filter(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )
        
        # Appliquer les filtres
        if filters:
            if filters.types:
                query = query.filter(Notification.type.in_(filters.types))
            if filters.priorities:
                query = query.filter(Notification.priority.in_(filters.priorities))
            if filters.is_read is not None:
                query = query.filter(Notification.is_read == filters.is_read)
            if filters.start_date:
                query = query.filter(Notification.created_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(Notification.created_at <= filters.end_date)
        
        # Compteurs
        total = query.count()
        unread_count = query.filter(Notification.is_read == False).count()
        
        # Pagination et tri
        notifications = (
            query
            .order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        # Calculer le nombre total de pages
        total_pages = (total + page_size - 1) // page_size
        
        return NotificationListResponse(
            items=[
                NotificationResponse(
                    id=n.id,
                    user_id=n.user_id,
                    type=n.type,
                    priority=n.priority,
                    title=n.title,
                    message=n.message,
                    data=n.data or {},
                    is_read=n.is_read,
                    is_dismissed=n.is_dismissed,
                    created_at=n.created_at,
                    read_at=n.read_at,
                    expires_at=n.expires_at,
                    icon=n.icon,
                    color=n.color
                )
                for n in notifications
            ],
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    @staticmethod
    def get_unread_count(
        db: Session,
        user_id: UUID,
        user_role: UserRole
    ) -> int:
        """Compter les notifications non lues."""
        query = db.query(func.count(Notification.id))
        
        if user_role == UserRole.ADMIN:
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)
                )
            )
        elif user_role == UserRole.MANAGER:
            # Manager voit ses notifications + broadcasts documents
            document_types = [
                NotificationType.DOCUMENT_COMPLETED,
                NotificationType.DOCUMENT_FAILED,
                NotificationType.DOCUMENT_UPLOADED
            ]
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    and_(
                        Notification.user_id.is_(None),
                        Notification.type.in_(document_types)
                    )
                )
            )
        else:
            query = query.filter(Notification.user_id == user_id)
        
        query = query.filter(
            Notification.is_read == False,
            Notification.is_dismissed == False,
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )
        
        return query.scalar() or 0
    
    # =========================================================================
    # MISE À JOUR
    # =========================================================================
    
    @staticmethod
    def mark_as_read(
        db: Session,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """Marquer une notification comme lue."""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None)
            )
        ).first()
        
        if notification:
            notification.mark_as_read()
            db.commit()
            db.refresh(notification)
        
        return notification
    
    @staticmethod
    def mark_all_as_read(
        db: Session,
        user_id: UUID,
        user_role: UserRole
    ) -> int:
        """Marquer toutes les notifications comme lues."""
        query = db.query(Notification).filter(
            Notification.is_read == False,
            Notification.is_dismissed == False
        )
        
        if user_role == UserRole.ADMIN:
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)
                )
            )
        elif user_role == UserRole.MANAGER:
            document_types = [
                NotificationType.DOCUMENT_COMPLETED,
                NotificationType.DOCUMENT_FAILED,
                NotificationType.DOCUMENT_UPLOADED
            ]
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    and_(
                        Notification.user_id.is_(None),
                        Notification.type.in_(document_types)
                    )
                )
            )
        else:
            query = query.filter(Notification.user_id == user_id)
        
        count = query.update({
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        }, synchronize_session=False)
        
        db.commit()
        return count
    
    @staticmethod
    def dismiss_notification(
        db: Session,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """Rejeter une notification."""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None)
            )
        ).first()
        
        if notification:
            notification.dismiss()
            db.commit()
            db.refresh(notification)
        
        return notification
    
    @staticmethod
    def dismiss_all(
        db: Session,
        user_id: UUID,
        user_role: UserRole
    ) -> int:
        """Rejeter toutes les notifications."""
        query = db.query(Notification).filter(
            Notification.is_dismissed == False
        )
        
        if user_role == UserRole.ADMIN:
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)
                )
            )
        elif user_role == UserRole.MANAGER:
            document_types = [
                NotificationType.DOCUMENT_COMPLETED,
                NotificationType.DOCUMENT_FAILED,
                NotificationType.DOCUMENT_UPLOADED
            ]
            query = query.filter(
                or_(
                    Notification.user_id == user_id,
                    and_(
                        Notification.user_id.is_(None),
                        Notification.type.in_(document_types)
                    )
                )
            )
        else:
            query = query.filter(Notification.user_id == user_id)
        
        count = query.update({
            Notification.is_dismissed: True,
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        }, synchronize_session=False)
        
        db.commit()
        return count
    
    # =========================================================================
    # SSE STREAMS
    # =========================================================================
    
    @staticmethod
    async def stream_user_notifications(
        user_id: UUID,
        user_role: str = "USER",
        initial_unread_count: int = 0
    ) -> AsyncGenerator[str, None]:
        """
        Générateur de stream SSE pour les notifications utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            user_role: Rôle de l'utilisateur (pour recevoir les broadcasts admin)
            initial_unread_count: Nombre initial de notifications non lues
            
        Yields:
            Événements SSE formatés
        """
        queue = await sse_manager.connect_user(str(user_id), user_role)
        
        try:
            # Envoyer le compteur initial
            yield NotificationService._format_sse_event(
                "connected",
                {"unread_count": initial_unread_count}
            )
            
            # Heartbeat pour maintenir la connexion
            heartbeat_interval = 30  # secondes
            
            while True:
                try:
                    # Attendre un événement avec timeout
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=heartbeat_interval
                    )
                    yield NotificationService._format_sse_event(
                        message["event"],
                        message["data"]
                    )
                except asyncio.TimeoutError:
                    # Envoyer un heartbeat
                    yield NotificationService._format_sse_event(
                        "heartbeat",
                        {"timestamp": datetime.utcnow().isoformat()}
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.disconnect_user(str(user_id), queue)
    
    @staticmethod
    async def stream_admin_events() -> AsyncGenerator[str, None]:
        """
        Générateur de stream SSE pour les événements admin.
        
        Yields:
            Événements SSE formatés (feedbacks, documents, etc.)
        """
        queue = await sse_manager.connect_admin()
        
        try:
            yield NotificationService._format_sse_event(
                "connected",
                {"message": "Admin events stream connected"}
            )
            
            heartbeat_interval = 30
            
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=heartbeat_interval
                    )
                    yield NotificationService._format_sse_event(
                        message["event"],
                        message["data"]
                    )
                except asyncio.TimeoutError:
                    yield NotificationService._format_sse_event(
                        "heartbeat",
                        {"timestamp": datetime.utcnow().isoformat()}
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.disconnect_admin(queue)
    
    @staticmethod
    async def stream_dashboard_stats(
        user_id: UUID
    ) -> AsyncGenerator[str, None]:
        """
        Générateur de stream SSE pour les statistiques dashboard.
        
        Yields:
            Événements SSE avec stats mises à jour
        """
        queue = await sse_manager.connect_dashboard(str(user_id))
        
        try:
            yield NotificationService._format_sse_event(
                "connected",
                {"message": "Dashboard stats stream connected"}
            )
            
            heartbeat_interval = 30
            
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=heartbeat_interval
                    )
                    yield NotificationService._format_sse_event(
                        message["event"],
                        message["data"]
                    )
                except asyncio.TimeoutError:
                    yield NotificationService._format_sse_event(
                        "heartbeat",
                        {"timestamp": datetime.utcnow().isoformat()}
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.disconnect_dashboard(str(user_id), queue)
    
    @staticmethod
    def _format_sse_event(event: str, data: dict) -> str:
        """Formater un événement SSE."""
        json_data = json.dumps(data, default=str, ensure_ascii=False)
        return f"event: {event}\ndata: {json_data}\n\n"
    
    # =========================================================================
    # NETTOYAGE
    # =========================================================================
    
    @staticmethod
    def cleanup_old_notifications(
        db: Session,
        days: int = 30
    ) -> int:
        """
        Supprimer les anciennes notifications.
        
        Args:
            db: Session de base de données
            days: Nombre de jours à conserver
            
        Returns:
            Nombre de notifications supprimées
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = db.query(Notification).filter(
            or_(
                # Notifications lues et anciennes
                and_(
                    Notification.is_read == True,
                    Notification.created_at < cutoff_date
                ),
                # Notifications expirées
                and_(
                    Notification.expires_at.isnot(None),
                    Notification.expires_at < datetime.utcnow()
                )
            )
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Nettoyage notifications: {count} notifications supprimées")
        
        return count


# ==============================================================================
# DOCUMENT STATUS SSE SERVICE
# ==============================================================================

class DocumentStatusSSE:
    """
    Service SSE spécifique pour le suivi du traitement des documents.
    """
    
    # Connexions par document_id
    _document_connections: Dict[str, List[asyncio.Queue]] = defaultdict(list)
    _lock = asyncio.Lock()
    
    @classmethod
    async def connect(cls, document_id: str) -> asyncio.Queue:
        """Connecter au suivi d'un document."""
        queue = asyncio.Queue()
        async with cls._lock:
            cls._document_connections[document_id].append(queue)
        return queue
    
    @classmethod
    async def disconnect(cls, document_id: str, queue: asyncio.Queue) -> None:
        """Déconnecter du suivi d'un document."""
        async with cls._lock:
            if document_id in cls._document_connections:
                try:
                    cls._document_connections[document_id].remove(queue)
                    if not cls._document_connections[document_id]:
                        del cls._document_connections[document_id]
                except ValueError:
                    pass
    
    @classmethod
    async def send_status_update(
        cls,
        document_id: str,
        status: str,
        stage: Optional[str] = None,
        progress: int = 0,
        error_message: Optional[str] = None,
        original_filename: str = "",
        total_chunks: Optional[int] = None,
        processing_time: Optional[float] = None
    ) -> int:
        """
        Envoyer une mise à jour de statut.
        
        Returns:
            Nombre de connexions notifiées
        """
        data = {
            "document_id": document_id,
            "status": status,
            "stage": stage,
            "progress": progress,
            "error_message": error_message,
            "original_filename": original_filename,
            "total_chunks": total_chunks,
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = {"event": "status", "data": data}
        sent_count = 0
        
        async with cls._lock:
            queues = cls._document_connections.get(document_id, [])
            for queue in queues:
                try:
                    await queue.put(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"SSE Document: Erreur envoi status: {e}")
        
        return sent_count
    
    @classmethod
    async def stream_document_status(
        cls,
        document_id: str,
        initial_status: dict
    ) -> AsyncGenerator[str, None]:
        """
        Générateur de stream SSE pour le status d'un document.
        
        Args:
            document_id: ID du document
            initial_status: Status initial du document
            
        Yields:
            Événements SSE formatés
        """
        queue = await cls.connect(document_id)
        
        try:
            # Envoyer le status initial
            yield NotificationService._format_sse_event("status", initial_status)
            
            heartbeat_interval = 10  # Plus fréquent pour le suivi document
            
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=heartbeat_interval
                    )
                    yield NotificationService._format_sse_event(
                        message["event"],
                        message["data"]
                    )
                    
                    # Si terminé ou en erreur, fermer le stream
                    if message["data"].get("status") in ["COMPLETED", "FAILED"]:
                        yield NotificationService._format_sse_event(
                            "complete",
                            message["data"]
                        )
                        break
                        
                except asyncio.TimeoutError:
                    yield NotificationService._format_sse_event(
                        "heartbeat",
                        {"document_id": document_id}
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await cls.disconnect(document_id, queue)