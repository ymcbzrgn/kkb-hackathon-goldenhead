"""
Application Configuration
Environment variables ve settings yönetimi

Pipeline Profilleri:
- LIGHT_16GB: 16GB RAM sistemler için optimize (az parallelism, düşük DPI)
- STANDARD_24GB: 24GB RAM sistemler için (orta parallelism, orta DPI)
- AGGRESSIVE: 32GB+ sistemler için (maksimum parallelism, yüksek DPI)
"""
import secrets
from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import BaseModel, field_validator
from typing import Optional, List


# ============================================
# Pipeline Profile Definitions
# ============================================

class PipelineProfile(str, Enum):
    """RAM bazlı pipeline profilleri"""
    LIGHT_16GB = "light_16gb"
    STANDARD_24GB = "standard_24gb"
    AGGRESSIVE = "aggressive"
    HYPER_MODE = "hyper_mode"  # 4 dakika MAX SPEED


class OCRConfig(BaseModel):
    """İhale Agent OCR ayarları"""
    dpi: int = 150                      # PDF → Image DPI (300 → 150 = 4x hız)
    rotations: List[int] = [0, 180]     # Denenecek rotasyonlar (4 → 2)
    languages: List[str] = ["tur"]      # OCR dilleri (2 → 1)
    min_text_threshold: int = 200       # Minimum text uzunluğu


class IhaleConfig(BaseModel):
    """İhale Agent konfigürasyonu"""
    max_concurrent_pdf: int = 3         # Paralel PDF işleme
    search_days_default: int = 90       # Demo modda taranacak gün
    search_days_full: int = 1095        # Full modda taranacak gün (3 yıl)
    page_timeout_ms: int = 300       # Sayfa yükleme timeout
    request_delay_sec: float = 1.5      # Rate limiting
    ocr: OCRConfig = OCRConfig()


class NewsConfig(BaseModel):
    """News Agent konfigürasyonu"""
    max_concurrent_scrapers: int = 10   # Paralel scraper sayısı
    max_articles_per_source: int = 50   # Kaynak başına max haber
    scraper_timeout_sec: int = 600      # Scraper timeout
    years_back_default: int = 2         # Demo modda yıl aralığı
    years_back_full: int = 10           # Full modda yıl aralığı
    enable_semantic_search: bool = True # Qdrant semantic search
    semantic_top_k: int = 20            # Semantic search sonuç sayısı


class ProfileSettings(BaseModel):
    """Profil bazlı tüm ayarlar"""
    celery_concurrency: int             # Celery worker sayısı
    memory_limit_mb: int                # Worker memory limit (MB)
    ihale: IhaleConfig                  # İhale agent ayarları
    news: NewsConfig                    # News agent ayarları


# Profil tanımları
PROFILE_CONFIGS = {
    PipelineProfile.LIGHT_16GB: ProfileSettings(
        celery_concurrency=4,
        memory_limit_mb=12000,
        ihale=IhaleConfig(
            max_concurrent_pdf=2,
            search_days_default=60,
            ocr=OCRConfig(dpi=150, rotations=[0, 180], languages=["tur"])
        ),
        news=NewsConfig(
            max_concurrent_scrapers=5,
            max_articles_per_source=20,
            scraper_timeout_sec=300
        )
    ),
    PipelineProfile.STANDARD_24GB: ProfileSettings(
        celery_concurrency=8,
        memory_limit_mb=20000,
        ihale=IhaleConfig(
            max_concurrent_pdf=10,       # 4 → 10 (10x pipeline için)
            search_days_default=900,     # 90 → 900 gün (10x tarama)
            ocr=OCRConfig(dpi=200, rotations=[0, 90, 180], languages=["tur"])
        ),
        news=NewsConfig(
            max_concurrent_scrapers=10,
            max_articles_per_source=50,
            scraper_timeout_sec=600
        )
    ),
    PipelineProfile.AGGRESSIVE: ProfileSettings(
        celery_concurrency=12,
        memory_limit_mb=28000,
        ihale=IhaleConfig(
            max_concurrent_pdf=6,
            search_days_default=180,
            ocr=OCRConfig(dpi=300, rotations=[0, 90, 180, 270], languages=["tur", "eng"])
        ),
        news=NewsConfig(
            max_concurrent_scrapers=15,
            max_articles_per_source=100,
            scraper_timeout_sec=900,
            semantic_top_k=50
        )
    ),
    # HYPER_MODE: 4 dakikada maksimum veri toplama - 100 paralel pipeline
    # TEK KISIT: ZAMAN (4 dakika) - Diğer tüm kısıtlamalar kaldırıldı
    # Her zaman 3 YIL geriye dönük FULL arama (spesifik tarih verilmedikçe)
    # Zaman öncelikli: Önce son 1 yıl, sonra 2. yıl, sonra 3. yıl
    PipelineProfile.HYPER_MODE: ProfileSettings(
        celery_concurrency=16,
        memory_limit_mb=32000,
        ihale=IhaleConfig(
            max_concurrent_pdf=100,          # 100 paralel PDF işleme
            search_days_default=730,         # 2 YIL default (tarih verilmezse)
            search_days_full=1095,           # 3 YIL (max)
            page_timeout_ms=5000,           # 5s timeout (hızlı fail)
            request_delay_sec=0.3,           # 0.3s delay (hızlı)
            ocr=OCRConfig(dpi=100, rotations=[0], languages=["tur"])
        ),
        news=NewsConfig(
            max_concurrent_scrapers=50,      # 50 paralel scraper
            max_articles_per_source=100,     # Kaynak başına 100 haber (kısıtlama yok)
            scraper_timeout_sec=60,          # 60s timeout (hızlı fail)
            years_back_default=3,            # 3 YIL (her zaman full arama)
            years_back_full=3,               # 3 YIL
            enable_semantic_search=True,
            semantic_top_k=200               # Daha fazla semantic sonuç
        )
    )
}


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

    # Pipeline Profile - RAM bazlı konfigürasyon
    # Seçenekler: light_16gb, standard_24gb, aggressive, hyper_mode
    PIPELINE_PROFILE: str = "hyper_mode"  # 4 dakika MAX SPEED

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

    @property
    def profile_config(self) -> ProfileSettings:
        """Aktif pipeline profilinin ayarlarını döndür."""
        return PROFILE_CONFIGS[PipelineProfile(self.PIPELINE_PROFILE)]


# Global settings instance
settings = Settings()
