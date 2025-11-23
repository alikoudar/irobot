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

# Token Usage schemas
from app.schemas.token_usage import (
    OperationType,
    TokenUsageBase,
    TokenUsageCreate,
    TokenUsageResponse,
    TokenUsageSummary,
    TokenUsageByOperation,
    TokenUsageByModel,
    TokenUsageByDate,
    TokenUsageStats,
    TokenUsageFilter,
    TokenUsageList,
)

# Exchange Rate schemas
from app.schemas.exchange_rate import (
    ExchangeRateBase,
    ExchangeRateCreate,
    ExchangeRateResponse,
    CurrentExchangeRate,
    ConversionRequest,
    ConversionResponse,
    ExchangeRateList,
    ExchangeRateStats,
)

# System Config schemas
from app.schemas.system_config import (
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    ConfigGroup,
    SystemConfigBulkUpdate,
    SystemConfigList,
    DEFAULT_CONFIGS,
    ModelConfigKeys,
    ChunkingConfigKeys,
    SearchConfigKeys,
    CacheConfigKeys,
    PricingConfigKeys,
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

    # Token Usage schemas
    "OperationType",
    "TokenUsageBase",
    "TokenUsageCreate",
    "TokenUsageResponse",
    "TokenUsageSummary",
    "TokenUsageByOperation",
    "TokenUsageByModel",
    "TokenUsageByDate",
    "TokenUsageStats",
    "TokenUsageFilter",
    "TokenUsageList",       

    # Exchange Rate schemas
    "ExchangeRateBase",
    "ExchangeRateCreate",
    "ExchangeRateResponse",
    "CurrentExchangeRate",
    "ConversionRequest",
    "ConversionResponse",
    "ExchangeRateList",
    "ExchangeRateStats",    

    # System Config schemas
    "SystemConfigBase",
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfigResponse",
    "ConfigGroup",
    "SystemConfigBulkUpdate",
    "SystemConfigList",
    "DEFAULT_CONFIGS",  
    "ModelConfigKeys",
    "ChunkingConfigKeys",
    "SearchConfigKeys",     
    "CacheConfigKeys",
    "PricingConfigKeys",
]