"""
API Dependencies
FastAPI dependency injection helpers
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    Mevcut kullanıcıyı döndürür.
    Hackathon için basit implementasyon - auth yok.
    """
    # Hackathon için auth devre dışı
    return {"id": "anonymous", "name": "Anonymous User"}


async def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> bool:
    """
    API key doğrulaması.
    Hackathon için devre dışı.
    """
    # Hackathon için api key kontrolü yok
    return True


def get_redis_client():
    """
    Redis client döndürür.
    """
    import redis
    return redis.from_url(settings.REDIS_URL)


def get_qdrant_client():
    """
    Qdrant client döndürür.
    """
    from qdrant_client import QdrantClient
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
