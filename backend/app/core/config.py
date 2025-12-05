"""
Application Configuration
Environment variables ve settings yönetimi
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Uygulama ayarları.
    .env dosyasından veya environment variables'dan okunur.
    """

    # Database
    DATABASE_URL: str = "postgresql://kkb:hackathon2024@localhost:5432/firma_istihbarat"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # KKB Kloudeks LLM API
    KKB_API_URL: str = "https://llmgateway.klfrm.com/api/v1"
    KKB_API_KEY: str = ""

    # App Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # JWT (ileride kullanılabilir)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
