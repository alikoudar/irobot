from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Union
import secrets


class Settings(BaseSettings):

    APP_NAME: str = "IroBot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = Field(...)
    REDIS_URL: str = Field(...)
    WEAVIATE_URL: str = Field(...)

    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MISTRAL_API_KEY: str = Field(...)
    EXCHANGE_RATE_API_KEY: str = ""
    EXCHANGE_RATE_API_URL: str = "https://api.exchangerate-api.com/v4/latest/USD"

    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost", "http://localhost:80", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    RATE_LIMIT_PER_MINUTE: int = 50
    RATE_LIMIT_PER_HOUR: int = 60

    MAX_FILE_SIZE_MB: int = 50
    MAX_BATCH_SIZE_MB: int = 500

    ALLOWED_FILE_TYPES: Union[str, List[str]] = [
    "pdf", "docx", "doc", "xlsx", "xls",
    "pptx", "ppt", "rtf", "txt", "md",
    "png", "jpg", "jpeg", "webp"
    ]

    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    CELERY_BROKER_URL: str = Field(...)
    CELERY_RESULT_BACKEND: str = Field(...)

    WORKER_PROCESSING_CONCURRENCY: int = 2
    WORKER_CHUNKING_CONCURRENCY: int = 2
    WORKER_EMBEDDING_CONCURRENCY: int = 2
    WORKER_INDEXING_CONCURRENCY: int = 2

    PHOENIX_URL: str = "http://phoenix:6006"

        # Grafana credentials
    GRAFANA_ADMIN_USER: str
    GRAFANA_ADMIN_PASSWORD: str

    # Phoenix (optionnel)
    PHOENIX_SQL_DATABASE_URL: str 

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # si tu veux ignorer les variables .env non déclarées
    }


settings = Settings()
