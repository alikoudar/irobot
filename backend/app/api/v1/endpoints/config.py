# -*- coding: utf-8 -*-
"""
Endpoints API Configuration - Sprint 12 Phase 1

Expose les endpoints pour la gestion des configurations système :
- GET /config : Liste toutes les configurations
- GET /config/category/{category} : Configurations par catégorie
- GET /config/{key} : Configuration spécifique
- PUT /config/{key} : Mise à jour d'une configuration
- GET /config/history/{key} : Historique des modifications

Auteur: IroBot Team
Date: 2025-11-29
Sprint: 12 - Phase 1
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.models.audit_log import AuditLog
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.system_config import (
    SystemConfigCreate,
    SystemConfigList,
    SystemConfigResponse,
    SystemConfigUpdate,
)
from app.services.config_service import get_config_service

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/config", tags=["Configuration"])


# =============================================================================
# GET ALL CONFIGS
# =============================================================================


@router.get("/", response_model=SystemConfigList)
async def get_all_configs(
    category: Optional[str] = Query(
        None,
        description="Filtrer par catégorie (pricing, models, chunking, search, etc.)"
    ),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère toutes les configurations système.

    **Permissions**: Admin uniquement.

    **Filtres disponibles**:
    - category: Filtrer par catégorie

    **Catégories disponibles**:
    - pricing: Tarifs Mistral
    - models: Modèles par défaut
    - chunking: Paramètres de chunking
    - embedding: Paramètres d'embedding
    - search: Paramètres de recherche
    - upload: Paramètres d'upload
    - rate_limit: Limitation de requêtes
    - cache: Paramètres de cache
    - exchange_rate: Taux de change
    """
    try:
        query = db.query(SystemConfig)

        # Filtrer par catégorie si spécifié
        if category:
            query = query.filter(SystemConfig.category == category)

        configs = query.order_by(SystemConfig.category, SystemConfig.key).all()

        return SystemConfigList(
            items=[
                SystemConfigResponse.model_validate(config) for config in configs
            ],
            total=len(configs),
        )

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des configurations",
        )


# =============================================================================
# GET CONFIG BY CATEGORY
# =============================================================================


@router.get("/category/{category}", response_model=Dict[str, Any])
async def get_configs_by_category(
    category: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère toutes les configurations d'une catégorie.

    **Permissions**: Admin uniquement.

    **Exemple**: GET /config/category/models

    **Returns**:
    ```json
    {
        "embedding": {...},
        "reranking": {...},
        "generation": {...}
    }
    ```
    """
    try:
        service = get_config_service()
        configs = service.get_all_by_category(category, db)

        if not configs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucune configuration trouvée pour la catégorie '{category}'",
            )

        return configs

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erreur lors de la récupération de la catégorie '{category}': {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des configurations",
        )


# =============================================================================
# GET SPECIFIC CONFIG
# =============================================================================


@router.get("/{key}", response_model=SystemConfigResponse)
async def get_config(
    key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère une configuration spécifique par sa clé.

    **Permissions**: Admin uniquement.

    **Exemple**: GET /config/models.embedding

    **Returns**:
    ```json
    {
        "id": "...",
        "key": "models.embedding",
        "value": {
            "model_name": "mistral-embed",
            "dimension": 1024,
            "max_tokens_per_text": 8192
        },
        "description": "Configuration du modèle d'embedding",
        "category": "models",
        "is_sensitive": false,
        "updated_by": "...",
        "created_at": "...",
        "updated_at": "..."
    }
    ```
    """
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{key}' non trouvée",
            )

        return SystemConfigResponse.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la config '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de la configuration",
        )


# =============================================================================
# UPDATE CONFIG
# =============================================================================


@router.put("/{key}", response_model=SystemConfigResponse)
async def update_config(
    key: str,
    update_data: SystemConfigUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Met à jour une configuration système.

    **Permissions**: Admin uniquement.

    **Important**:
    - La mise à jour invalide automatiquement le cache Redis
    - Les modifications prennent effet immédiatement (pas de restart requis)
    - Un log d'audit est créé automatiquement

    **Body**:
    ```json
    {
        "value": {
            "model_name": "mistral-large-latest",
            "max_tokens": 4096,
            "temperature": 0.7
        },
        "description": "Nouvelle description (optionnel)"
    }
    ```

    **Validation automatique**:
    - Les valeurs numériques sont validées (min/max)
    - Les listes d'extensions sont validées
    - Les modèles Mistral sont vérifiés
    """
    try:
        # Vérifier que la config existe
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{key}' non trouvée",
            )

        # Validation des valeurs selon la catégorie
        _validate_config_value(key, update_data.value, config.category)

        # Mise à jour via ConfigService (gère le cache automatiquement)
        service = get_config_service()
        updated_config = service.set(
            key=key,
            value=update_data.value,
            db=db,
            updated_by=str(current_user.id),
            description=update_data.description,
        )

        # Créer un log d'audit
        audit_log = AuditLog(
            user_id=current_user.id,
            action="UPDATE",
            entity_type="config",
            entity_id=updated_config.id,
            details={
                "key": key,
                "old_value": config.value,
                "new_value": update_data.value,
                "description": update_data.description,
            },
        )
        db.add(audit_log)
        db.commit()

        logger.info(
            f"Configuration '{key}' mise à jour par {current_user.email} "
            f"(ID: {current_user.id})"
        )

        return SystemConfigResponse.model_validate(updated_config)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de la configuration",
        )


# =============================================================================
# GET CONFIG HISTORY
# =============================================================================


@router.get("/history/{key}", response_model=List[Dict[str, Any]])
async def get_config_history(
    key: str,
    limit: int = Query(50, ge=1, le=500, description="Nombre max de résultats"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère l'historique des modifications d'une configuration.

    **Permissions**: Admin uniquement.

    **Exemple**: GET /config/history/models.generation?limit=20

    **Returns**:
    ```json
    [
        {
            "id": "...",
            "user_id": "...",
            "user_email": "admin@beac.int",
            "action": "UPDATE",
            "details": {
                "key": "models.generation",
                "old_value": {...},
                "new_value": {...}
            },
            "created_at": "2025-11-29T10:30:00Z"
        }
    ]
    ```
    """
    try:
        # Vérifier que la config existe
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{key}' non trouvée",
            )

        # Récupérer l'historique depuis audit_logs
        history = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "config",
                AuditLog.details["key"].astext == key,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

        # Enrichir avec les infos utilisateur
        result = []
        for log in history:
            user = db.query(User).filter(User.id == log.user_id).first()
            result.append(
                {
                    "id": str(log.id),
                    "user_id": str(log.user_id),
                    "user_email": user.email if user else "Utilisateur inconnu",
                    "action": log.action,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() + 'Z',  # ✅ CORRECTION: Ajout du Z pour timezone UTC
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'historique",
        )


# =============================================================================
# VALIDATION HELPERS
# =============================================================================


def _validate_config_value(key: str, value: Any, category: str) -> None:
    """
    Valide une valeur de configuration selon sa catégorie et sa clé.

    Args:
        key: Clé de configuration
        value: Valeur à valider
        category: Catégorie de la configuration

    Raises:
        ValueError: Si la valeur est invalide
    """
    # Validation des modèles Mistral
    if category == "models" and "model_name" in value:
        valid_models = [
            "mistral-embed",
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
            "pixtral-12b",
            "mistral-ocr-latest",
        ]
        if value["model_name"] not in valid_models:
            raise ValueError(
                f"Modèle '{value['model_name']}' non valide. "
                f"Modèles acceptés: {', '.join(valid_models)}"
            )

    # Validation des paramètres de chunking
    if category == "chunking":
        if "value" in value:
            val = value["value"]
            if key == "chunking.size" and not (50 <= val <= 2048):
                raise ValueError("La taille de chunk doit être entre 50 et 2048 tokens")
            if key == "chunking.overlap" and not (0 <= val <= 512):
                raise ValueError("Le overlap doit être entre 0 et 512 tokens")

    # Validation des paramètres de recherche
    if category == "search":
        if "value" in value:
            val = value["value"]
            if key == "search.hybrid_alpha" and not (0.0 <= val <= 1.0):
                raise ValueError("L'alpha doit être entre 0.0 et 1.0")
            if key == "search.top_k" and not (1 <= val <= 100):
                raise ValueError("Le top_k doit être entre 1 et 100")

    # Validation des extensions autorisées
    if key == "upload.allowed_extensions" and "value" in value:
        valid_extensions = [
            "pdf",
            "docx",
            "doc",
            "xlsx",
            "xls",
            "pptx",
            "ppt",
            "rtf",
            "txt",
            "md",
            "png",
            "jpg",
            "jpeg",
            "webp",
        ]
        for ext in value["value"]:
            if ext not in valid_extensions:
                raise ValueError(
                    f"Extension '{ext}' non valide. "
                    f"Extensions acceptées: {', '.join(valid_extensions)}"
                )

    # Validation des tarifs
    if category == "pricing":
        if "price_per_million_input" in value:
            if value["price_per_million_input"] < 0:
                raise ValueError("Le prix ne peut pas être négatif")

    logger.debug(f"Validation réussie pour '{key}' (catégorie: {category})")