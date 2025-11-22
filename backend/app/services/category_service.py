"""Category service."""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status
from typing import Optional
import uuid

from app.models.category import Category
from app.models.document import Document
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryWithStats
from app.models.audit_log import AuditLog


class CategoryService:
    """Service for category management."""
    
    @staticmethod
    def get_categories(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        include_stats: bool = False
    ) -> tuple[list[Category], int]:
        """
        Get paginated list of categories.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Optional search term (searches in name and description)
            include_stats: Whether to include document count
            
        Returns:
            Tuple of (categories list, total count)
        """
        query = db.query(Category)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and get results
        categories = query.order_by(Category.name).offset(skip).limit(limit).all()
        
        return categories, total
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: uuid.UUID) -> Optional[Category]:
        """
        Get category by ID.
        
        Args:
            db: Database session
            category_id: Category UUID
            
        Returns:
            Category or None if not found
        """
        return db.query(Category).filter(Category.id == category_id).first()
    
    @staticmethod
    def get_category_by_name(db: Session, name: str) -> Optional[Category]:
        """
        Get category by name.
        
        Args:
            db: Database session
            name: Category name
            
        Returns:
            Category or None if not found
        """
        return db.query(Category).filter(Category.name == name).first()
    
    @staticmethod
    def create_category(
        db: Session,
        category_data: CategoryCreate,
        created_by_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Category:
        """
        Create a new category.
        
        Args:
            db: Database session
            category_data: Category creation data
            created_by_id: ID of user creating the category
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            Created category
            
        Raises:
            HTTPException: If category with same name already exists
        """
        # Check if category with same name exists
        existing = CategoryService.get_category_by_name(db, category_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Une catégorie avec le nom '{category_data.name}' existe déjà"
            )
        
        # Create category
        category = Category(
            name=category_data.name,
            description=category_data.description,
            color=category_data.color,
            created_by=created_by_id
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=created_by_id,
            action="CATEGORY_CREATED",
            entity_type="CATEGORY",
            entity_id=str(category.id),
            details={
                "name": category.name,
                "description": category.description,
                "color": category.color
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
        
        return category
    
    @staticmethod
    def update_category(
        db: Session,
        category_id: uuid.UUID,
        category_data: CategoryUpdate,
        updated_by_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Category:
        """
        Update a category.
        
        Args:
            db: Database session
            category_id: Category UUID
            category_data: Category update data
            updated_by_id: ID of user updating the category
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            Updated category
            
        Raises:
            HTTPException: If category not found or name conflict
        """
        # Get category
        category = CategoryService.get_category_by_id(db, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Catégorie non trouvée"
            )
        
        # Store old values for audit
        old_values = {
            "name": category.name,
            "description": category.description,
            "color": category.color
        }
        
        # Check if new name conflicts with existing category
        if category_data.name and category_data.name != category.name:
            existing = CategoryService.get_category_by_name(db, category_data.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Une catégorie avec le nom '{category_data.name}' existe déjà"
                )
        
        # Update fields
        update_data = category_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=updated_by_id,
            action="CATEGORY_UPDATED",
            entity_type="CATEGORY",
            entity_id=str(category.id),
            details={
                "old_values": old_values,
                "new_values": update_data
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
        
        return category
    
    @staticmethod
    def delete_category(
        db: Session,
        category_id: uuid.UUID,
        deleted_by_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Delete a category.
        
        Args:
            db: Database session
            category_id: Category UUID
            deleted_by_id: ID of user deleting the category
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Raises:
            HTTPException: If category not found or has associated documents
        """
        # Get category
        category = CategoryService.get_category_by_id(db, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Catégorie non trouvée"
            )
        
        # Check if category has documents
        document_count = db.query(func.count(Document.id)).filter(
            Document.category_id == category_id
        ).scalar()
        
        if document_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible de supprimer cette catégorie car elle contient {document_count} document(s). Veuillez d'abord réassigner ou supprimer ces documents."
            )
        
        # Store category data for audit
        category_data = {
            "name": category.name,
            "description": category.description,
            "color": category.color
        }
        
        # Delete category
        db.delete(category)
        db.commit()
        
        # Create audit log
        audit_log = AuditLog(
            user_id=deleted_by_id,
            action="CATEGORY_DELETED",
            entity_type="CATEGORY",
            entity_id=str(category_id),
            details=category_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def get_category_with_stats(db: Session, category_id: uuid.UUID) -> Optional[dict]:
        """
        Get category with document statistics.
        
        Args:
            db: Database session
            category_id: Category UUID
            
        Returns:
            Dictionary with category and stats or None if not found
        """
        category = CategoryService.get_category_by_id(db, category_id)
        if not category:
            return None
        
        # Get document count
        document_count = db.query(func.count(Document.id)).filter(
            Document.category_id == category_id
        ).scalar()
        
        return {
            **category.__dict__,
            "document_count": document_count
        }
    
    @staticmethod
    def get_all_categories_with_stats(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> tuple[list[dict], int]:
        """
        Get all categories with document count.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Optional search term
            
        Returns:
            Tuple of (categories with stats, total count)
        """
        # Build query with document count
        query = db.query(
            Category,
            func.count(Document.id).label('document_count')
        ).outerjoin(Document)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term)
                )
            )
        
        query = query.group_by(Category.id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        results = query.order_by(Category.name).offset(skip).limit(limit).all()
        
        # Format results
        categories_with_stats = []
        for category, doc_count in results:
            cat_dict = {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "color": category.color,
                "created_by": category.created_by,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "document_count": doc_count or 0
            }
            categories_with_stats.append(cat_dict)
        
        return categories_with_stats, total