"""
Celery Tasks
Arka plan görevleri
"""
import asyncio
from celery import current_task
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.report_service import ReportService


@celery_app.task(bind=True, max_retries=3)
def generate_report_task(self, report_id: str, company_name: str):
    """
    Rapor oluşturma görevi.

    1. Agent'ları paralel çalıştır
    2. Council toplantısını başlat
    3. Sonuçları kaydet
    """
    try:
        # Database session
        db = SessionLocal()
        report_service = ReportService(db)

        # Status güncelle
        report_service.update_status(report_id, "processing")

        # Async orchestrator'ı çalıştır
        from app.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator(report_id=report_id)

        # Async loop oluştur ve çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                orchestrator.run(company_name)
            )
        finally:
            loop.close()

        # Sonuçları kaydet
        if result and result.get("council_decision"):
            council = result["council_decision"]
            report_service.update_result(
                report_id=report_id,
                final_score=council.get("final_score", 50),
                risk_level=council.get("risk_level", "orta"),
                decision=council.get("decision", "inceleme_gerek"),
                decision_summary=council.get("decision_summary")
            )
            report_service.update_status(report_id, "completed")
        else:
            report_service.update_status(report_id, "failed", "Council sonucu alınamadı")

        db.close()
        return {"status": "completed", "report_id": report_id}

    except Exception as e:
        # Hata durumunda
        db = SessionLocal()
        report_service = ReportService(db)
        report_service.update_status(report_id, "failed", str(e))
        db.close()

        # Retry
        raise self.retry(exc=e, countdown=60)  # 1 dakika sonra tekrar dene
