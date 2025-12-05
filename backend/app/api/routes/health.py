"""
Health Check Endpoint
Sistem durumu kontrolü
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Sistem sağlık kontrolü.
    Database, Redis, Celery durumlarını kontrol eder.
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "celery": "unknown"
        }
    }

    # Database kontrolü
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "up"
    except Exception as e:
        health_status["services"]["database"] = "down"
        health_status["status"] = "degraded"

    # Redis kontrolü
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["services"]["redis"] = "up"
    except Exception as e:
        health_status["services"]["redis"] = "down"
        health_status["status"] = "degraded"

    # Celery kontrolü (basit)
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        if inspect.ping():
            health_status["services"]["celery"] = "up"
        else:
            health_status["services"]["celery"] = "down"
    except Exception as e:
        health_status["services"]["celery"] = "down"

    return {
        "success": True,
        "data": health_status,
        "error": None
    }
