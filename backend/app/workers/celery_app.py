"""
Celery Application Configuration
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "firma_istihbarat",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 saat max
    task_soft_time_limit=3000,  # 50 dakika soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routes (opsiyonel)
celery_app.conf.task_routes = {
    "app.workers.tasks.generate_report_task": {"queue": "reports"},
}
