"""
Agent-Level Celery Tasks
========================
Basit sıralı rapor işleme:
1. Bir rapor tamamen bitsin, sonra diğeri başlasın
2. TSG -> News + İhale (paralel) -> Council

TASK FLOW:
1. generate_report_task_v2 -> TSG başlatır
2. TSG bitince News + İhale paralel başlar
3. Tüm agent'lar bitince Council başlar
"""
import asyncio
from datetime import datetime, timezone
from celery import current_task, group
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.report_service import ReportService
from app.models.council_decision import AgentResult as DBAgentResult, CouncilDecision
from app.models.report import Report
from app.agents.base_agent import AgentResult
import json
import redis


# Redis client for coordination
def get_redis():
    from app.core.config import settings
    return redis.Redis.from_url(settings.REDIS_URL)


def update_agent_progress(report_id: str, agent_id: str, progress: int, message: str):
    """Agent progress'ini DB'ye kaydet"""
    try:
        db = SessionLocal()
        service = ReportService(db)
        service.update_agent_progress(report_id, agent_id, progress, message)
        db.close()
    except Exception as e:
        print(f"[AGENT_TASKS] Progress update error: {e}")


def publish_event(report_id: str, event_type: str, payload: dict):
    """Redis'e event publish et (WebSocket için)"""
    try:
        from app.services.redis_pubsub import publish_agent_event
        publish_agent_event(report_id, event_type, payload)
    except Exception as e:
        print(f"[AGENT_TASKS] Publish error: {e}")


@celery_app.task(bind=True, max_retries=2)
def run_tsg_agent_task(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    TSG Agent task'ı - Ticaret Sicili Gazetesi taraması
    TSG ilk çalışır, bitince News ve İhale paralel başlar.
    """
    print(f"[TSG_TASK] Starting for {company_name} (report: {report_id[:8]}...)")

    r = get_redis()
    resolved_name = company_name  # Default to original

    try:
        # Agent'ı oluştur ve çalıştır
        from app.agents.tsg.agent import TSGAgent

        agent = TSGAgent(demo_mode=demo_mode)
        agent.set_progress_callback(lambda p: update_agent_progress(report_id, "tsg_agent", p.progress, p.message))

        # Event: Agent started
        publish_event(report_id, "agent_started", {
            "agent_id": "tsg_agent",
            "agent_name": "TSG Agent",
            "agent_description": f"TSG taraması başladı - {company_name}"
        })

        # Async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(agent.run(company_name))
        finally:
            loop.close()

        # Sonucu Redis'e kaydet (council için)
        result_key = f"agent_result:{report_id}:tsg"
        r.setex(result_key, 3600, json.dumps(result.to_dict()))  # 1 saat TTL

        # Extract resolved company name from TSG data
        if result.data:
            tsg_sonuc = result.data.get("tsg_sonuc", {})
            yapilandirilmis = tsg_sonuc.get("yapilandirilmis_veri", {})
            found_name = yapilandirilmis.get("Firma Unvani")

            if found_name and found_name.strip():
                resolved_name = found_name.strip()
                r.setex(f"resolved_name:{report_id}", 3600, resolved_name)
                print(f"[TSG_TASK] Resolved company name: {resolved_name}")

        # DB'ye kaydet
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.tsg_data = result.data
            db.commit()
        db.close()

        # Event: Agent completed
        publish_event(report_id, "agent_completed", {
            "agent_id": "tsg_agent",
            "duration_seconds": result.duration_seconds,
            "resolved_company_name": resolved_name,
            "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
        })

        print(f"[TSG_TASK] Completed in {result.duration_seconds}s")

        # TSG bitti, şimdi News ve İhale paralel başlasın
        # NEWS: Orijinal kısa isim kullan (haber araması için daha etkili)
        # İHALE: Resolved tam isim kullan (yasal kontrol için)
        run_news_agent_task.delay(report_id, company_name, demo_mode)  # Orijinal isim
        run_ihale_agent_task.delay(report_id, resolved_name, demo_mode)  # TSG'den gelen tam unvan

        return {"status": "completed", "agent_id": "tsg_agent", "duration": result.duration_seconds}

    except Exception as e:
        print(f"[TSG_TASK] Error: {e}")
        publish_event(report_id, "agent_failed", {
            "agent_id": "tsg_agent",
            "error_message": str(e)
        })

        # TSG hata verse bile News/İhale orijinal isimle devam etsin
        run_news_agent_task.delay(report_id, company_name, demo_mode)
        run_ihale_agent_task.delay(report_id, company_name, demo_mode)

        return {"status": "failed", "agent_id": "tsg_agent", "error": str(e)}


@celery_app.task(bind=True, max_retries=2)
def run_news_agent_task(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    News Agent task'ı - Haber toplama ve sentiment analizi
    TSG'den sonra çalışır.
    """
    print(f"[NEWS_TASK] Starting for {company_name} (report: {report_id[:8]}...)")

    r = get_redis()

    try:
        from app.agents.news_agent import NewsAgent

        agent = NewsAgent(demo_mode=demo_mode)
        agent.set_progress_callback(lambda p: update_agent_progress(report_id, "news_agent", p.progress, p.message))

        publish_event(report_id, "agent_started", {
            "agent_id": "news_agent",
            "agent_name": "Haber Agent",
            "agent_description": f"Haber taraması başladı - {company_name}"
        })

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(agent.run(company_name))
        finally:
            loop.close()

        # Redis'e kaydet
        result_key = f"agent_result:{report_id}:news"
        r.setex(result_key, 3600, json.dumps(result.to_dict()))

        # DB'ye kaydet
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.news_data = result.data
            db.commit()
        db.close()

        publish_event(report_id, "agent_completed", {
            "agent_id": "news_agent",
            "duration_seconds": result.duration_seconds,
            "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
        })

        print(f"[NEWS_TASK] Completed in {result.duration_seconds}s")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "completed", "agent_id": "news_agent", "duration": result.duration_seconds}

    except Exception as e:
        print(f"[NEWS_TASK] Error: {e}")
        publish_event(report_id, "agent_failed", {
            "agent_id": "news_agent",
            "error_message": str(e)
        })

        check_and_start_council.delay(report_id, company_name, demo_mode)
        return {"status": "failed", "agent_id": "news_agent", "error": str(e)}


@celery_app.task(bind=True, max_retries=2)
def run_ihale_agent_task(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    İhale Agent task'ı - Resmi Gazete yasaklama kontrolü
    TSG'den sonra çalışır.
    """
    print(f"[IHALE_TASK] Starting for {company_name} (report: {report_id[:8]}...)")

    r = get_redis()

    try:
        from app.agents.ihale.agent import IhaleAgent

        agent = IhaleAgent(demo_mode=demo_mode)
        agent.set_progress_callback(lambda p: update_agent_progress(report_id, "ihale_agent", p.progress, p.message))

        publish_event(report_id, "agent_started", {
            "agent_id": "ihale_agent",
            "agent_name": "İhale Agent",
            "agent_description": f"Resmi Gazete taraması başladı - {company_name}"
        })

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(agent.run(company_name))
        finally:
            loop.close()

        # Redis'e kaydet
        result_key = f"agent_result:{report_id}:ihale"
        r.setex(result_key, 3600, json.dumps(result.to_dict()))

        # DB'ye kaydet
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.ihale_data = result.data
            db.commit()
        db.close()

        publish_event(report_id, "agent_completed", {
            "agent_id": "ihale_agent",
            "duration_seconds": result.duration_seconds,
            "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
        })

        print(f"[IHALE_TASK] Completed in {result.duration_seconds}s")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "completed", "agent_id": "ihale_agent", "duration": result.duration_seconds}

    except Exception as e:
        print(f"[IHALE_TASK] Error: {e}")
        publish_event(report_id, "agent_failed", {
            "agent_id": "ihale_agent",
            "error_message": str(e)
        })

        check_and_start_council.delay(report_id, company_name, demo_mode)
        return {"status": "failed", "agent_id": "ihale_agent", "error": str(e)}


def is_report_timeout(r, report_id: str, demo_mode: bool = False) -> bool:
    """Demo mode'da 4 dakika (240s) geçtiyse True döner"""
    if not demo_mode:
        return False

    # Report started_at'ı DB'den al
    db = SessionLocal()
    report = db.query(Report).filter(Report.id == report_id).first()
    db.close()

    if not report or not report.started_at:
        return False

    elapsed = (datetime.now(timezone.utc) - report.started_at).total_seconds()
    timeout_seconds = 240  # Demo mode: 4 dakika

    is_timeout = elapsed >= timeout_seconds
    if is_timeout:
        print(f"[TIMEOUT] Report {report_id[:8]} timeout after {elapsed:.0f}s (limit: {timeout_seconds}s)")

    return is_timeout


@celery_app.task(bind=True)
def check_and_start_council(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    Tüm agent'ların bitip bitmediğini kontrol et.
    Hepsi bittiyse veya timeout olduysa council'ı başlat.

    Demo mode: 4 dakika timeout - mevcut verilerle devam et
    """
    r = get_redis()

    # Agent sonuçlarını kontrol et
    tsg_result = r.get(f"agent_result:{report_id}:tsg")
    news_result = r.get(f"agent_result:{report_id}:news")
    ihale_result = r.get(f"agent_result:{report_id}:ihale")

    # Council zaten başladı mı?
    council_started = r.get(f"council_started:{report_id}")
    if council_started:
        print(f"[CHECK_COUNCIL] Council already started for {report_id[:8]}...")
        return {"status": "council_already_started"}

    # Timeout kontrolü (demo mode: 4 dakika)
    timeout_reached = is_report_timeout(r, report_id, demo_mode)

    # Tüm agent'lar bitti mi VEYA timeout mu?
    all_completed = tsg_result and news_result and ihale_result

    if all_completed or timeout_reached:
        # Council'ı bir kez başlat (race condition önleme)
        if r.setnx(f"council_started:{report_id}", "1"):
            r.expire(f"council_started:{report_id}", 3600)  # 1 saat TTL

            if timeout_reached and not all_completed:
                # Timeout durumu - mevcut verilerle devam
                print(f"[CHECK_COUNCIL] ⏰ TIMEOUT! Starting council with available data for {report_id[:8]}...")

                # Eksik agent'lar için boş sonuç oluştur
                if not tsg_result:
                    empty_result = {"status": "timeout", "data": None, "summary": "Timeout - veri toplanamadı"}
                    r.setex(f"agent_result:{report_id}:tsg", 3600, json.dumps(empty_result))
                    update_agent_progress(report_id, "tsg_agent", 100, "Timeout - tamamlandı")

                if not news_result:
                    empty_result = {"status": "timeout", "data": None, "summary": "Timeout - veri toplanamadı"}
                    r.setex(f"agent_result:{report_id}:news", 3600, json.dumps(empty_result))
                    update_agent_progress(report_id, "news_agent", 100, "Timeout - tamamlandı")

                if not ihale_result:
                    empty_result = {"status": "timeout", "data": None, "summary": "Timeout - veri toplanamadı"}
                    r.setex(f"agent_result:{report_id}:ihale", 3600, json.dumps(empty_result))
                    update_agent_progress(report_id, "ihale_agent", 100, "Timeout - tamamlandı")

                # WebSocket event
                publish_event(report_id, "timeout_reached", {
                    "message": "4 dakika doldu, mevcut verilerle devam ediliyor",
                    "available_agents": {
                        "tsg": bool(tsg_result),
                        "news": bool(news_result),
                        "ihale": bool(ihale_result)
                    }
                })
            else:
                print(f"[CHECK_COUNCIL] All agents completed, starting council for {report_id[:8]}...")

            # Council task'ını başlat
            run_council_task.delay(report_id, company_name, demo_mode)

            return {"status": "council_started", "timeout": timeout_reached}
        else:
            print(f"[CHECK_COUNCIL] Council start race condition caught for {report_id[:8]}...")
            return {"status": "council_race_condition"}
    else:
        # Hangi agent'lar eksik?
        missing = []
        if not tsg_result:
            missing.append("tsg")
        if not news_result:
            missing.append("news")
        if not ihale_result:
            missing.append("ihale")

        print(f"[CHECK_COUNCIL] Waiting for agents: {missing} (report: {report_id[:8]})")
        return {"status": "waiting", "missing_agents": missing}


@celery_app.task(bind=True, max_retries=1)
def run_council_task(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    Council toplantısı task'ı - Tüm agent verilerini değerlendir
    """
    print(f"[COUNCIL_TASK] Starting council for {company_name} (report: {report_id[:8]}...)")

    start_time = datetime.now(timezone.utc)

    try:
        r = get_redis()

        # Agent sonuçlarını al
        tsg_data = json.loads(r.get(f"agent_result:{report_id}:tsg") or "{}")
        news_data = json.loads(r.get(f"agent_result:{report_id}:news") or "{}")
        ihale_data = json.loads(r.get(f"agent_result:{report_id}:ihale") or "{}")

        # Intelligence report oluştur
        from app.services.report_generator import ReportGenerator
        report_generator = ReportGenerator()
        intelligence_report = report_generator.generate(
            company_name=company_name,
            tsg_data=tsg_data.get("data"),
            ihale_data=ihale_data.get("data"),
            news_data=news_data.get("data")
        )

        # Council servisi
        from app.council.council_service import CouncilService
        council_service = CouncilService(report_id=report_id, demo_mode=demo_mode)

        # WebSocket callback
        def ws_callback(event_type, payload):
            publish_event(report_id, event_type, payload)

        # Async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            council_result = loop.run_until_complete(
                council_service.run_meeting(
                    company_name=company_name,
                    agent_data={
                        "tsg": tsg_data.get("data"),
                        "ihale": ihale_data.get("data"),
                        "news": news_data.get("data")
                    },
                    intelligence_report=intelligence_report,
                    ws_callback=ws_callback
                )
            )
        finally:
            loop.close()

        # DB'ye kaydet
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()

        if report and council_result:
            # Council Decision kaydı
            db_council = CouncilDecision(
                report_id=report_id,
                final_score=council_result.get("final_score", 50),
                risk_level=council_result.get("risk_level", "orta"),
                decision=council_result.get("decision", "inceleme_gerek"),
                consensus=council_result.get("consensus"),
                initial_scores=council_result.get("initial_scores"),
                final_scores=council_result.get("final_scores"),
                conditions=council_result.get("conditions", []),
                summary=council_result.get("decision_rationale") or council_result.get("summary"),
                transcript=council_result.get("transcript", []),
                duration_seconds=council_result.get("duration_seconds"),
                started_at=start_time,
                completed_at=datetime.now(timezone.utc)
            )
            db.add(db_council)

            # Report güncelle
            report.council_data = council_result
            report.final_score = council_result.get("final_score", 50)
            report.risk_level = council_result.get("risk_level", "orta")
            report.decision = council_result.get("decision", "inceleme_gerek")
            report.decision_summary = council_result.get("decision_summary") or council_result.get("summary")
            report.status = "completed"
            report.completed_at = datetime.now(timezone.utc)

            # Duration hesapla
            if report.started_at:
                report.duration_seconds = int((datetime.now(timezone.utc) - report.started_at).total_seconds())

            db.commit()

            # ═══════════════════════════════════════════════════════════════
            # AUTO PDF GENERATION - Council sonrası otomatik PDF oluştur
            # ═══════════════════════════════════════════════════════════════
            try:
                from app.services.pdf_export import PDFExportService

                # Rapor verisini hazırla
                pdf_report_data = {
                    "company_name": report.company_name,
                    "company_tax_no": report.company_tax_no,
                    "final_score": report.final_score,
                    "risk_level": report.risk_level,
                    "decision": report.decision,
                    "decision_summary": report.decision_summary,
                    "created_at": report.created_at,
                    "completed_at": report.completed_at,
                    "duration_seconds": report.duration_seconds,
                    "agent_results": {
                        "tsg_agent": {"data": tsg_data.get("data"), "summary": tsg_data.get("summary")},
                        "news_agent": {"data": news_data.get("data"), "summary": news_data.get("summary")},
                        "ihale_agent": {"data": ihale_data.get("data"), "summary": ihale_data.get("summary")}
                    },
                    "council_decision": {
                        "final_score": council_result.get("final_score", 50),
                        "risk_level": council_result.get("risk_level", "orta"),
                        "decision": council_result.get("decision", "inceleme_gerek"),
                        "consensus": council_result.get("consensus"),
                        "initial_scores": council_result.get("initial_scores"),
                        "final_scores": council_result.get("final_scores"),
                        "conditions": council_result.get("conditions", []),
                        "summary": council_result.get("decision_summary") or council_result.get("summary"),
                        "transcript": council_result.get("transcript", [])
                    }
                }

                # PDF oluştur
                pdf_service = PDFExportService()
                pdf_buffer = pdf_service.generate_report_pdf(pdf_report_data)

                # Redis'e kaydet (1 saat TTL)
                pdf_key = f"pdf:{report_id}"
                r.setex(pdf_key, 3600, pdf_buffer.getvalue())

                print(f"[COUNCIL_TASK] ✅ PDF auto-generated and cached in Redis: {pdf_key}")

                # WebSocket event - PDF hazır
                publish_event(report_id, "pdf_ready", {
                    "report_id": report_id,
                    "pdf_url": f"/api/reports/{report_id}/pdf",
                    "message": "PDF raporu hazır, indirilebilir"
                })

            except Exception as pdf_error:
                print(f"[COUNCIL_TASK] ⚠️ PDF generation failed (non-critical): {pdf_error}")
                # PDF hatası kritik değil, rapor yine de tamamlandı

        db.close()

        # Event: Job completed
        end_time = datetime.now(timezone.utc)
        duration = int((end_time - start_time).total_seconds())

        publish_event(report_id, "job_completed", {
            "report_id": report_id,
            "duration_seconds": duration,
            "final_score": council_result.get("final_score", 50),
            "risk_level": council_result.get("risk_level", "orta"),
            "decision": council_result.get("decision", "inceleme_gerek"),
            "pdf_ready": True
        })

        print(f"[COUNCIL_TASK] ✅ Completed - Score: {council_result.get('final_score')}, Decision: {council_result.get('decision')}")

        # Cleanup Redis keys
        r.delete(f"agent_result:{report_id}:tsg")
        r.delete(f"agent_result:{report_id}:news")
        r.delete(f"agent_result:{report_id}:ihale")
        r.delete(f"council_started:{report_id}")
        r.delete(f"resolved_name:{report_id}")

        return {"status": "completed", "final_score": council_result.get("final_score")}

    except Exception as e:
        print(f"[COUNCIL_TASK] Error: {e}")

        # Status'u failed yap
        db = SessionLocal()
        service = ReportService(db)
        service.update_status(report_id, "failed", str(e))
        db.close()

        publish_event(report_id, "job_failed", {
            "report_id": report_id,
            "error_message": str(e)
        })

        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True, max_retries=3)
def generate_report_task_v2(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    Basit sıralı rapor işleme:
    1. TSG başlar (ilk agent)
    2. TSG bitince News + İhale paralel başlar
    3. Tüm agent'lar bitince Council başlar

    Args:
        report_id: Rapor ID
        company_name: Firma adı
        demo_mode: Demo mode (~10dk) veya Normal mode
    """
    print(f"[REPORT_V2] Starting report: {company_name}, demo_mode={demo_mode}")

    try:
        # Status güncelle ve started_at set et
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "processing"
            report.started_at = datetime.now(timezone.utc)
            db.commit()
        db.close()

        # Event: Job started
        estimated_duration = 600 if demo_mode else 3600
        publish_event(report_id, "job_started", {
            "report_id": report_id,
            "company_name": company_name,
            "estimated_duration_seconds": estimated_duration
        })

        # TSG'yi başlat (TSG bitince News + İhale otomatik başlayacak)
        run_tsg_agent_task.delay(report_id, company_name, demo_mode)

        print(f"[REPORT_V2] TSG agent started for {report_id[:8]}")

        return {"status": "tsg_started", "report_id": report_id}

    except Exception as e:
        print(f"[REPORT_V2] Error: {e}")
        db = SessionLocal()
        report_service = ReportService(db)
        report_service.update_status(report_id, "failed", str(e))
        db.close()
        raise self.retry(exc=e, countdown=60)
