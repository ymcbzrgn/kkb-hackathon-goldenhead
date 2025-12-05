"""
Security utilities
Authentication, authorization helpers
"""
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from app.core.config import settings


def generate_api_key() -> str:
    """
    Güvenli API key oluşturur.
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    API key'i hashler (storage için).
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    API key doğrulaması yapar.
    """
    return hash_api_key(api_key) == hashed_key


def generate_report_id() -> str:
    """
    Unique rapor ID'si oluşturur.
    """
    import uuid
    return str(uuid.uuid4())


# Rate limiting için basit in-memory store
# Production'da Redis kullanılmalı
_rate_limit_store: dict[str, list[datetime]] = {}


def check_rate_limit(
    identifier: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> bool:
    """
    Basit rate limiting kontrolü.

    Args:
        identifier: IP adresi veya API key
        max_requests: İzin verilen maksimum istek sayısı
        window_seconds: Zaman penceresi (saniye)

    Returns:
        True eğer istek yapılabilir, False eğer limit aşıldı
    """
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)

    if identifier not in _rate_limit_store:
        _rate_limit_store[identifier] = []

    # Eski kayıtları temizle
    _rate_limit_store[identifier] = [
        t for t in _rate_limit_store[identifier]
        if t > window_start
    ]

    # Limit kontrolü
    if len(_rate_limit_store[identifier]) >= max_requests:
        return False

    # Yeni isteği kaydet
    _rate_limit_store[identifier].append(now)
    return True
