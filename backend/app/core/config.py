"""
Application Configuration
Environment variables ve settings yönetimi
"""
import secrets
from pydantic_settings import BaseSettings
from pydantic import field_validator
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

    # KKB Kloudeks LLM API (MIA)
    KKB_API_URL: str = "https://mia.csp.kloudeks.com/v1"
    KKB_API_KEY: str = ""

    # App Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Demo Mode - 10 dakikalık kısaltılmış pipeline
    DEMO_MODE: bool = False

    # CORS - Production'da spesifik origin'ler belirtilmeli
    # Env'de virgülle ayrılmış: ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # JWT - SECRET_KEY mutlaka .env'den okunmalı, yoksa her restart'ta yeni key
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator('SECRET_KEY', mode='before')
    @classmethod
    def generate_secret_key_if_empty(cls, v: str) -> str:
        """SECRET_KEY boşsa güvenli random key üret ve uyarı ver."""
        if not v or v == "your-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "SECRET_KEY is not set! Generating random key. "
                "Set SECRET_KEY in .env for production!",
                UserWarning
            )
            return secrets.token_urlsafe(32)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
