"""Category endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import math

from app.api.deps import get_db, get_current_user, require_admin, require_admin_or_manager
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithStats,
    CategoryListResponse
)
from app.services.category_service import CategoryService


router = APIRouter(prefix="/categories", tags=["Categories"])


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("", response_model=CategoryListResponse)
async def get_categories(
    request: Request,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    search: Optional[str] = Query(None, description="Recherche dans nom et description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des catégories avec pagination et recherche.
    
    - **page**: Numéro de page (commence à 1)
    - **page_size**: Nombre d'éléments par page (max 100)
    - **search**: Terme de recherche optionnel
    
    Accessible à tous les utilisateurs authentifiés.
    """
    skip = (page - 1) * page_size
    
    # Get categories with stats
    categories, total = CategoryService.get_all_categories_with_stats(
        db=db,
        skip=skip,
        limit=page_size,
        search=search
    )
    
    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return CategoryListResponse(
        items=categories,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{category_id}", response_model=CategoryWithStats)
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les détails d'une catégorie avec statistiques.
    
    - **category_id**: UUID de la catégorie
    
    Accessible à tous les utilisateurs authentifiés.
    """
    category = CategoryService.get_category_with_stats(db, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catégorie non trouvée"
        )
    
    return category


# ============================================================================
# CREATE ENDPOINT
# ============================================================================

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: Request,
    category_data: CategoryCreate,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle catégorie.
    
    Accessible uniquement aux Admins et Managers.
    
    **Validation**:
    - Le nom doit être unique
    - Le nom doit contenir au moins 2 caractères
    - La couleur doit être au format hexadécimal #RRGGBB
    """
    # Get client IP and user agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    category = CategoryService.create_category(
        db=db,
        category_data=category_data,
        created_by_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return category


# ============================================================================
# UPDATE ENDPOINT
# ============================================================================

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    request: Request,
    category_id: uuid.UUID,
    category_data: CategoryUpdate,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour une catégorie.
    
    Accessible uniquement aux Admins et Managers.
    
    - **category_id**: UUID de la catégorie à modifier
    
    **Validation**:
    - Le nouveau nom doit être unique (si modifié)
    - Le nom doit contenir au moins 2 caractères
    - La couleur doit être au format hexadécimal #RRGGBB
    """
    # Get client IP and user agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    category = CategoryService.update_category(
        db=db,
        category_id=category_id,
        category_data=category_data,
        updated_by_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return category


# ============================================================================
# DELETE ENDPOINT
# ============================================================================

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    request: Request,
    category_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Supprimer une catégorie.
    
    Accessible uniquement aux Admins.
    
    - **category_id**: UUID de la catégorie à supprimer
    
    **Attention**:
    - Une catégorie contenant des documents ne peut pas être supprimée
    - Les documents doivent d'abord être réassignés ou supprimés
    """
    # Get client IP and user agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    CategoryService.delete_category(
        db=db,
        category_id=category_id,
        deleted_by_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return None