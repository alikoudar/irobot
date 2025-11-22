"""Service d'authentification - Gestion des tokens JWT et connexion."""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
import secrets

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    get_password_hash
)
from app.core.config import settings
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import TokenResponse, UserResponse


class AuthService:
    """Service de gestion de l'authentification."""
    
    @staticmethod
    def authenticate_user(
        db: Session,
        matricule: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """
        Authentifie un utilisateur avec son matricule et mot de passe.
        
        Args:
            db: Session de base de données
            matricule: Matricule de l'utilisateur
            password: Mot de passe en clair
            ip_address: Adresse IP de la requête
            user_agent: User agent de la requête
            
        Returns:
            Optional[User]: Utilisateur si authentification réussie, None sinon
        """
        # Rechercher l'utilisateur par matricule
        user = db.query(User).filter(User.matricule == matricule).first()
        
        if not user:
            # Log de tentative de connexion échouée (utilisateur inexistant)
            AuthService._log_failed_login(
                db=db,
                matricule=matricule,
                reason="Matricule inexistant",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return None
        
        # Vérifier le mot de passe
        if not verify_password(password, user.hashed_password):
            # Log de tentative de connexion échouée (mot de passe incorrect)
            AuthService._log_failed_login(
                db=db,
                matricule=matricule,
                reason="Mot de passe incorrect",
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user.id
            )
            return None
        
        # Vérifier que l'utilisateur est actif
        if not user.is_active:
            # Log de tentative de connexion échouée (compte désactivé)
            AuthService._log_failed_login(
                db=db,
                matricule=matricule,
                reason="Compte désactivé",
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user.id
            )
            return None
        
        # Mettre à jour le last_login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Log de connexion réussie
        AuthService._log_successful_login(
            db=db,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return user
    
    @staticmethod
    def create_tokens(user: User) -> Tuple[str, str, int]:
        """
        Crée les tokens d'accès et de rafraîchissement pour un utilisateur.
        
        Args:
            user: Utilisateur pour lequel créer les tokens
            
        Returns:
            Tuple[str, str, int]: (access_token, refresh_token, expires_in)
        """
        # Données à encoder dans les tokens
        token_data = {
            "sub": str(user.id),
            "matricule": user.matricule,
            "role": user.role.value,
        }
        
        # Créer l'access token
        access_token = create_access_token(token_data)
        
        # Créer le refresh token
        refresh_token = create_refresh_token(token_data)
        
        # Durée de validité en secondes
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return access_token, refresh_token, expires_in
    
    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token: str
    ) -> Tuple[str, int]:
        """
        Rafraîchit un access token à partir d'un refresh token.
        
        Args:
            db: Session de base de données
            refresh_token: Token de rafraîchissement
            
        Returns:
            Tuple[str, int]: (new_access_token, expires_in)
            
        Raises:
            HTTPException: Si le refresh token est invalide
        """
        # Décoder le refresh token
        try:
            payload = decode_token(refresh_token)
        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide ou expiré",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        
        # Vérifier que c'est un refresh token
        if not verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Type de token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Récupérer l'user_id
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
        
        # Récupérer l'utilisateur
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
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
        
        # Créer un nouveau access token
        token_data = {
            "sub": str(user.id),
            "matricule": user.matricule,
            "role": user.role.value,
        }
        new_access_token = create_access_token(token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return new_access_token, expires_in
    
    @staticmethod
    def update_profile(
        db: Session,
        user_id: UUID,
        nom: Optional[str] = None,
        prenom: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> User:
        """
        Met à jour le profil d'un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            nom: Nouveau nom (optionnel)
            prenom: Nouveau prénom (optionnel)
            email: Nouvel email (optionnel)
            ip_address: Adresse IP de la requête
            
        Returns:
            User: Utilisateur mis à jour
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas ou l'email est déjà utilisé
        """
        # Récupérer l'utilisateur
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable"
            )
        
        # Préparer les anciennes valeurs pour le log
        old_values = {
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email
        }
        
        # Mettre à jour les champs fournis
        if nom is not None:
            user.nom = nom
        
        if prenom is not None:
            user.prenom = prenom
        
        if email is not None:
            # Vérifier que l'email n'est pas déjà utilisé par un autre utilisateur
            existing_user = db.query(User).filter(
                User.email == email,
                User.id != user_id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email est déjà utilisé par un autre utilisateur"
                )
            
            user.email = email
        
        # Mettre à jour updated_at
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        # Log de mise à jour du profil
        AuthService._log_profile_update(
            db=db,
            user=user,
            old_values=old_values,
            ip_address=ip_address
        )
        
        return user
    
    @staticmethod
    def initiate_password_reset(
        db: Session,
        identifier: str,
        ip_address: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Initie une demande de réinitialisation de mot de passe.
        
        Args:
            db: Session de base de données
            identifier: Matricule ou email de l'utilisateur
            ip_address: Adresse IP de la requête
            
        Returns:
            Tuple[User, str]: (utilisateur, reset_token)
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas ou est inactif
        """
        # Rechercher l'utilisateur par matricule ou email
        user = db.query(User).filter(
            (User.matricule == identifier) | (User.email == identifier)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun utilisateur trouvé avec ce matricule ou email"
            )
        
        # Vérifier que l'utilisateur est actif
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce compte est désactivé. Contactez l'administrateur."
            )
        
        # Générer un token de réinitialisation sécurisé
        reset_token = secrets.token_urlsafe(32)
        
        # TODO: En production, sauvegarder le token dans la DB avec expiration
        # Pour l'instant, on génère juste le token
        
        # Log de demande de réinitialisation
        AuthService._log_password_reset_request(
            db=db,
            user=user,
            ip_address=ip_address
        )
        
        return user, reset_token
    
    @staticmethod
    def send_password_reset_email(
        user: User,
        reset_token: str,
        is_dev: bool = False
    ) -> dict:
        """
        Envoie un email de réinitialisation de mot de passe.
        
        Args:
            user: Utilisateur
            reset_token: Token de réinitialisation
            is_dev: Mode développement (email simulé)
            
        Returns:
            dict: Informations sur l'envoi (email masqué, etc.)
        """
        # Masquer l'email
        email_parts = user.email.split('@')
        masked_email = f"{email_parts[0][:2]}***@{email_parts[1]}"
        
        if is_dev:
            # Mode développement: ne pas envoyer d'email réel
            print(f"\n{'='*60}")
            print(f"[DEV MODE] Email de réinitialisation de mot de passe")
            print(f"{'='*60}")
            print(f"Destinataire: {user.email}")
            print(f"Matricule: {user.matricule}")
            print(f"Nom: {user.prenom} {user.nom}")
            print(f"\nLien de réinitialisation:")
            print(f"http://localhost:5173/reset-password?token={reset_token}")
            print(f"{'='*60}\n")
            
            return {
                "email": masked_email,
                "message": "Email de réinitialisation envoyé (mode développement)",
                "reset_token": reset_token  # Retourner le token en dev uniquement
            }
        else:
            # Mode production: envoyer un vrai email
            # TODO: Implémenter l'envoi d'email réel (SMTP, SendGrid, etc.)
            
            return {
                "email": masked_email,
                "message": "Email de réinitialisation envoyé",
                "reset_token": None  # Ne pas retourner le token en production
            }
    
    @staticmethod
    def _log_successful_login(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Enregistre une connexion réussie dans les logs d'audit.
        
        Args:
            db: Session de base de données
            user: Utilisateur connecté
            ip_address: Adresse IP
            user_agent: User agent
        """
        audit_log = AuditLog(
            user_id=user.id,
            action="LOGIN_SUCCESS",
            entity_type="AUTH",
            entity_id=None,
            details={
                "matricule": user.matricule,
                "role": user.role.value,
                "message": "Connexion réussie"
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def _log_failed_login(
        db: Session,
        matricule: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> None:
        """
        Enregistre une tentative de connexion échouée dans les logs d'audit.
        
        Args:
            db: Session de base de données
            matricule: Matricule utilisé pour la tentative
            reason: Raison de l'échec
            ip_address: Adresse IP
            user_agent: User agent
            user_id: ID de l'utilisateur si trouvé
        """
        audit_log = AuditLog(
            user_id=user_id,
            action="LOGIN_FAILED",
            entity_type="AUTH",
            entity_id=None,
            details={
                "matricule": matricule,
                "reason": reason,
                "message": f"Tentative de connexion échouée: {reason}"
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def _log_profile_update(
        db: Session,
        user: User,
        old_values: dict,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Enregistre une mise à jour de profil dans les logs d'audit.
        
        Args:
            db: Session de base de données
            user: Utilisateur
            old_values: Anciennes valeurs
            ip_address: Adresse IP
        """
        audit_log = AuditLog(
            user_id=user.id,
            action="PROFILE_UPDATE",
            entity_type="USER",
            entity_id=str(user.id),
            details={
                "matricule": user.matricule,
                "old_values": old_values,
                "new_values": {
                    "nom": user.nom,
                    "prenom": user.prenom,
                    "email": user.email
                },
                "message": "Profil mis à jour"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def _log_password_reset_request(
        db: Session,
        user: User,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Enregistre une demande de réinitialisation de mot de passe.
        
        Args:
            db: Session de base de données
            user: Utilisateur
            ip_address: Adresse IP
        """
        audit_log = AuditLog(
            user_id=user.id,
            action="PASSWORD_RESET_REQUEST",
            entity_type="AUTH",
            entity_id=str(user.id),
            details={
                "matricule": user.matricule,
                "email": user.email,
                "message": "Demande de réinitialisation de mot de passe"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()