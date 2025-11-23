"""Document schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from uuid import UUID




# ============================================================================
# BASE SCHEMAS
# ============================================================================

class DocumentBase(BaseModel):
    """Base document schema."""
    original_filename: str = Field(..., min_length=1, max_length=255, description="Nom original du fichier")
    category_id: Optional[uuid.UUID] = Field(None, description="ID de la catégorie")
    
    @field_validator('original_filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename."""
        v = v.strip()
        if not v:
            raise ValueError("Le nom du fichier ne peut pas être vide")
        # Interdire les caractères dangereux
        forbidden_chars = ['..', '/', '\\', '\x00']
        for char in forbidden_chars:
            if char in v:
                raise ValueError(f"Le nom du fichier contient un caractère interdit: {char}")
        return v


# ============================================================================
# CREATE SCHEMA
# ============================================================================

class DocumentCreate(DocumentBase):
    """Schema for creating a document (internal use)."""
    file_path: str
    file_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash du fichier")
    file_size_bytes: int = Field(..., gt=0, description="Taille du fichier en octets")
    mime_type: str = Field(..., max_length=100)
    file_extension: str = Field(..., max_length=10)
    uploaded_by: uuid.UUID


# ============================================================================
# UPDATE SCHEMA
# ============================================================================

class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    category_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(None, pattern=r'^(PENDING|PROCESSING|COMPLETED|FAILED)$')
    processing_stage: Optional[str] = Field(
        None,
        pattern=r'^(VALIDATION|EXTRACTION|CHUNKING|EMBEDDING|INDEXING)$'
    )
    error_message: Optional[str] = None
    total_pages: Optional[int] = Field(None, ge=0)
    total_chunks: Optional[int] = Field(None, ge=0)
    extracted_text_length: Optional[int] = Field(None, ge=0)
    document_metadata: Optional[Dict[str, Any]] = None
    extraction_time_seconds: Optional[float] = Field(None, ge=0)
    chunking_time_seconds: Optional[float] = Field(None, ge=0)
    embedding_time_seconds: Optional[float] = Field(None, ge=0)
    total_processing_time_seconds: Optional[float] = Field(None, ge=0)
    processed_at: Optional[datetime] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: uuid.UUID
    file_path: str
    file_hash: str
    file_size_bytes: int
    mime_type: str
    file_extension: str
    status: str
    processing_stage: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    total_pages: Optional[int] = None
    total_chunks: int
    extracted_text_length: Optional[int] = None
    document_metadata: Optional[Dict[str, Any]] = None
    extraction_time_seconds: Optional[float] = None
    chunking_time_seconds: Optional[float] = None
    embedding_time_seconds: Optional[float] = None
    total_processing_time_seconds: Optional[float] = None
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentWithChunks(DocumentResponse):
    """Schema for document with chunks count detail."""
    chunks_count: int = Field(..., description="Nombre de chunks")
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for paginated document list."""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# SPECIFIC ACTION SCHEMAS
# ============================================================================

class DocumentStatusUpdate(BaseModel):
    """Schema for updating document status."""
    status: str = Field(..., pattern=r'^(PENDING|PROCESSING|COMPLETED|FAILED)$')
    processing_stage: Optional[str] = Field(
        None,
        pattern=r'^(VALIDATION|EXTRACTION|CHUNKING|EMBEDDING|INDEXING)$'
    )
    error_message: Optional[str] = None


class DocumentRetryRequest(BaseModel):
    """Schema for retrying document processing."""
    from_stage: str = Field(
        ...,
        pattern=r'^(VALIDATION|EXTRACTION|CHUNKING|EMBEDDING|INDEXING)$',
        description="Étape à partir de laquelle relancer le traitement"
    )


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    document_id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    status: str
    message: str = Field(..., description="Message de confirmation")


class DocumentBatchUploadResponse(BaseModel):
    """Schema for batch document upload response."""
    uploaded: List[DocumentUploadResponse]
    failed: List[Dict[str, str]]
    total_uploaded: int
    total_failed: int


# ============================================================================
# UPLOAD SCHEMAS
# ============================================================================

class DocumentUploadItem(BaseModel):
    """Item d'un document uploadé."""
    
    id: UUID
    original_filename: str
    status: str
    message: str
    
    class Config:
        from_attributes = True


class DocumentUploadError(BaseModel):
    """Erreur lors de l'upload."""
    
    filename: str
    error: str
    existing_document_id: Optional[UUID] = None


class DocumentUploadResponse(BaseModel):
    """Réponse de l'upload de documents."""
    
    uploaded: int = Field(..., description="Nombre de documents uploadés")
    documents: List[DocumentUploadItem] = Field(default_factory=list)
    errors: List[DocumentUploadError] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "uploaded": 2,
                "documents": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "original_filename": "rapport.pdf",
                        "status": "pending",
                        "message": "En attente de traitement"
                    },
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174001",
                        "original_filename": "contrat.docx",
                        "status": "pending",
                        "message": "En attente de traitement"
                    }
                ],
                "errors": []
            }
        }


# ============================================================================
# STATUS SCHEMAS
# ============================================================================

class DocumentStatusResponse(BaseModel):
    """Status détaillé d'un document."""
    
    id: UUID
    status: str
    processing_stage: str
    progress: int = Field(..., ge=0, le=100, description="Progression en %")
    error_message: Optional[str] = None
    retry_count: int
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "processing_stage": "extraction",
                "progress": 30,
                "error_message": None,
                "retry_count": 0,
                "total_pages": None,
                "total_chunks": None,
                "uploaded_at": "2024-11-22T12:00:00",
                "processed_at": None
            }
        }


class DocumentStatusSSE(BaseModel):
    """Event SSE pour le status d'un document."""
    
    event: str = Field(..., description="Type d'événement (status, error, complete)")
    data: Dict[str, Any] = Field(..., description="Données de l'événement")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "status",
                "data": {
                    "status": "processing",
                    "stage": "extraction",
                    "progress": 30
                }
            }
        }


# ============================================================================
# LIST SCHEMAS
# ============================================================================

class DocumentListItem(BaseModel):
    """
    Schema pour un item dans la liste des documents.
    
    Inclut le nom de l'uploader et les informations de coûts calculées.
    Optimisé pour l'affichage dans le frontend.
    """
    
    id: uuid.UUID
    original_filename: str
    file_extension: str
    file_size_bytes: int
    file_hash: str  # ← AJOUTÉ
    mime_type: Optional[str] = None  # ← AJOUTÉ
    
    # Status et progression
    status: str
    processing_stage: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Métriques document
    total_pages: Optional[int] = None
    total_chunks: int = 0
    
    # Catégorie
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None  # ← AJOUTÉ : Nom de la catégorie
    
    # Uploader - INFORMATIONS ENRICHIES
    uploaded_by: uuid.UUID
    uploader_name: Optional[str] = None  # ← AJOUTÉ : Nom complet de l'uploader
    uploader_matricule: Optional[str] = None  # ← AJOUTÉ : Matricule
    
    # Timestamps
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    # Temps de traitement - AJOUTÉS
    extraction_time_seconds: Optional[float] = None
    chunking_time_seconds: Optional[float] = None
    embedding_time_seconds: Optional[float] = None
    indexing_time_seconds: Optional[float] = None
    total_processing_time_seconds: Optional[float] = None  # ← Calculé
    
    # Coûts - AJOUTÉS
    total_cost_usd: Optional[float] = None  # ← Coût total en USD
    total_cost_xaf: Optional[float] = None  # ← Coût total en XAF
    
    # Métriques embedding - AJOUTÉS
    total_tokens: Optional[int] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Réponse de la liste de documents avec pagination."""
    
    items: List[DocumentListItem]
    total: int = Field(..., description="Nombre total de documents")
    page: int = Field(..., description="Page actuelle")
    pages: int = Field(..., description="Nombre total de pages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "original_filename": "rapport.pdf",
                        "file_extension": "pdf",
                        "file_size_bytes": 1048576,
                        "status": "completed",
                        "processing_stage": "indexing",
                        "total_pages": 10,
                        "total_chunks": 25,
                        "category_id": "123e4567-e89b-12d3-a456-426614174100",
                        "uploaded_by": "123e4567-e89b-12d3-a456-426614174200",
                        "uploaded_at": "2024-11-22T12:00:00",
                        "processed_at": "2024-11-22T12:05:00"
                    }
                ],
                "total": 150,
                "page": 1,
                "pages": 8
            }
        }


# ============================================================================
# RETRY SCHEMA
# ============================================================================

class DocumentRetryRequest(BaseModel):
    """Requête pour relancer un document."""
    
    from_stage: Optional[str] = Field(
        None,
        description="Stage depuis lequel recommencer (optionnel)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "from_stage": "extraction"
            }
        }


class DocumentRetryResponse(BaseModel):
    """Réponse du retry."""
    
    id: UUID
    status: str
    message: str
    retry_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Document en attente de retraitement",
                "retry_count": 1
            }
        }


# ============================================================================
# DELETE SCHEMA
# ============================================================================

class DocumentDeleteResponse(BaseModel):
    """Réponse de la suppression."""
    
    id: UUID
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Document supprimé avec succès"
            }
        }