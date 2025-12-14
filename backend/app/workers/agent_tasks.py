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


# Redis client for coordination (connection pool ile - performans!)
_redis_pool = None

def get_redis():
    """Redis connection pool'dan client al (her seferinde yeni bağlantı açmaz)"""
    global _redis_pool
    if _redis_pool is None:
        from app.core.config import settings
        _redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=20)
    return redis.Redis(connection_pool=_redis_pool)


def redis_get_json(r, key: str, default=None):
    """Redis'ten JSON al - bytes decode işlemini handle et"""
    result = r.get(key)
    if result is None:
        return default if default is not None else {}
    # Redis bytes döner, decode et
    if isinstance(result, bytes):
        result = result.decode('utf-8')
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return default if default is not None else {}


def merge_news_results(phase1_data: dict, phase2_data: dict) -> dict:
    """
    Phase 1 ve Phase 2 haber sonuçlarını birleştir.
    URL'ye göre duplicate kontrolü yapar.
    """
    seen_urls = set()
    merged_haberler = []

    # Phase 1 haberlerini ekle
    for haber in phase1_data.get("haberler", []):
        url = haber.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged_haberler.append(haber)

    # Phase 2 haberlerini ekle (duplicate kontrolü ile)
    for haber in phase2_data.get("haberler", []):
        url = haber.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged_haberler.append(haber)

    # Sentiment istatistiklerini haberlerden hesapla
    # News agent hem "olumlu/olumsuz" hem de "pozitif/negatif" kullanabilir
    pozitif = 0
    negatif = 0
    notr = 0

    for haber in merged_haberler:
        sentiment = haber.get("sentiment", "notr").lower()
        if sentiment in ("olumlu", "pozitif", "positive"):
            pozitif += 1
        elif sentiment in ("olumsuz", "negatif", "negative"):
            negatif += 1
        else:
            notr += 1

    merged_sentiment = {
        "pozitif": pozitif,
        "olumlu": pozitif,  # Her iki isimlendirmeyi de destekle
        "negatif": negatif,
        "olumsuz": negatif,
        "notr": notr
    }

    return {
        "haberler": merged_haberler,
        "toplam_haber": len(merged_haberler),
        "sentiment_ozeti": merged_sentiment,
        "arama_terimleri": list(set(
            phase1_data.get("arama_terimleri", []) +
            phase2_data.get("arama_terimleri", [])
        )),
        "phase1_haber_sayisi": len(phase1_data.get("haberler", [])),
        "phase2_haber_sayisi": len(phase2_data.get("haberler", [])),
        "iki_asamali_arama": True
    }


def merge_ihale_results(phase1_data: dict, phase2_data: dict) -> dict:
    """
    Phase 1 ve Phase 2 ihale sonuçlarını birleştir.
    Yasak varsa yasak var (OR mantığı).
    En yüksek risk değerlendirmesini al.
    """
    # Yasak durumu: herhangi birinde varsa var
    yasak_phase1 = phase1_data.get("yasak_durumu", False)
    yasak_phase2 = phase2_data.get("yasak_durumu", False)
    yasak_durumu = yasak_phase1 or yasak_phase2

    # Risk değerlendirmesi: en yüksek olanı al
    risk_map = {"dusuk": 0, "düşük": 0, "orta": 1, "yuksek": 2, "yüksek": 2}
    risk_phase1 = phase1_data.get("risk_degerlendirmesi", "dusuk")
    risk_phase2 = phase2_data.get("risk_degerlendirmesi", "dusuk")

    risk1_score = risk_map.get(risk_phase1.lower(), 0)
    risk2_score = risk_map.get(risk_phase2.lower(), 0)

    if risk1_score >= risk2_score:
        final_risk = risk_phase1
    else:
        final_risk = risk_phase2

    # Bulunan kayıtları birleştir
    kayitlar_phase1 = phase1_data.get("bulunan_kayitlar", [])
    kayitlar_phase2 = phase2_data.get("bulunan_kayitlar", [])

    # Duplicate kontrolü (basit: aynı URL veya aynı içerik)
    seen = set()
    merged_kayitlar = []

    for kayit in kayitlar_phase1 + kayitlar_phase2:
        kayit_key = kayit.get("url", "") or str(kayit.get("tarih", "")) + str(kayit.get("aciklama", ""))[:50]
        if kayit_key and kayit_key not in seen:
            seen.add(kayit_key)
            merged_kayitlar.append(kayit)

    return {
        "yasak_durumu": yasak_durumu,
        "risk_degerlendirmesi": final_risk,
        "bulunan_kayitlar": merged_kayitlar,
        "toplam_kayit": len(merged_kayitlar),
        "phase1_sonuc": {
            "yasak": yasak_phase1,
            "kayit_sayisi": len(kayitlar_phase1)
        },
        "phase2_sonuc": {
            "yasak": yasak_phase2,
            "kayit_sayisi": len(kayitlar_phase2)
        },
        "iki_asamali_arama": True
    }


def update_agent_progress(report_id: str, agent_id: str, progress: int, message: str):
    """Agent progress'ini DB'ye kaydet + WebSocket'e publish et (best-effort)."""
    db = None
    try:
        db = SessionLocal()
        service = ReportService(db)
        service.update_agent_progress(report_id, agent_id, progress, message)
    except Exception as e:
        print(f"[AGENT_TASKS] Progress update error: {e}")
    finally:
        if db:
            db.close()

    # UI canlı güncellensin diye progress event'ini Redis üzerinden publish et
    # (Redis yoksa/çalışmıyorsa DB güncellemesi yine de yapılmış olur)
    publish_event(report_id, "agent_progress", {
        "agent_id": agent_id,
        "progress": progress,
        "message": message
    })


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

    TSG paralel başlar. Bittiğinde resolved_name farklıysa Phase 2 tetikler.
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

        # DB'ye kaydet (try-finally ile güvenli)
        db = None
        try:
            db = SessionLocal()
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.tsg_data = result.data
                db.commit()
        finally:
            if db:
                db.close()

        # Event: Agent completed
        publish_event(report_id, "agent_completed", {
            "agent_id": "tsg_agent",
            "duration_seconds": result.duration_seconds,
            "resolved_company_name": resolved_name,
            "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
        })

        print(f"[TSG_TASK] Completed in {result.duration_seconds}s")

        # Phase 2 kontrolü: resolved_name farklı mı?
        original_name = r.get(f"original_name:{report_id}")
        if original_name:
            original_name = original_name.decode('utf-8') if isinstance(original_name, bytes) else original_name

        needs_phase2 = resolved_name.lower().strip() != (original_name or company_name.lower().strip())

        if needs_phase2:
            print(f"[TSG_TASK] Phase 2 needed: '{original_name}' → '{resolved_name}'")
            r.setex(f"needs_phase2:{report_id}", 3600, "1")
            # Phase 2 task'larını başlat (resolved_name ile)
            run_news_agent_task.delay(report_id, resolved_name, demo_mode, False, True)  # is_phase2=True
            run_ihale_agent_task.delay(report_id, resolved_name, demo_mode, False, True)  # is_phase2=True
        else:
            print(f"[TSG_TASK] Phase 2 not needed, names match")
            r.setex(f"needs_phase2:{report_id}", 3600, "0")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "completed", "agent_id": "tsg_agent", "duration": result.duration_seconds}

    except Exception as e:
        print(f"[TSG_TASK] Error: {e}")
        publish_event(report_id, "agent_failed", {
            "agent_id": "tsg_agent",
            "error_message": str(e)
        })

        # TSG hata verse bile Phase 2 gerekmiyor
        r.setex(f"needs_phase2:{report_id}", 3600, "0")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "failed", "agent_id": "tsg_agent", "error": str(e)}


@celery_app.task(bind=True, max_retries=2)
def run_news_agent_task(self, report_id: str, company_name: str, demo_mode: bool = False,
                        is_phase1: bool = True, is_phase2: bool = False):
    """
    News Agent task'ı - Haber toplama ve sentiment analizi

    Phase 1: Orijinal isimle arama (paralel başlar)
    Phase 2: TSG'den gelen resolved_name ile arama (farklıysa)

    Progress: Phase 1 = %0-50, Phase 2 = %50-100
    """
    phase_str = "Phase1" if is_phase1 else "Phase2"
    print(f"[NEWS_TASK:{phase_str}] Starting for {company_name} (report: {report_id[:8]}...)")

    r = get_redis()

    # Progress offset: Phase 1 = 0, Phase 2 = 50
    progress_offset = 0 if is_phase1 else 50
    progress_multiplier = 0.5  # Her phase %50

    def adjusted_progress(raw_progress: int, message: str):
        # Phase 1'de: Eğer Phase 2 başladıysa progress güncelleme (Phase 2 halleder)
        if is_phase1:
            needs_phase2 = r.get(f"needs_phase2:{report_id}")
            if needs_phase2:
                needs_phase2 = needs_phase2.decode('utf-8') if isinstance(needs_phase2, bytes) else needs_phase2
            if needs_phase2 == "1":
                # Phase 2 başladı, Phase 1 progress güncellemesini atla
                return

        adjusted = progress_offset + int(raw_progress * progress_multiplier)
        update_agent_progress(report_id, "news_agent", adjusted, f"[{phase_str}] {message}")

    # Demo mode'da report başlangıcından kalan süreyi hesapla
    remaining_time = None
    if demo_mode:
        db = None
        try:
            db = SessionLocal()
            report = db.query(Report).filter(Report.id == report_id).first()
            if report and report.started_at:
                elapsed = (datetime.now(timezone.utc) - report.started_at).total_seconds()
                total_timeout = 240  # 4 dakika
                remaining_time = max(30, total_timeout - elapsed)  # En az 30 saniye ver
                print(f"[NEWS_TASK:{phase_str}] Demo mode: {elapsed:.0f}s elapsed, {remaining_time:.0f}s remaining")
        except Exception as e:
            print(f"[NEWS_TASK:{phase_str}] Error calculating remaining time: {e}")
        finally:
            if db:
                db.close()

    try:
        from app.agents.news_agent import NewsAgent

        agent = NewsAgent(demo_mode=demo_mode)

        # Demo mode'da kalan süreyi agent'a geç
        if remaining_time is not None and hasattr(agent, 'max_execution_time'):
            agent.max_execution_time = remaining_time
            print(f"[NEWS_TASK:{phase_str}] Agent timeout set to {remaining_time:.0f}s")

        agent.set_progress_callback(lambda p: adjusted_progress(p.progress, p.message))

        # Sadece Phase 1'de agent_started event'i gönder
        if is_phase1:
            publish_event(report_id, "agent_started", {
                "agent_id": "news_agent",
                "agent_name": "Haber Agent",
                "agent_description": f"Haber taraması başladı - {company_name}"
            })

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Timeout wrapper - kalan süre kadar bekle
            if remaining_time is not None:
                result = loop.run_until_complete(
                    asyncio.wait_for(agent.run(company_name), timeout=remaining_time)
                )
            else:
                result = loop.run_until_complete(agent.run(company_name))
        except asyncio.TimeoutError:
            print(f"[NEWS_TASK:{phase_str}] ⏰ TIMEOUT after {remaining_time:.0f}s - using partial data")
            # Timeout - partial result oluştur
            result = agent._create_timeout_result(company_name) if hasattr(agent, '_create_timeout_result') else None
            if result is None:
                from app.agents.base_agent import AgentResult
                result = AgentResult(
                    agent_id="news_agent",
                    status="completed",
                    data={"timeout": True, "message": "Zaman aşımı - kısmi veri"},
                    summary="Haber taraması zaman aşımına uğradı"
                )
        finally:
            loop.close()

        # Phase'e göre Redis key
        phase_key = "phase1" if is_phase1 else "phase2"
        result_key = f"agent_result:{report_id}:news:{phase_key}"
        r.setex(result_key, 3600, json.dumps(result.to_dict()))

        # Phase 2'de sonuçları birleştir ve final key'e kaydet
        if is_phase2:
            phase1_data = redis_get_json(r, f"agent_result:{report_id}:news:phase1")
            merged_data = merge_news_results(phase1_data.get("data", {}), result.data or {})

            # Merged result oluştur
            merged_result = {
                "agent_id": "news_agent",
                "status": "completed",
                "data": merged_data,
                "summary": f"Toplam {merged_data.get('toplam_haber', 0)} haber bulundu (2 aşamalı arama)"
            }
            r.setex(f"agent_result:{report_id}:news", 3600, json.dumps(merged_result))

            # DB'ye birleştirilmiş veriyi kaydet
            db = None
            try:
                db = SessionLocal()
                report = db.query(Report).filter(Report.id == report_id).first()
                if report:
                    report.news_data = merged_data
                    db.commit()
            finally:
                if db:
                    db.close()

            # Phase 2 bitti, %100 yap
            update_agent_progress(report_id, "news_agent", 100, "Haber analizi tamamlandı (2 aşama)")
        else:
            # Phase 1 - needs_phase2 kontrolü yap
            needs_phase2 = r.get(f"needs_phase2:{report_id}")
            if needs_phase2:
                needs_phase2 = needs_phase2.decode('utf-8') if isinstance(needs_phase2, bytes) else needs_phase2

            if needs_phase2 != "1":
                # Phase 2 yok, Phase 1 final sonuç
                r.setex(f"agent_result:{report_id}:news", 3600, json.dumps(result.to_dict()))

                # DB'ye kaydet
                db = None
                try:
                    db = SessionLocal()
                    report = db.query(Report).filter(Report.id == report_id).first()
                    if report:
                        report.news_data = result.data
                        db.commit()
                finally:
                    if db:
                        db.close()

                # %100 yap
                is_timeout = result.data.get("timeout", False) if result.data else False
                timeout_msg = "Tarama tamamlandı (zaman aşımı)" if is_timeout else "Haber analizi tamamlandı"
                update_agent_progress(report_id, "news_agent", 100, timeout_msg)
            else:
                # Phase 2 gelecek, %50'de kal
                adjusted_progress(100, "Phase 1 tamamlandı, Phase 2 bekleniyor")

        # Sadece Phase 1'de veya Phase 2'de (Phase 2 varsa) completed event gönder
        needs_phase2_flag = r.get(f"needs_phase2:{report_id}")
        if needs_phase2_flag:
            needs_phase2_flag = needs_phase2_flag.decode('utf-8') if isinstance(needs_phase2_flag, bytes) else needs_phase2_flag

        should_send_completed = (is_phase1 and needs_phase2_flag != "1") or is_phase2

        if should_send_completed:
            publish_event(report_id, "agent_completed", {
                "agent_id": "news_agent",
                "duration_seconds": result.duration_seconds,
                "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
            })

        print(f"[NEWS_TASK:{phase_str}] Completed in {result.duration_seconds}s")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "completed", "agent_id": "news_agent", "phase": phase_str, "duration": result.duration_seconds}

    except Exception as e:
        print(f"[NEWS_TASK:{phase_str}] Error: {e}")

        # Hata durumunda da ilgili phase'i kaydet
        phase_key = "phase1" if is_phase1 else "phase2"
        error_result = {"status": "failed", "error": str(e), "data": None}
        r.setex(f"agent_result:{report_id}:news:{phase_key}", 3600, json.dumps(error_result))

        # Phase 2 yoksa veya Phase 2'deysek %100 yap
        needs_phase2_flag = r.get(f"needs_phase2:{report_id}")
        if needs_phase2_flag:
            needs_phase2_flag = needs_phase2_flag.decode('utf-8') if isinstance(needs_phase2_flag, bytes) else needs_phase2_flag

        if is_phase2 or needs_phase2_flag != "1":
            update_agent_progress(report_id, "news_agent", 100, f"Hata: {str(e)[:50]}")

        publish_event(report_id, "agent_failed", {
            "agent_id": "news_agent",
            "error_message": str(e)
        })

        check_and_start_council.delay(report_id, company_name, demo_mode)
        return {"status": "failed", "agent_id": "news_agent", "error": str(e)}


@celery_app.task(bind=True, max_retries=2)
def run_ihale_agent_task(self, report_id: str, company_name: str, demo_mode: bool = False,
                         is_phase1: bool = True, is_phase2: bool = False):
    """
    İhale Agent task'ı - Resmi Gazete yasaklama kontrolü

    Phase 1: Orijinal isimle arama (paralel başlar)
    Phase 2: TSG'den gelen resolved_name ile arama (farklıysa)

    Progress: Phase 1 = %0-50, Phase 2 = %50-100
    """
    phase_str = "Phase1" if is_phase1 else "Phase2"
    print(f"[IHALE_TASK:{phase_str}] Starting for {company_name} (report: {report_id[:8]}...)")

    r = get_redis()

    # Progress offset: Phase 1 = 0, Phase 2 = 50
    progress_offset = 0 if is_phase1 else 50
    progress_multiplier = 0.5  # Her phase %50

    def adjusted_progress(raw_progress: int, message: str):
        # Phase 1'de: Eğer Phase 2 başladıysa progress güncelleme (Phase 2 halleder)
        if is_phase1:
            needs_phase2 = r.get(f"needs_phase2:{report_id}")
            if needs_phase2:
                needs_phase2 = needs_phase2.decode('utf-8') if isinstance(needs_phase2, bytes) else needs_phase2
            if needs_phase2 == "1":
                # Phase 2 başladı, Phase 1 progress güncellemesini atla
                return

        adjusted = progress_offset + int(raw_progress * progress_multiplier)
        update_agent_progress(report_id, "ihale_agent", adjusted, f"[{phase_str}] {message}")

    # Demo mode'da report başlangıcından kalan süreyi hesapla
    remaining_time = None
    if demo_mode:
        db = None
        try:
            db = SessionLocal()
            report = db.query(Report).filter(Report.id == report_id).first()
            if report and report.started_at:
                elapsed = (datetime.now(timezone.utc) - report.started_at).total_seconds()
                total_timeout = 240  # 4 dakika
                remaining_time = max(30, total_timeout - elapsed)  # En az 30 saniye ver
                print(f"[IHALE_TASK:{phase_str}] Demo mode: {elapsed:.0f}s elapsed, {remaining_time:.0f}s remaining")
        except Exception as e:
            print(f"[IHALE_TASK:{phase_str}] Error calculating remaining time: {e}")
        finally:
            if db:
                db.close()

    try:
        from app.agents.ihale.agent import IhaleAgent

        agent = IhaleAgent(demo_mode=demo_mode)

        # Demo mode'da kalan süreyi agent'a geç
        if remaining_time is not None:
            agent.max_execution_time = remaining_time
            print(f"[IHALE_TASK:{phase_str}] Agent timeout set to {remaining_time:.0f}s")

        agent.set_progress_callback(lambda p: adjusted_progress(p.progress, p.message))

        # Sadece Phase 1'de agent_started event'i gönder
        if is_phase1:
            publish_event(report_id, "agent_started", {
                "agent_id": "ihale_agent",
                "agent_name": "İhale Agent",
                "agent_description": f"Resmi Gazete taraması başladı - {company_name}"
            })

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Timeout wrapper - kalan süre kadar bekle
            if remaining_time is not None:
                result = loop.run_until_complete(
                    asyncio.wait_for(agent.run(company_name), timeout=remaining_time)
                )
            else:
                result = loop.run_until_complete(agent.run(company_name))
        except asyncio.TimeoutError:
            print(f"[IHALE_TASK:{phase_str}] ⏰ TIMEOUT after {remaining_time:.0f}s - using partial data")
            # Timeout - partial result oluştur
            result = agent._create_timeout_result(company_name) if hasattr(agent, '_create_timeout_result') else None
            if result is None:
                from app.agents.base_agent import AgentResult
                result = AgentResult(
                    agent_id="ihale_agent",
                    status="completed",
                    data={"timeout": True, "yasak_durumu": False, "message": "Zaman aşımı - kısmi veri"},
                    summary="İhale taraması zaman aşımına uğradı"
                )
        finally:
            loop.close()

        # Phase'e göre Redis key
        phase_key = "phase1" if is_phase1 else "phase2"
        result_key = f"agent_result:{report_id}:ihale:{phase_key}"
        r.setex(result_key, 3600, json.dumps(result.to_dict()))

        # Phase 2'de sonuçları birleştir ve final key'e kaydet
        if is_phase2:
            phase1_data = redis_get_json(r, f"agent_result:{report_id}:ihale:phase1")
            merged_data = merge_ihale_results(phase1_data.get("data", {}), result.data or {})

            # Merged result oluştur
            merged_result = {
                "agent_id": "ihale_agent",
                "status": "completed",
                "data": merged_data,
                "summary": f"İhale kontrolü tamamlandı (2 aşamalı arama)"
            }
            r.setex(f"agent_result:{report_id}:ihale", 3600, json.dumps(merged_result))

            # DB'ye birleştirilmiş veriyi kaydet
            db = None
            try:
                db = SessionLocal()
                report = db.query(Report).filter(Report.id == report_id).first()
                if report:
                    report.ihale_data = merged_data
                    db.commit()
            finally:
                if db:
                    db.close()

            # Phase 2 bitti, %100 yap
            update_agent_progress(report_id, "ihale_agent", 100, "İhale kontrolü tamamlandı (2 aşama)")
        else:
            # Phase 1 - needs_phase2 kontrolü yap
            needs_phase2 = r.get(f"needs_phase2:{report_id}")
            if needs_phase2:
                needs_phase2 = needs_phase2.decode('utf-8') if isinstance(needs_phase2, bytes) else needs_phase2

            if needs_phase2 != "1":
                # Phase 2 yok, Phase 1 final sonuç
                r.setex(f"agent_result:{report_id}:ihale", 3600, json.dumps(result.to_dict()))

                # DB'ye kaydet
                db = None
                try:
                    db = SessionLocal()
                    report = db.query(Report).filter(Report.id == report_id).first()
                    if report:
                        report.ihale_data = result.data
                        db.commit()
                finally:
                    if db:
                        db.close()

                # %100 yap
                is_timeout = result.data.get("timeout", False) if result.data else False
                timeout_msg = "Tarama tamamlandı (zaman aşımı)" if is_timeout else "İhale kontrolü tamamlandı"
                update_agent_progress(report_id, "ihale_agent", 100, timeout_msg)
            else:
                # Phase 2 gelecek, %50'de kal
                adjusted_progress(100, "Phase 1 tamamlandı, Phase 2 bekleniyor")

        # Sadece Phase 1'de veya Phase 2'de (Phase 2 varsa) completed event gönder
        needs_phase2_flag = r.get(f"needs_phase2:{report_id}")
        if needs_phase2_flag:
            needs_phase2_flag = needs_phase2_flag.decode('utf-8') if isinstance(needs_phase2_flag, bytes) else needs_phase2_flag

        should_send_completed = (is_phase1 and needs_phase2_flag != "1") or is_phase2

        if should_send_completed:
            publish_event(report_id, "agent_completed", {
                "agent_id": "ihale_agent",
                "duration_seconds": result.duration_seconds,
                "summary": {"key_findings": result.key_findings, "warning_flags": result.warning_flags}
            })

        print(f"[IHALE_TASK:{phase_str}] Completed in {result.duration_seconds}s")

        # Council kontrolü
        check_and_start_council.delay(report_id, company_name, demo_mode)

        return {"status": "completed", "agent_id": "ihale_agent", "phase": phase_str, "duration": result.duration_seconds}

    except Exception as e:
        print(f"[IHALE_TASK:{phase_str}] Error: {e}")

        # Hata durumunda da ilgili phase'i kaydet
        phase_key = "phase1" if is_phase1 else "phase2"
        error_result = {"status": "failed", "error": str(e), "data": None}
        r.setex(f"agent_result:{report_id}:ihale:{phase_key}", 3600, json.dumps(error_result))

        # Phase 2 yoksa veya Phase 2'deysek %100 yap
        needs_phase2_flag = r.get(f"needs_phase2:{report_id}")
        if needs_phase2_flag:
            needs_phase2_flag = needs_phase2_flag.decode('utf-8') if isinstance(needs_phase2_flag, bytes) else needs_phase2_flag

        if is_phase2 or needs_phase2_flag != "1":
            update_agent_progress(report_id, "ihale_agent", 100, f"Hata: {str(e)[:50]}")

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

    # Report started_at'ı DB'den al (try-finally ile güvenli)
    db = None
    try:
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()

        if not report or not report.started_at:
            return False

        elapsed = (datetime.now(timezone.utc) - report.started_at).total_seconds()
        timeout_seconds = 240  # Demo mode: 4 dakika

        is_timeout = elapsed >= timeout_seconds
        if is_timeout:
            print(f"[TIMEOUT] Report {report_id[:8]} timeout after {elapsed:.0f}s (limit: {timeout_seconds}s)")

        return is_timeout
    except Exception as e:
        print(f"[TIMEOUT] Error checking timeout: {e}")
        return False
    finally:
        if db:
            db.close()


@celery_app.task(bind=True)
def check_and_start_council(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    Tüm agent'ların bitip bitmediğini kontrol et.
    Hepsi bittiyse veya timeout olduysa council'ı başlat.

    İki aşamalı arama desteği:
    - needs_phase2 == "1" ise: TSG + News (Phase1+2) + İhale (Phase1+2) bekle
    - needs_phase2 == "0" veya yok ise: TSG + News + İhale final sonuçlarını bekle

    Demo mode: 4 dakika timeout - mevcut verilerle devam et
    """
    r = get_redis()

    # Council zaten başladı mı?
    council_started = r.get(f"council_started:{report_id}")
    if council_started:
        print(f"[CHECK_COUNCIL] Council already started for {report_id[:8]}...")
        return {"status": "council_already_started"}

    # Phase 2 gerekli mi?
    needs_phase2 = r.get(f"needs_phase2:{report_id}")
    if needs_phase2:
        needs_phase2 = needs_phase2.decode('utf-8') if isinstance(needs_phase2, bytes) else needs_phase2
    phase2_required = (needs_phase2 == "1")

    # TSG sonucu her zaman tek
    tsg_result = r.get(f"agent_result:{report_id}:tsg")

    # News ve İhale sonuçları - phase'e göre kontrol
    if phase2_required:
        # Phase 2 gerekli - hem phase1 hem phase2 tamamlanmış olmalı
        news_phase1 = r.get(f"agent_result:{report_id}:news:phase1")
        news_phase2 = r.get(f"agent_result:{report_id}:news:phase2")
        ihale_phase1 = r.get(f"agent_result:{report_id}:ihale:phase1")
        ihale_phase2 = r.get(f"agent_result:{report_id}:ihale:phase2")

        news_completed = news_phase1 and news_phase2
        ihale_completed = ihale_phase1 and ihale_phase2

        # Final sonuçlar zaten merge edilmiş olmalı
        news_result = r.get(f"agent_result:{report_id}:news")
        ihale_result = r.get(f"agent_result:{report_id}:ihale")
    else:
        # Phase 2 yok - sadece final sonuçları kontrol et
        news_result = r.get(f"agent_result:{report_id}:news")
        ihale_result = r.get(f"agent_result:{report_id}:ihale")
        news_completed = bool(news_result)
        ihale_completed = bool(ihale_result)

    # Timeout kontrolü (demo mode: 4 dakika)
    timeout_reached = is_report_timeout(r, report_id, demo_mode)

    # Tüm agent'lar bitti mi?
    all_completed = tsg_result and news_completed and ihale_completed

    # Debug log
    print(f"[CHECK_COUNCIL] Status for {report_id[:8]}: tsg={bool(tsg_result)}, news={news_completed}, ihale={ihale_completed}, phase2_required={phase2_required}, timeout={timeout_reached}")

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

                if not r.get(f"agent_result:{report_id}:news"):
                    # News final sonucu yok - phase1 varsa onu kullan, yoksa boş
                    phase1_data = redis_get_json(r, f"agent_result:{report_id}:news:phase1")
                    if phase1_data and phase1_data.get("data"):
                        r.setex(f"agent_result:{report_id}:news", 3600, json.dumps(phase1_data))
                    else:
                        empty_result = {"status": "timeout", "data": None, "summary": "Timeout - veri toplanamadı"}
                        r.setex(f"agent_result:{report_id}:news", 3600, json.dumps(empty_result))
                    update_agent_progress(report_id, "news_agent", 100, "Timeout - tamamlandı")

                if not r.get(f"agent_result:{report_id}:ihale"):
                    # İhale final sonucu yok - phase1 varsa onu kullan, yoksa boş
                    phase1_data = redis_get_json(r, f"agent_result:{report_id}:ihale:phase1")
                    if phase1_data and phase1_data.get("data"):
                        r.setex(f"agent_result:{report_id}:ihale", 3600, json.dumps(phase1_data))
                    else:
                        empty_result = {"status": "timeout", "data": None, "summary": "Timeout - veri toplanamadı"}
                        r.setex(f"agent_result:{report_id}:ihale", 3600, json.dumps(empty_result))
                    update_agent_progress(report_id, "ihale_agent", 100, "Timeout - tamamlandı")

                # WebSocket event
                publish_event(report_id, "timeout_reached", {
                    "message": "4 dakika doldu, mevcut verilerle devam ediliyor",
                    "available_agents": {
                        "tsg": bool(tsg_result),
                        "news": news_completed,
                        "ihale": ihale_completed
                    },
                    "phase2_required": phase2_required
                })
            else:
                print(f"[CHECK_COUNCIL] All agents completed, starting council for {report_id[:8]}...")

            # Council task'ını başlat
            run_council_task.delay(report_id, company_name, demo_mode)

            return {"status": "council_started", "timeout": timeout_reached, "phase2_required": phase2_required}
        else:
            print(f"[CHECK_COUNCIL] Council start race condition caught for {report_id[:8]}...")
            return {"status": "council_race_condition"}
    else:
        # Hangi agent'lar eksik?
        missing = []
        if not tsg_result:
            missing.append("tsg")
        if not news_completed:
            if phase2_required:
                if not r.get(f"agent_result:{report_id}:news:phase1"):
                    missing.append("news:phase1")
                if not r.get(f"agent_result:{report_id}:news:phase2"):
                    missing.append("news:phase2")
            else:
                missing.append("news")
        if not ihale_completed:
            if phase2_required:
                if not r.get(f"agent_result:{report_id}:ihale:phase1"):
                    missing.append("ihale:phase1")
                if not r.get(f"agent_result:{report_id}:ihale:phase2"):
                    missing.append("ihale:phase2")
            else:
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

    db = None
    try:
        r = get_redis()

        # Agent sonuçlarını al (bytes decode ile güvenli)
        tsg_data = redis_get_json(r, f"agent_result:{report_id}:tsg")
        news_data = redis_get_json(r, f"agent_result:{report_id}:news")
        ihale_data = redis_get_json(r, f"agent_result:{report_id}:ihale")

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

        # DB'ye kaydet (try-finally ile güvenli - db yukarıda tanımlı)
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
        r.delete(f"agent_result:{report_id}:news:phase1")
        r.delete(f"agent_result:{report_id}:news:phase2")
        r.delete(f"agent_result:{report_id}:ihale")
        r.delete(f"agent_result:{report_id}:ihale:phase1")
        r.delete(f"agent_result:{report_id}:ihale:phase2")
        r.delete(f"council_started:{report_id}")
        r.delete(f"resolved_name:{report_id}")
        r.delete(f"needs_phase2:{report_id}")
        r.delete(f"original_name:{report_id}")

        return {"status": "completed", "final_score": council_result.get("final_score")}

    except Exception as e:
        print(f"[COUNCIL_TASK] Error: {e}")

        # Status'u failed yap (ayrı try-finally ile)
        error_db = None
        try:
            error_db = SessionLocal()
            service = ReportService(error_db)
            service.update_status(report_id, "failed", str(e))
        finally:
            if error_db:
                error_db.close()

        publish_event(report_id, "job_failed", {
            "report_id": report_id,
            "error_message": str(e)
        })

        return {"status": "failed", "error": str(e)}

    finally:
        # Ana db session'ı kapat
        if db:
            db.close()


@celery_app.task(bind=True, max_retries=3)
def generate_report_task_v2(self, report_id: str, company_name: str, demo_mode: bool = False):
    """
    İki aşamalı paralel rapor işleme:

    Aşama 1: TSG + News + İhale hepsi paralel başlar (orijinal isimle)
    Aşama 2: TSG'den resolved_name farklıysa News + İhale tekrar arar

    Args:
        report_id: Rapor ID
        company_name: Firma adı (kullanıcının yazdığı)
        demo_mode: Demo mode (~10dk) veya Normal mode
    """
    print(f"[REPORT_V2] Starting report: {company_name}, demo_mode={demo_mode}")

    db = None
    try:
        # Status güncelle ve started_at set et
        db = SessionLocal()
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "processing"
            report.started_at = datetime.now(timezone.utc)
            db.commit()

        # Orijinal ismi Redis'e kaydet (Phase 2 karşılaştırması için)
        r = get_redis()
        r.setex(f"original_name:{report_id}", 3600, company_name.lower().strip())

        # Event: Job started
        estimated_duration = 600 if demo_mode else 3600
        publish_event(report_id, "job_started", {
            "report_id": report_id,
            "company_name": company_name,
            "estimated_duration_seconds": estimated_duration
        })

        # TÜM AGENT'LAR PARALEL BAŞLASIN (Aşama 1)
        run_tsg_agent_task.delay(report_id, company_name, demo_mode)
        run_news_agent_task.delay(report_id, company_name, demo_mode, True, False)  # is_phase1=True
        run_ihale_agent_task.delay(report_id, company_name, demo_mode, True, False)  # is_phase1=True

        print(f"[REPORT_V2] All agents started in parallel for {report_id[:8]}")

        return {"status": "tsg_started", "report_id": report_id}

    except Exception as e:
        print(f"[REPORT_V2] Error: {e}")
        error_db = None
        try:
            error_db = SessionLocal()
            report_service = ReportService(error_db)
            report_service.update_status(report_id, "failed", str(e))
        finally:
            if error_db:
                error_db.close()
        raise self.retry(exc=e, countdown=60)

    finally:
        if db:
            db.close()
