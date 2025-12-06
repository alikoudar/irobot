# ==============================================================================
# SCHEMAS NOTIFICATION - SPRINT 14
# ==============================================================================
# Schémas Pydantic pour la validation des notifications
# ==============================================================================

from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_serializer


# ==============================================================================
# ENUMS
# ==============================================================================

class NotificationType(str, Enum):
    """Types de notifications."""
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"
    DOCUMENT_COMPLETED = "DOCUMENT_COMPLETED"
    DOCUMENT_FAILED = "DOCUMENT_FAILED"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    FEEDBACK_NEGATIVE = "FEEDBACK_NEGATIVE"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_PASSWORD_RESET = "USER_PASSWORD_RESET"
    SYSTEM_INFO = "SYSTEM_INFO"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    STATS_UPDATE = "STATS_UPDATE"


class NotificationPriority(str, Enum):
    """Priorité des notifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ==============================================================================
# SCHEMAS BASE
# ==============================================================================

class NotificationBase(BaseModel):
    """Schéma de base pour les notifications."""
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str = Field(..., min_length=1, max_length=200)
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NotificationCreate(NotificationBase):
    """Schéma pour créer une notification."""
    user_id: Optional[UUID] = None  # NULL = tous les admins
    expires_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    """Schéma pour mettre à jour une notification."""
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class NotificationResponse(NotificationBase):
    """Schéma de réponse pour une notification."""
    id: UUID
    user_id: Optional[UUID]
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    read_at: Optional[datetime]
    expires_at: Optional[datetime]
    icon: str
    color: str
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('created_at', 'read_at', 'expires_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO format avec Z."""
        return dt.isoformat() + 'Z' if dt else None


class NotificationListResponse(BaseModel):
    """Réponse paginée des notifications."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int


# ==============================================================================
# SCHEMAS SSE
# ==============================================================================

class SSEEvent(BaseModel):
    """Événement SSE générique."""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None


class DocumentStatusEvent(BaseModel):
    """Événement SSE pour le statut d'un document."""
    document_id: UUID
    status: str
    stage: Optional[str] = None
    progress: int = Field(ge=0, le=100)
    error_message: Optional[str] = None
    original_filename: str
    total_chunks: Optional[int] = None
    processing_time: Optional[float] = None


class FeedbackEvent(BaseModel):
    """Événement SSE pour un nouveau feedback."""
    feedback_id: UUID
    message_id: UUID
    conversation_id: UUID
    user_id: UUID
    user_name: str
    rating: str  # positive, negative
    comment: Optional[str] = None
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO format avec Z."""
        return dt.isoformat() + 'Z' if dt else None


class DashboardStatsEvent(BaseModel):
    """Événement SSE pour les statistiques dashboard."""
    total_users: int
    total_documents: int
    total_conversations: int
    total_messages: int
    documents_processing: int
    cache_hit_rate: float
    feedbacks_today: int
    timestamp: datetime
    
    @field_serializer('timestamp')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO format avec Z."""
        return dt.isoformat() + 'Z' if dt else None


# ==============================================================================
# SCHEMAS BULK OPERATIONS
# ==============================================================================

class NotificationBulkAction(BaseModel):
    """Action en masse sur les notifications."""
    notification_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., pattern="^(read|dismiss|delete)$")


class NotificationBulkResponse(BaseModel):
    """Réponse pour les actions en masse."""
    success: bool
    affected_count: int
    message: str


# ==============================================================================
# SCHEMAS FILTRES
# ==============================================================================

class NotificationFilters(BaseModel):
    """Filtres pour la liste des notifications."""
    types: Optional[List[NotificationType]] = None
    priorities: Optional[List[NotificationPriority]] = None
    is_read: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ==============================================================================
# SCHEMAS SETTINGS
# ==============================================================================

class NotificationSettings(BaseModel):
    """Paramètres de notification utilisateur."""
    email_notifications: bool = True
    push_notifications: bool = True
    sound_enabled: bool = True
    
    # Types de notifications activés
    document_notifications: bool = True
    feedback_notifications: bool = True
    system_notifications: bool = True
    
    model_config = ConfigDict(from_attributes=True)