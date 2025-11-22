"""Endpoints d'authentification."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserResponse,
    ProfileUpdateRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse
)
from app.services import AuthService, UserService
from app.models.user import User
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur")
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authentifie un utilisateur et retourne les tokens JWT.
    
    - **matricule**: Matricule de l'utilisateur
    - **password**: Mot de passe
    
    Returns:
        TokenResponse avec access_token, refresh_token et informations utilisateur
    """
    # Extraire l'IP et user agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Authentifier l'utilisateur
    user = AuthService.authenticate_user(
        db=db,
        matricule=login_data.matricule,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Matricule ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Créer les tokens
    access_token, refresh_token, expires_in = AuthService.create_tokens(user)
    
    # Préparer la réponse
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", summary="Rafraîchir le token d'accès")
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Génère un nouveau access token à partir d'un refresh token valide.
    
    - **refresh_token**: Token de rafraîchissement valide
    
    Returns:
        Nouveau access_token et expires_in
    """
    try:
        new_access_token, expires_in = AuthService.refresh_access_token(
            db=db,
            refresh_token=token_data.refresh_token
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": expires_in
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du rafraîchissement du token: {str(e)}"
        )


@router.post("/logout", summary="Déconnexion utilisateur")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Déconnecte l'utilisateur courant.
    
    Note: La déconnexion côté serveur est limitée avec JWT.
    Le client doit supprimer les tokens de son côté.
    
    Returns:
        Message de confirmation
    """
    # Avec JWT, la déconnexion est principalement côté client
    # On pourrait implémenter une blacklist de tokens si nécessaire
    
    return {
        "message": "Déconnexion réussie",
        "detail": "Veuillez supprimer les tokens côté client"
    }


@router.post("/change-password", summary="Changer le mot de passe")
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change le mot de passe de l'utilisateur courant.
    
    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe (min 10 caractères)
    
    Returns:
        Message de confirmation
    """
    ip_address = request.client.host if request.client else None
    
    try:
        UserService.change_password(
            db=db,
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            ip_address=ip_address
        )
        
        return {
            "message": "Mot de passe changé avec succès",
            "detail": "Veuillez vous reconnecter avec le nouveau mot de passe"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du changement de mot de passe: {str(e)}"
        )


@router.get("/me", response_model=UserResponse, summary="Informations utilisateur courant")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Retourne les informations de l'utilisateur actuellement connecté.
    
    Returns:
        UserResponse avec toutes les informations de l'utilisateur
    """
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse, summary="Mettre à jour le profil")
async def update_profile(
    profile_data: ProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour le profil de l'utilisateur connecté.
    
    - **nom**: Nouveau nom (optionnel)
    - **prenom**: Nouveau prénom (optionnel)
    - **email**: Nouvel email (optionnel)
    
    Returns:
        UserResponse avec les informations mises à jour
    """
    ip_address = request.client.host if request.client else None
    
    try:
        updated_user = AuthService.update_profile(
            db=db,
            user_id=current_user.id,
            nom=profile_data.nom,
            prenom=profile_data.prenom,
            email=profile_data.email,
            ip_address=ip_address
        )
        
        return UserResponse.model_validate(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour du profil: {str(e)}"
        )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Demander une réinitialisation de mot de passe"
)
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Initie une demande de réinitialisation de mot de passe.
    
    - **identifier**: Matricule ou email de l'utilisateur
    
    En mode développement, retourne le token de réinitialisation.
    En production, envoie un email avec le lien de réinitialisation.
    
    Returns:
        ForgotPasswordResponse avec message de confirmation
    """
    ip_address = request.client.host if request.client else None
    
    try:
        # Initier la réinitialisation
        user, reset_token = AuthService.initiate_password_reset(
            db=db,
            identifier=forgot_data.identifier,
            ip_address=ip_address
        )
        
        # Déterminer si on est en dev ou prod
        is_dev = settings.APP_ENV == "development"
        
        # Envoyer l'email (réel ou simulé)
        email_result = AuthService.send_password_reset_email(
            user=user,
            reset_token=reset_token,
            is_dev=is_dev
        )
        
        return ForgotPasswordResponse(
            message=email_result["message"],
            email=email_result["email"],
            reset_token=email_result.get("reset_token")  # None en production
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la demande de réinitialisation: {str(e)}"
        )