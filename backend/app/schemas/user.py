"""Schémas Pydantic pour la gestion des utilisateurs et l'authentification."""
from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole


# ============================================================================
# SCHÉMAS BASE
# ============================================================================

class UserBase(BaseModel):
    """Schéma de base pour un utilisateur."""
    
    matricule: str = Field(..., min_length=3, max_length=50, description="Matricule unique de l'utilisateur")
    email: EmailStr = Field(..., description="Adresse email")
    nom: str = Field(..., min_length=1, max_length=100, description="Nom de famille")
    prenom: str = Field(..., min_length=1, max_length=100, description="Prénom")
    role: UserRole = Field(default=UserRole.USER, description="Rôle de l'utilisateur")
    is_active: bool = Field(default=True, description="Statut actif/inactif")
    
    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """
        Valide que l'email appartient au domaine @beac.int.
        
        Args:
            v: Adresse email à valider
            
        Returns:
            str: Email validé
            
        Raises:
            ValueError: Si le domaine n'est pas @beac.int
        """
        if not v.lower().endswith("@beac.int"):
            raise ValueError(
                "L'adresse email doit appartenir au domaine @beac.int. "
                f"Email fourni: {v}"
            )
        return v.lower()  # Normaliser en minuscules


# ============================================================================
# SCHÉMAS CRÉATION / MISE À JOUR
# ============================================================================

class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""
    
    password: str = Field(..., min_length=10, max_length=255, description="Mot de passe (min 10 caractères)")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valide la force du mot de passe."""
        from app.core.security import validate_password_strength
        
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""
    
    email: Optional[EmailStr] = None
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    
    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: Optional[str]) -> Optional[str]:
        """Valide que l'email appartient au domaine @beac.int."""
        if v is not None and not v.lower().endswith("@beac.int"):
            raise ValueError(
                "L'adresse email doit appartenir au domaine @beac.int. "
                f"Email fourni: {v}"
            )
        return v.lower() if v else None


class UserImportRow(BaseModel):
    """Schéma pour une ligne d'import Excel."""
    
    matricule: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="USER", description="Rôle (ADMIN, MANAGER, USER)")
    password: str = Field(..., min_length=10, max_length=255, description="Mot de passe initial")
    
    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Valide que l'email appartient au domaine @beac.int."""
        if not v.lower().endswith("@beac.int"):
            raise ValueError(
                "L'adresse email doit appartenir au domaine @beac.int. "
                f"Email fourni: {v}"
            )
        return v.lower()
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Valide et normalise le rôle."""
        v = v.upper().strip()
        if v not in ["ADMIN", "MANAGER", "USER"]:
            raise ValueError(f"Rôle invalide: {v}. Valeurs acceptées: ADMIN, MANAGER, USER")
        return v


# ============================================================================
# SCHÉMAS RÉPONSE
# ============================================================================

class UserResponse(UserBase):
    """Schéma de réponse pour un utilisateur."""
    
    id: UUID
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    @field_serializer('created_at', 'updated_at', 'last_login')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schéma de réponse pour une liste paginée d'utilisateurs."""
    
    users: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# SCHÉMAS AUTHENTIFICATION
# ============================================================================

class LoginRequest(BaseModel):
    """Schéma pour la requête de connexion."""
    
    matricule: str = Field(..., min_length=3, max_length=50, description="Matricule de l'utilisateur")
    password: str = Field(..., min_length=1, description="Mot de passe")


class TokenResponse(BaseModel):
    """Schéma de réponse pour les tokens JWT."""
    
    access_token: str = Field(..., description="Token d'accès JWT")
    refresh_token: str = Field(..., description="Token de rafraîchissement JWT")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée de validité en secondes")
    user: UserResponse = Field(..., description="Informations de l'utilisateur connecté")


class RefreshTokenRequest(BaseModel):
    """Schéma pour la requête de rafraîchissement de token."""
    
    refresh_token: str = Field(..., description="Token de rafraîchissement")


class ChangePasswordRequest(BaseModel):
    """Schéma pour le changement de mot de passe."""
    
    current_password: str = Field(..., min_length=1, description="Mot de passe actuel")
    new_password: str = Field(..., min_length=10, max_length=255, description="Nouveau mot de passe")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valide la force du nouveau mot de passe."""
        from app.core.security import validate_password_strength
        
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class ResetPasswordRequest(BaseModel):
    """Schéma pour la réinitialisation de mot de passe (admin)."""
    
    new_password: str = Field(..., min_length=10, max_length=255, description="Nouveau mot de passe")
    force_change: bool = Field(default=True, description="Forcer le changement au prochain login")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valide la force du nouveau mot de passe."""
        from app.core.security import validate_password_strength
        
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


# ============================================================================
# SCHÉMAS PROFIL
# ============================================================================

class ProfileUpdateRequest(BaseModel):
    """Schéma pour la mise à jour du profil utilisateur."""
    
    nom: Optional[str] = Field(None, min_length=1, max_length=100, description="Nom de famille")
    prenom: Optional[str] = Field(None, min_length=1, max_length=100, description="Prénom")
    email: Optional[EmailStr] = Field(None, description="Adresse email")
    
    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: Optional[str]) -> Optional[str]:
        """Valide que l'email appartient au domaine @beac.int."""
        if v is not None and not v.lower().endswith("@beac.int"):
            raise ValueError(
                "L'adresse email doit appartenir au domaine @beac.int. "
                f"Email fourni: {v}"
            )
        return v.lower() if v else None


class ForgotPasswordRequest(BaseModel):
    """Schéma pour la demande de réinitialisation de mot de passe."""
    
    identifier: str = Field(..., min_length=3, description="Matricule ou email de l'utilisateur")


class ForgotPasswordResponse(BaseModel):
    """Schéma de réponse pour la demande de réinitialisation."""
    
    message: str
    email: Optional[str] = Field(None, description="Email masqué où l'email a été envoyé")
    reset_token: Optional[str] = Field(None, description="Token de réinitialisation (dev uniquement)")


# ============================================================================
# SCHÉMAS IMPORT EXCEL
# ============================================================================

class UserImportResult(BaseModel):
    """Schéma de résultat pour l'import Excel."""
    
    success_count: int = Field(..., description="Nombre d'utilisateurs importés avec succès")
    error_count: int = Field(..., description="Nombre d'erreurs")
    errors: list[dict] = Field(default_factory=list, description="Liste des erreurs rencontrées")
    created_users: list[UserResponse] = Field(default_factory=list, description="Utilisateurs créés")


# ============================================================================
# SCHÉMAS STATS
# ============================================================================

class UserStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques utilisateurs."""
    
    total_users: int
    active_users: int
    inactive_users: int
    users_by_role: dict[str, int]
    recent_logins: int = Field(..., description="Connexions des 7 derniers jours")