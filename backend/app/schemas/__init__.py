"""Schemas package."""
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserImportRow,
    UserResponse,
    UserListResponse,
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ProfileUpdateRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    UserImportResult,
    UserStatsResponse
)

from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithStats,
    CategoryListResponse
)

from app.schemas.document import (
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentWithChunks,
    DocumentListResponse,
    DocumentStatusUpdate,
    DocumentRetryRequest,
    DocumentUploadResponse,
    DocumentBatchUploadResponse
)

from app.schemas.chunk import (
    ChunkBase,
    ChunkCreate,
    ChunkUpdate,
    ChunkResponse,
    ChunkWithDocument,
    ChunkListResponse,
    ChunkSearchResult
)


__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserImportRow",
    "UserResponse",
    "UserListResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "ResetPasswordRequest",
    "ProfileUpdateRequest",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "UserImportResult",
    "UserStatsResponse",

    # Category schemas
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryWithStats",
    "CategoryListResponse",

     # Document schemas
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentWithChunks",
    "DocumentListResponse",
    "DocumentStatusUpdate",
    "DocumentRetryRequest",
    "DocumentUploadResponse",
    "DocumentBatchUploadResponse",
    
    # Chunk schemas
    "ChunkBase",
    "ChunkCreate",
    "ChunkUpdate",
    "ChunkResponse",
    "ChunkWithDocument",
    "ChunkListResponse",
    "ChunkSearchResult",
]