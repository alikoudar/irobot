"""Service de gestion des utilisateurs - CRUD, Import Excel, Gestion mots de passe."""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status, UploadFile
from uuid import UUID
from datetime import datetime
import openpyxl
from io import BytesIO

from app.core.security import get_password_hash, verify_password, validate_password_strength
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserImportRow,
    UserImportResult,
    UserResponse,
    UserStatsResponse
)


class UserService:
    """Service de gestion des utilisateurs."""
    
    @staticmethod
    def get_users(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        Récupère une liste paginée d'utilisateurs avec filtres.
        
        Args:
            db: Session de base de données
            skip: Nombre d'éléments à sauter (pagination)
            limit: Nombre maximum d'éléments à retourner
            search: Terme de recherche (matricule, nom, prénom, email)
            role: Filtrer par rôle
            is_active: Filtrer par statut actif/inactif
            
        Returns:
            Tuple[List[User], int]: (liste d'utilisateurs, total)
        """
        query = db.query(User)
        
        # Filtre de recherche
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.matricule.ilike(search_term),
                    User.nom.ilike(search_term),
                    User.prenom.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Filtre par rôle
        if role:
            query = query.filter(User.role == role)
        
        # Filtre par statut actif
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # Total
        total = query.count()
        
        # Pagination
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return users, total
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """
        Récupère un utilisateur par son ID.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            
        Returns:
            Optional[User]: Utilisateur trouvé ou None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_matricule(db: Session, matricule: str) -> Optional[User]:
        """
        Récupère un utilisateur par son matricule.
        
        Args:
            db: Session de base de données
            matricule: Matricule de l'utilisateur
            
        Returns:
            Optional[User]: Utilisateur trouvé ou None
        """
        return db.query(User).filter(User.matricule == matricule).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son email.
        
        Args:
            db: Session de base de données
            email: Email de l'utilisateur
            
        Returns:
            Optional[User]: Utilisateur trouvé ou None
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_user(
        db: Session,
        user_data: UserCreate,
        created_by: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> User:
        """
        Crée un nouvel utilisateur.
        
        Args:
            db: Session de base de données
            user_data: Données de l'utilisateur à créer
            created_by: ID de l'utilisateur créateur (admin)
            ip_address: Adresse IP de la requête
            
        Returns:
            User: Utilisateur créé
            
        Raises:
            HTTPException: Si le matricule ou l'email existe déjà
        """
        # Vérifier si le matricule existe déjà
        if UserService.get_user_by_matricule(db, user_data.matricule):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le matricule {user_data.matricule} existe déjà"
            )
        
        # Vérifier si l'email existe déjà
        if UserService.get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'email {user_data.email} existe déjà"
            )
        
        # Hasher le mot de passe
        hashed_password = get_password_hash(user_data.password)
        
        # Créer l'utilisateur
        new_user = User(
            matricule=user_data.matricule,
            email=user_data.email,
            nom=user_data.nom,
            prenom=user_data.prenom,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=user_data.is_active,
            is_verified=False  # L'utilisateur doit vérifier son compte
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Log d'audit
        audit_log = AuditLog(
            user_id=created_by,
            action="USER_CREATED",
            entity_type="USER",
            entity_id=new_user.id,
            details={
                "matricule": new_user.matricule,
                "email": new_user.email,
                "role": new_user.role.value,
                "message": f"Utilisateur {new_user.matricule} créé"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        
        return new_user
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: UUID,
        user_data: UserUpdate,
        updated_by: UUID,
        ip_address: Optional[str] = None
    ) -> User:
        """
        Met à jour un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur à mettre à jour
            user_data: Nouvelles données
            updated_by: ID de l'utilisateur effectuant la modification
            ip_address: Adresse IP de la requête
            
        Returns:
            User: Utilisateur mis à jour
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas ou email en conflit
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable"
            )
        
        # Vérifier l'unicité de l'email si modifié
        if user_data.email and user_data.email != user.email:
            existing_user = UserService.get_user_by_email(db, user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"L'email {user_data.email} est déjà utilisé"
                )
        
        # Mettre à jour les champs
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        # Log d'audit
        audit_log = AuditLog(
            user_id=updated_by,
            action="USER_UPDATED",
            entity_type="USER",
            entity_id=user.id,
            details={
                "matricule": user.matricule,
                "updated_fields": list(update_data.keys()),
                "message": f"Utilisateur {user.matricule} mis à jour"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        
        return user
    
    @staticmethod
    def delete_user(
        db: Session,
        user_id: UUID,
        deleted_by: UUID,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Supprime un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur à supprimer
            deleted_by: ID de l'utilisateur effectuant la suppression
            ip_address: Adresse IP de la requête
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas ou ne peut pas être supprimé
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable"
            )
        
        # Ne pas permettre de supprimer un admin si c'est le dernier
        if user.role == UserRole.ADMIN:
            admin_count = db.query(User).filter(
                User.role == UserRole.ADMIN,
                User.is_active == True
            ).count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de supprimer le dernier administrateur actif"
                )
        
        # Log d'audit avant suppression
        audit_log = AuditLog(
            user_id=deleted_by,
            action="USER_DELETED",
            entity_type="USER",
            entity_id=user.id,
            details={
                "matricule": user.matricule,
                "email": user.email,
                "message": f"Utilisateur {user.matricule} supprimé"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        
        # Supprimer l'utilisateur
        db.delete(user)
        db.commit()
    
    @staticmethod
    def change_password(
        db: Session,
        user_id: UUID,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Change le mot de passe d'un utilisateur.
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            current_password: Mot de passe actuel
            new_password: Nouveau mot de passe
            ip_address: Adresse IP de la requête
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas ou le mot de passe actuel est incorrect
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable"
            )
        
        # Vérifier le mot de passe actuel
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )
        
        # Valider le nouveau mot de passe
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Mettre à jour le mot de passe
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        # Log d'audit
        audit_log = AuditLog(
            user_id=user.id,
            action="PASSWORD_CHANGED",
            entity_type="USER",
            entity_id=user.id,
            details={
                "matricule": user.matricule,
                "message": "Mot de passe changé avec succès"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def reset_password(
        db: Session,
        user_id: UUID,
        new_password: str,
        reset_by: UUID,
        force_change: bool = True,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Réinitialise le mot de passe d'un utilisateur (admin only).
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            new_password: Nouveau mot de passe
            reset_by: ID de l'admin effectuant la réinitialisation
            force_change: Forcer le changement au prochain login
            ip_address: Adresse IP de la requête
            
        Raises:
            HTTPException: Si l'utilisateur n'existe pas
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable"
            )
        
        # Mettre à jour le mot de passe
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Si force_change, l'utilisateur devra changer son mot de passe
        # (champ à ajouter dans le modèle si nécessaire)
        
        db.commit()
        
        # Log d'audit
        audit_log = AuditLog(
            user_id=reset_by,
            action="PASSWORD_RESET",
            entity_type="USER",
            entity_id=user.id,
            details={
                "matricule": user.matricule,
                "force_change": force_change,
                "message": f"Mot de passe réinitialisé par admin"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    async def import_users_from_excel(
        db: Session,
        file: UploadFile,
        imported_by: UUID,
        ip_address: Optional[str] = None
    ) -> UserImportResult:
        """
        Importe des utilisateurs depuis un fichier Excel.
        
        Format attendu:
        - Colonne A: matricule
        - Colonne B: email
        - Colonne C: nom
        - Colonne D: prenom
        - Colonne E: role (ADMIN, MANAGER, USER)
        - Colonne F: password
        
        Args:
            db: Session de base de données
            file: Fichier Excel
            imported_by: ID de l'admin effectuant l'import
            ip_address: Adresse IP de la requête
            
        Returns:
            UserImportResult: Résultat de l'import
        """
        # Lire le fichier Excel
        try:
            contents = await file.read()
            workbook = openpyxl.load_workbook(BytesIO(contents))
            sheet = workbook.active
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur de lecture du fichier Excel: {str(e)}"
            ) from e
        
        success_count = 0
        error_count = 0
        errors = []
        created_users = []
        
        # Parcourir les lignes (skip header)
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # Extraire les données
                matricule, email, nom, prenom, role, password = row[:6]
                
                # Valider les données
                if not all([matricule, email, nom, prenom, password]):
                    errors.append({
                        "row": row_idx,
                        "error": "Données manquantes"
                    })
                    error_count += 1
                    continue
                
                # Normaliser le rôle
                role = str(role).upper().strip() if role else "USER"
                if role not in ["ADMIN", "MANAGER", "USER"]:
                    errors.append({
                        "row": row_idx,
                        "matricule": matricule,
                        "error": f"Rôle invalide: {role}"
                    })
                    error_count += 1
                    continue
                
                # Créer l'utilisateur
                user_data = UserCreate(
                    matricule=str(matricule).strip(),
                    email=str(email).strip().lower(),
                    nom=str(nom).strip(),
                    prenom=str(prenom).strip(),
                    role=UserRole[role],
                    password=str(password),
                    is_active=True
                )
                
                user = UserService.create_user(
                    db=db,
                    user_data=user_data,
                    created_by=imported_by,
                    ip_address=ip_address
                )
                
                created_users.append(UserResponse.model_validate(user))
                success_count += 1
                
            except HTTPException as e:
                errors.append({
                    "row": row_idx,
                    "matricule": matricule if matricule else "N/A",
                    "error": e.detail
                })
                error_count += 1
            except Exception as e:
                errors.append({
                    "row": row_idx,
                    "matricule": matricule if matricule else "N/A",
                    "error": str(e)
                })
                error_count += 1
        
        # Log d'audit global
        audit_log = AuditLog(
            user_id=imported_by,
            action="USERS_IMPORTED",
            entity_type="USER",
            entity_id=None,
            details={
                "success_count": success_count,
                "error_count": error_count,
                "message": f"Import de {success_count} utilisateurs avec {error_count} erreurs"
            },
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        
        return UserImportResult(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            created_users=created_users
        )
    
    @staticmethod
    def get_user_stats(db: Session) -> UserStatsResponse:
        """
        Récupère les statistiques des utilisateurs.
        
        Args:
            db: Session de base de données
            
        Returns:
            UserStatsResponse: Statistiques
        """
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        inactive_users = total_users - active_users
        
        # Stats par rôle
        users_by_role = {
            "ADMIN": db.query(User).filter(User.role == UserRole.ADMIN).count(),
            "MANAGER": db.query(User).filter(User.role == UserRole.MANAGER).count(),
            "USER": db.query(User).filter(User.role == UserRole.USER).count(),
        }
        
        # Connexions récentes (7 derniers jours)
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = db.query(User).filter(
            User.last_login >= seven_days_ago
        ).count()
        
        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            users_by_role=users_by_role,
            recent_logins=recent_logins
        )