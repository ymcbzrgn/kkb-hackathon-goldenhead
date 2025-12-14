"""
Celery Application Configuration

Basit Sıralı Rapor İşleme:
- Bir rapor tamamen bitsin, sonra diğeri başlasın
- TSG -> News + İhale (paralel) -> Council

Pipeline Profilleri (PIPELINE_PROFILE env var):
- light_16gb: 4 worker, 12GB memory limit
- standard_24gb: 8 worker, 20GB memory limit
- aggressive: 12 worker, 28GB memory limit
"""
from celery import Celery
from app.core.config import settings

# Profil bazlı ayarları al
profile = settings.profile_config

celery_app = Celery(
    "firma_istihbarat",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.agent_tasks"]
)

# Celery configuration - profil bazlı dinamik ayarlar
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
    # Dinamik concurrency: Pipeline profiline göre ayarlanır
    # light_16gb=4, standard_24gb=8, aggressive=12
    worker_concurrency=profile.celery_concurrency,
    # Memory limit: Worker başına max RAM (KB cinsinden)
    worker_max_memory_per_child=profile.memory_limit_mb * 1024,
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
