# ==============================================================================
# MODÈLE NOTIFICATION - SPRINT 14
# ==============================================================================
# Gestion des notifications temps réel pour les utilisateurs
# ==============================================================================

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID
import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class NotificationType(str, enum.Enum):
    """Types de notifications disponibles."""
    # Documents
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"
    DOCUMENT_COMPLETED = "DOCUMENT_COMPLETED"
    DOCUMENT_FAILED = "DOCUMENT_FAILED"
    
    # Feedbacks
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    FEEDBACK_NEGATIVE = "FEEDBACK_NEGATIVE"
    
    # Users
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_PASSWORD_RESET = "USER_PASSWORD_RESET"
    
    # Système
    SYSTEM_INFO = "SYSTEM_INFO"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    
    # Dashboard
    STATS_UPDATE = "STATS_UPDATE"


class NotificationPriority(str, enum.Enum):
    """Priorité des notifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Notification(Base):
    """
    Modèle pour les notifications utilisateur.
    
    Attributes:
        id: Identifiant unique
        user_id: Utilisateur destinataire (NULL = tous les admins)
        type: Type de notification
        priority: Priorité de la notification
        title: Titre de la notification
        message: Message détaillé
        data: Données JSON additionnelles (document_id, feedback_id, etc.)
        is_read: Notification lue ou non
        is_dismissed: Notification rejetée
        created_at: Date de création
        read_at: Date de lecture
        expires_at: Date d'expiration (optionnel)
    """
    
    __tablename__ = "notifications"
    
    # Identifiant
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Destinataire (NULL = broadcast aux admins)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Type et priorité
    type = Column(
        Enum(NotificationType),
        nullable=False,
        index=True
    )
    priority = Column(
        Enum(NotificationPriority),
        default=NotificationPriority.MEDIUM,
        nullable=False
    )
    
    # Contenu
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    
    # Données additionnelles (JSON)
    # Peut contenir: document_id, feedback_id, user_id source, etc.
    data = Column(JSON, nullable=True, default=dict)
    
    # État
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relations
    user = relationship("User", back_populates="notifications")
    
    # Index composites pour les requêtes fréquentes
    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
        Index('ix_notifications_created_at', 'created_at'),
        Index('ix_notifications_type_created', 'type', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Notification {self.id}: {self.type.value} - {self.title[:30]}>"
    
    def to_dict(self) -> dict:
        """Convertir la notification en dictionnaire."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "data": self.data or {},
            "is_read": self.is_read,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    def to_sse_event(self) -> dict:
        """Format pour envoi SSE."""
        return {
            "event": "notification",
            "data": self.to_dict()
        }
    
    def mark_as_read(self) -> None:
        """Marquer la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def dismiss(self) -> None:
        """Rejeter la notification."""
        self.is_dismissed = True
        if not self.is_read:
            self.mark_as_read()
    
    @property
    def is_expired(self) -> bool:
        """Vérifier si la notification a expiré."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Âge de la notification en secondes."""
        if self.created_at is None:
            return 0
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    @property
    def icon(self) -> str:
        """Icône associée au type de notification."""
        icons = {
            NotificationType.DOCUMENT_UPLOADED: "Upload",
            NotificationType.DOCUMENT_PROCESSING: "Loading",
            NotificationType.DOCUMENT_COMPLETED: "SuccessFilled",
            NotificationType.DOCUMENT_FAILED: "CircleCloseFilled",
            NotificationType.FEEDBACK_RECEIVED: "ChatLineSquare",
            NotificationType.FEEDBACK_NEGATIVE: "WarningFilled",
            NotificationType.USER_CREATED: "UserFilled",
            NotificationType.USER_UPDATED: "Edit",
            NotificationType.USER_DELETED: "Delete",
            NotificationType.USER_ACTIVATED: "CircleCheckFilled",
            NotificationType.USER_DEACTIVATED: "CircleCloseFilled",
            NotificationType.USER_PASSWORD_RESET: "Lock",
            NotificationType.SYSTEM_INFO: "InfoFilled",
            NotificationType.SYSTEM_WARNING: "WarningFilled",
            NotificationType.SYSTEM_ERROR: "CircleCloseFilled",
            NotificationType.STATS_UPDATE: "TrendCharts",
        }
        return icons.get(self.type, "Bell")
    
    @property
    def color(self) -> str:
        """Couleur associée au type/priorité de notification."""
        # Par priorité d'abord
        if self.priority == NotificationPriority.URGENT:
            return "#ef4444"  # Rouge
        if self.priority == NotificationPriority.HIGH:
            return "#f59e0b"  # Orange
        
        # Puis par type
        colors = {
            NotificationType.DOCUMENT_COMPLETED: "#10b981",  # Vert
            NotificationType.DOCUMENT_FAILED: "#ef4444",     # Rouge
            NotificationType.FEEDBACK_NEGATIVE: "#f59e0b",   # Orange
            NotificationType.USER_CREATED: "#10b981",        # Vert
            NotificationType.USER_ACTIVATED: "#10b981",      # Vert
            NotificationType.USER_DELETED: "#ef4444",        # Rouge
            NotificationType.USER_DEACTIVATED: "#f59e0b",    # Orange
            NotificationType.SYSTEM_ERROR: "#ef4444",        # Rouge
            NotificationType.SYSTEM_WARNING: "#f59e0b",      # Orange
        }
        return colors.get(self.type, "#3b82f6")  # Bleu par défaut