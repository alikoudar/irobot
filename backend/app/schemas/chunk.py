"""Chunk schemas."""
from pydantic import BaseModel, Field, field_validator, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class ChunkBase(BaseModel):
    """Base chunk schema."""
    content: str = Field(..., min_length=1, description="Contenu textuel du chunk")
    chunk_index: int = Field(..., ge=0, description="Index du chunk dans le document")
    page_number: Optional[int] = Field(None, ge=1, description="Numéro de page source")
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Le contenu du chunk ne peut pas être vide")
        return v


# ============================================================================
# CREATE SCHEMA
# ============================================================================

class ChunkCreate(ChunkBase):
    """Schema for creating a chunk."""
    document_id: uuid.UUID
    weaviate_id: str = Field(..., min_length=1, max_length=255, description="ID du vecteur dans Weaviate")
    token_count: int = Field(..., gt=0, description="Nombre de tokens")
    char_count: int = Field(..., gt=0, description="Nombre de caractères")
    start_char: Optional[int] = Field(None, ge=0, description="Position de début dans le document")
    end_char: Optional[int] = Field(None, ge=0, description="Position de fin dans le document")
    chunk_metadata: Optional[Dict[str, Any]] = Field(None, description="Métadonnées additionnelles")
    embedding_model: Optional[str] = Field(None, max_length=50, description="Modèle d'embedding utilisé")
    embedding_time_seconds: Optional[float] = Field(None, ge=0, description="Temps d'embedding en secondes")
    
    @field_validator('end_char')
    @classmethod
    def validate_end_char(cls, v: Optional[int], info) -> Optional[int]:
        """Validate end_char is greater than start_char."""
        if v is not None and 'start_char' in info.data:
            start_char = info.data.get('start_char')
            if start_char is not None and v <= start_char:
                raise ValueError("end_char doit être supérieur à start_char")
        return v


# ============================================================================
# UPDATE SCHEMA
# ============================================================================

class ChunkUpdate(BaseModel):
    """Schema for updating a chunk."""
    content: Optional[str] = Field(None, min_length=1)
    token_count: Optional[int] = Field(None, gt=0)
    char_count: Optional[int] = Field(None, gt=0)
    page_number: Optional[int] = Field(None, ge=1)
    chunk_metadata: Optional[Dict[str, Any]] = None
    indexed_at: Optional[datetime] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ChunkResponse(ChunkBase):
    """Schema for chunk response."""
    id: uuid.UUID
    document_id: uuid.UUID
    weaviate_id: str
    token_count: int
    char_count: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    chunk_metadata: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = None
    embedding_time_seconds: Optional[float] = None
    created_at: datetime
    indexed_at: Optional[datetime] = None
    
    @field_serializer('created_at', 'indexed_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Sérialise les datetime en ISO + Z."""
        return dt.isoformat() + 'Z' if dt else None
    
    class Config:
        from_attributes = True


class ChunkWithDocument(ChunkResponse):
    """Schema for chunk with document info."""
    document_filename: str = Field(..., description="Nom du document source")
    document_category: Optional[str] = Field(None, description="Catégorie du document")
    
    class Config:
        from_attributes = True


class ChunkListResponse(BaseModel):
    """Schema for paginated chunk list."""
    items: List[ChunkResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChunkSearchResult(ChunkResponse):
    """Schema for chunk search result with relevance score."""
    relevance_score: float = Field(..., ge=0, le=1, description="Score de pertinence (0-1)")
    distance: Optional[float] = Field(None, description="Distance vectorielle")
    
    class Config:
        from_attributes = True