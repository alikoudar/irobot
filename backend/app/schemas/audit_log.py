# -*- coding: utf-8 -*-
"""
Schemas Pydantic pour les Audit Logs.

Définit les schemas de validation pour la consultation et le filtrage
des logs d'audit du système.

Sprint 13 - Complément : Endpoint Audit Logs Admin
Auteur: IroBot Team
Date: 2025-12-02
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_serializer


# =============================================================================
# ENUMS
# =============================================================================

class AuditActionEnum(str, Enum):
    """Types d'actions pour les logs d'audit."""
    # Authentification
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    
    # Catégories
    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    CATEGORY_DELETED = "CATEGORY_DELETED"
    
    # Documents
    DOCUMENT_CREATED = "DOCUMENT_CREATED"
    RETRY = "RETRY"
    
    # Utilisateurs
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    USERS_IMPORTED = "USERS_IMPORTED"
    
    # Configuration
    CONFIG_UPDATE = "CONFIG_UPDATE"


class EntityTypeEnum(str, Enum):
    """Types d'entités pour les logs d'audit."""
    AUTH = "AUTH"
    USER = "USER"
    DOCUMENT = "DOCUMENT"
    CATEGORY = "CATEGORY"
    CONFIG = "CONFIG"


# =============================================================================
# SCHEMAS DE FILTRAGE
# =============================================================================

class AuditLogFilterParams(BaseModel):
    """Paramètres de filtrage pour les logs d'audit."""
    
    user_id: Optional[UUID] = Field(
        default=None,
        description="Filtrer par ID utilisateur"
    )
    action: Optional[AuditActionEnum] = Field(
        default=None,
        description="Filtrer par type d'action"
    )
    entity_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="Filtrer par type d'entité"
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Date de début (incluse)"
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Date de fin (incluse)"
    )
    search: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Recherche textuelle dans les détails"
    )


# =============================================================================
# SCHEMAS DE RÉPONSE
# =============================================================================

class AuditLogUserInfo(BaseModel):
    """Informations utilisateur simplifiées pour les logs."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    matricule: str
    nom: str
    prenom: str
    email: str


class AuditLogResponse(BaseModel):
    """Schema de réponse pour un log d'audit."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    # Informations utilisateur (optionnel, pour l'affichage enrichi)
    user: Optional[AuditLogUserInfo] = None
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO 8601 + Z (format UTC)."""
        return dt.isoformat() + 'Z' if dt else None


class AuditLogListResponse(BaseModel):
    """Schema de réponse pour une liste paginée de logs d'audit."""
    
    items: List[AuditLogResponse]
    total: int = Field(..., ge=0, description="Nombre total de résultats")
    page: int = Field(..., ge=1, description="Page actuelle")
    page_size: int = Field(..., ge=1, le=100, description="Taille de la page")
    total_pages: int = Field(..., ge=0, description="Nombre total de pages")
    
    # Filtres appliqués (pour référence)
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filtres appliqués à la requête"
    )


# =============================================================================
# SCHEMAS DE STATISTIQUES
# =============================================================================

class AuditLogStats(BaseModel):
    """Statistiques globales des logs d'audit."""
    
    total_logs: int = Field(default=0, description="Nombre total de logs")
    logs_today: int = Field(default=0, description="Logs d'aujourd'hui")
    logs_this_week: int = Field(default=0, description="Logs de la semaine")
    logs_this_month: int = Field(default=0, description="Logs du mois")
    
    # Par type d'action
    by_action: Dict[str, int] = Field(
        default_factory=dict,
        description="Nombre de logs par type d'action"
    )
    
    # Par type d'entité
    by_entity_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Nombre de logs par type d'entité"
    )
    
    # Dernière activité
    last_activity: Optional[datetime] = None
    
    @field_serializer('last_activity')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO 8601 + Z (format UTC)."""
        return dt.isoformat() + 'Z' if dt else None


class AuditLogActivityByDate(BaseModel):
    """Activité des logs par date."""
    
    date: date
    count: int = Field(..., ge=0)
    
    # Détail par action (optionnel)
    by_action: Optional[Dict[str, int]] = None


class AuditLogActivityResponse(BaseModel):
    """Réponse pour l'activité des logs sur une période."""
    
    start_date: date
    end_date: date
    total: int = Field(..., ge=0)
    daily_activity: List[AuditLogActivityByDate]


# =============================================================================
# SCHEMAS D'EXPORT
# =============================================================================

class AuditLogExportRequest(BaseModel):
    """Paramètres pour l'export des logs d'audit."""
    
    format: str = Field(
        default="csv",
        pattern="^(csv|json)$",
        description="Format d'export : csv ou json"
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Date de début"
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Date de fin"
    )
    action: Optional[AuditActionEnum] = Field(
        default=None,
        description="Filtrer par action"
    )
    entity_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="Filtrer par type d'entité"
    )
    max_records: int = Field(
        default=10000,
        ge=1,
        le=50000,
        description="Nombre maximum d'enregistrements à exporter"
    )


# =============================================================================
# CONSTANTES POUR RÉFÉRENCE FRONTEND
# =============================================================================

# Liste des actions disponibles (pour le frontend)
AVAILABLE_ACTIONS = [
    {"value": "LOGIN_SUCCESS", "label": "Connexion réussie", "category": "AUTH"},
    {"value": "LOGIN_FAILED", "label": "Connexion échouée", "category": "AUTH"},
    {"value": "PROFILE_UPDATE", "label": "Mise à jour profil", "category": "AUTH"},
    {"value": "PASSWORD_RESET_REQUEST", "label": "Demande réinitialisation MDP", "category": "AUTH"},
    {"value": "CATEGORY_CREATED", "label": "Catégorie créée", "category": "CATEGORY"},
    {"value": "CATEGORY_UPDATED", "label": "Catégorie modifiée", "category": "CATEGORY"},
    {"value": "CATEGORY_DELETED", "label": "Catégorie supprimée", "category": "CATEGORY"},
    {"value": "DOCUMENT_CREATED", "label": "Document créé", "category": "DOCUMENT"},
    {"value": "RETRY", "label": "Réessai traitement", "category": "DOCUMENT"},
    {"value": "USER_CREATED", "label": "Utilisateur créé", "category": "USER"},
    {"value": "USER_UPDATED", "label": "Utilisateur modifié", "category": "USER"},
    {"value": "USER_DELETED", "label": "Utilisateur supprimé", "category": "USER"},
    {"value": "PASSWORD_CHANGED", "label": "Mot de passe changé", "category": "USER"},
    {"value": "PASSWORD_RESET", "label": "Mot de passe réinitialisé", "category": "USER"},
    {"value": "USERS_IMPORTED", "label": "Utilisateurs importés", "category": "USER"},
    {"value": "CONFIG_UPDATE", "label": "Configuration modifiée", "category": "CONFIG"},
]

# Liste des types d'entités disponibles (pour le frontend)
AVAILABLE_ENTITY_TYPES = [
    {"value": "AUTH", "label": "Authentification", "icon": "🔐"},
    {"value": "USER", "label": "Utilisateur", "icon": "👤"},
    {"value": "DOCUMENT", "label": "Document", "icon": "📄"},
    {"value": "CATEGORY", "label": "Catégorie", "icon": "📁"},
    {"value": "CONFIG", "label": "Configuration", "icon": "⚙️"},
]