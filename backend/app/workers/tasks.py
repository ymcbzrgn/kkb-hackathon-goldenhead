"""
Celery Tasks
Arka plan görevleri
"""
import asyncio
from datetime import datetime
from celery import current_task
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.report_service import ReportService
from app.models.council_decision import AgentResult, CouncilDecision


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

        # DB progress callback - her progress update'inde DB'ye kaydet
        def db_progress_callback(agent_id: str, progress: int, message: str):
            """Agent progress'ini DB'ye kaydet (reserved_json içinde)"""
            try:
                # Yeni session kullan (thread safety)
                progress_db = SessionLocal()
                progress_service = ReportService(progress_db)
                progress_service.update_agent_progress(report_id, agent_id, progress, message)
                progress_db.close()
            except Exception as e:
                print(f"DB progress error for {agent_id}: {e}")

        orchestrator = Orchestrator(
            report_id=report_id,
            db_callback=db_progress_callback
        )

        # Async loop oluştur ve çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                orchestrator.run(company_name)
            )
        finally:
            loop.close()

        # ============================================
        # Agent sonuçlarını DB'ye kaydet
        # ============================================
        agent_results = result.get("agent_results", {})
        for agent_id, agent_result in agent_results.items():
            db_agent_result = AgentResult(
                report_id=report_id,
                agent_id=f"{agent_id}_agent" if not agent_id.endswith("_agent") else agent_id,
                agent_name=agent_id.replace("_", " ").title() + " Agent",
                status=agent_result.get("status", "completed"),
                data=agent_result.get("data"),
                summary=agent_result.get("summary"),
                key_findings=agent_result.get("key_findings", []),
                warning_flags=agent_result.get("warning_flags", []),
                duration_seconds=agent_result.get("duration_seconds"),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db.add(db_agent_result)

        # ============================================
        # Council kararını DB'ye kaydet
        # ============================================
        if result and result.get("council_decision"):
            council = result["council_decision"]

            # Council Decision kaydı
            db_council = CouncilDecision(
                report_id=report_id,
                final_score=council.get("final_score", 50),
                risk_level=council.get("risk_level", "orta"),
                decision=council.get("decision", "inceleme_gerek"),
                consensus=council.get("consensus"),
                initial_scores=council.get("initial_scores"),
                final_scores=council.get("final_scores"),
                conditions=council.get("conditions", []),
                summary=council.get("decision_rationale") or council.get("summary"),
                transcript=council.get("transcript", []),
                duration_seconds=council.get("duration_seconds"),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db.add(db_council)

            # Report sonuçlarını güncelle
            report_service.update_result(
                report_id=report_id,
                final_score=council.get("final_score", 50),
                risk_level=council.get("risk_level", "orta"),
                decision=council.get("decision", "inceleme_gerek"),
                decision_summary=council.get("decision_summary") or council.get("summary")
            )

            db.commit()
            report_service.update_status(report_id, "completed")
        else:
            db.commit()
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
