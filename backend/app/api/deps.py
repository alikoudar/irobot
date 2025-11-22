"""Dependencies FastAPI pour l'authentification et les permissions."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import decode_token, verify_token_type
from app.db.session import get_db
from app.models.user import User, UserRole

# Security scheme pour JWT Bearer
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT.
    
    Args:
        credentials: Credentials HTTP Bearer contenant le token
        db: Session de base de données
        
    Returns:
        User: Utilisateur authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    token = credentials.credentials
    
    # Décoder le token
    payload = decode_token(token)
    
    # Vérifier que c'est un access token
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Récupérer l'user_id du payload
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide: user_id manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide: user_id malformé",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    # Récupérer l'utilisateur de la base de données
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier que l'utilisateur est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur désactivé",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Récupère l'utilisateur courant et vérifie qu'il est actif.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        User: Utilisateur actif
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas actif
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur désactivé"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Vérifie que l'utilisateur courant est un administrateur.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        User: Utilisateur admin
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis"
        )
    return current_user


async def require_admin_or_manager(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Vérifie que l'utilisateur courant est admin ou manager.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        User: Utilisateur admin ou manager
        
    Raises:
        HTTPException: Si l'utilisateur n'est ni admin ni manager
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur ou manager requis"
        )
    return current_user


async def require_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Vérifie que l'utilisateur courant a vérifié son compte.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        User: Utilisateur vérifié
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas vérifié
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vérification du compte requise"
        )
    return current_user


def check_user_permission(user: User, required_role: UserRole) -> bool:
    """
    Vérifie si un utilisateur a le rôle requis ou supérieur.
    
    Hiérarchie des rôles: ADMIN > MANAGER > USER
    
    Args:
        user: Utilisateur à vérifier
        required_role: Rôle minimum requis
        
    Returns:
        bool: True si l'utilisateur a les permissions
    """
    role_hierarchy = {
        UserRole.USER: 1,
        UserRole.MANAGER: 2,
        UserRole.ADMIN: 3
    }
    
    user_level = role_hierarchy.get(user.role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level