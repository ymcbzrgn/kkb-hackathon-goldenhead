"""
Celery Application Configuration

Basit Sıralı Rapor İşleme:
- Bir rapor tamamen bitsin, sonra diğeri başlasın
- TSG -> News + İhale (paralel) -> Council
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "firma_istihbarat",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.agent_tasks"]
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
    worker_concurrency=4,  # 4 paralel task
)

# Task routes
celery_app.conf.task_routes = {
    # Eski monolitik task
    "app.workers.tasks.generate_report_task": {"queue": "reports"},
    # V2: Basit sıralı rapor işleme
    "app.workers.agent_tasks.generate_report_task_v2": {"queue": "agents"},
    # Agent tasks
    "app.workers.agent_tasks.run_tsg_agent_task": {"queue": "agents"},
    "app.workers.agent_tasks.run_news_agent_task": {"queue": "agents"},
    "app.workers.agent_tasks.run_ihale_agent_task": {"queue": "agents"},
    # Coordination
    "app.workers.agent_tasks.check_and_start_council": {"queue": "agents"},
    "app.workers.agent_tasks.run_council_task": {"queue": "agents"},  # council -> agents (aynı worker)
}
