"""Category schemas."""
from pydantic import BaseModel, Field, field_validator, field_serializer
from typing import Optional
from datetime import datetime
import uuid


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class CategoryBase(BaseModel):
    """Base category schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la catégorie")
    description: Optional[str] = Field(None, description="Description de la catégorie")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Couleur hex (ex: #005ca9)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name."""
        v = v.strip()
        if not v:
            raise ValueError("Le nom de la catégorie ne peut pas être vide")
        if len(v) < 2:
            raise ValueError("Le nom de la catégorie doit contenir au moins 2 caractères")
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color format."""
        if v is not None:
            v = v.upper()
            if not v.startswith('#'):
                raise ValueError("La couleur doit commencer par #")
            if len(v) != 7:
                raise ValueError("La couleur doit être au format #RRGGBB")
        return v


# ============================================================================
# CREATE SCHEMA
# ============================================================================

class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    pass


# ============================================================================
# UPDATE SCHEMA
# ============================================================================

class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate category name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Le nom de la catégorie ne peut pas être vide")
            if len(v) < 2:
                raise ValueError("Le nom de la catégorie doit contenir au moins 2 caractères")
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color format."""
        if v is not None:
            v = v.upper()
            if not v.startswith('#'):
                raise ValueError("La couleur doit commencer par #")
            if len(v) != 7:
                raise ValueError("La couleur doit être au format #RRGGBB")
        return v


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class CategoryResponse(CategoryBase):
    """Schema for category response."""
    id: uuid.UUID
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    class Config:
        from_attributes = True


class CategoryWithStats(CategoryResponse):
    """Schema for category with statistics."""
    document_count: int = Field(0, description="Nombre de documents dans cette catégorie")
    
    class Config:
        from_attributes = True


# ============================================================================
# LIST RESPONSE SCHEMA
# ============================================================================

class CategoryListResponse(BaseModel):
    """Schema for paginated category list response."""
    items: list[CategoryWithStats]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True