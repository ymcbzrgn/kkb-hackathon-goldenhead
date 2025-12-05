"""
Workers module - Celery tasks
"""
from app.workers.celery_app import celery_app
from app.workers.tasks import generate_report_task

__all__ = ["celery_app", "generate_report_task"]
