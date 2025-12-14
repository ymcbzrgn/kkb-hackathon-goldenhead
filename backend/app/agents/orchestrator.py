"""
Orchestrator - Agent ve Council Koordinasyonu
Tüm süreci yönetir

FALLBACK MEKANİZMASI:
- K8s agent'lar default olarak aktif
- K8s agent fail olursa (bağlantı hatası, veri yok vb.) LOCAL agent'a düşer
- Böylece her durumda veri toplanmaya çalışılır
"""
import asyncio
import os
from typing import Callable, Dict, Optional, Any, List
from datetime import datetime

from app.agents.tsg.agent import TSGAgent

# K8s configuration - local development için default false
# Production'da K8s varsa env'den true yapılabilir
USE_K8S_IHALE_AGENT = os.getenv("USE_K8S_IHALE_AGENT", "false").lower() == "true"
USE_K8S_NEWS_AGENT = os.getenv("USE_K8S_NEWS_AGENT", "false").lower() == "true"
USE_K8S_TSG_AGENT = os.getenv("USE_K8S_TSG_AGENT", "false").lower() == "true"

# Her iki agent türünü de import et (fallback için)
from app.agents.ihale_agent_k8s import IhaleAgentK8s
from app.agents.ihale_agent import IhaleAgent as LocalIhaleAgent
from app.agents.news_agent_k8s import NewsAgentK8s
from app.agents.news_agent import NewsAgent as LocalNewsAgent
from app.agents.tsg_agent_k8s import TSGAgentK8s

# Demo mode - 10 dakikalık kısaltılmış pipeline (env'den default alınır, per-request override edilebilir)
DEFAULT_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

print(f"[ORCHESTRATOR] Default Demo Mode: {'ENABLED - 10dk pipeline' if DEFAULT_DEMO_MODE else 'DISABLED - Tam pipeline'}")
print(f"[ORCHESTRATOR] K8s Ihale Agent: {'ENABLED' if USE_K8S_IHALE_AGENT else 'DISABLED'} (fallback to local on failure)")
print(f"[ORCHESTRATOR] K8s News Agent: {'ENABLED' if USE_K8S_NEWS_AGENT else 'DISABLED'} (fallback to local on failure)")
print(f"[ORCHESTRATOR] K8s TSG Agent: {'ENABLED' if USE_K8S_TSG_AGENT else 'DISABLED'} (fallback to local on failure)")
from app.agents.base_agent import AgentResult, AgentProgress
from app.council.council_service import CouncilService
from app.services.report_generator import ReportGenerator
from app.api.websocket import manager as ws_manager


class Orchestrator:
    """
    Ana orkestratör sınıfı.

    Görevleri:
    1. Agent'ları paralel çalıştır
    2. Sonuçları topla
    3. Council toplantısını başlat
    4. WebSocket üzerinden ilerleme bildir
    """

    def __init__(
        self,
        report_id: str,
        ws_callback: Optional[Callable] = None,
        db_callback: Optional[Callable] = None,
        demo_mode: Optional[bool] = None
    ):
        self.report_id = report_id
        self.ws_callback = ws_callback or self._default_ws_callback
        self.db_callback = db_callback  # Progress'i DB'ye kaydetmek için

        # Demo mode: per-request veya env default
        self.demo_mode = demo_mode if demo_mode is not None else DEFAULT_DEMO_MODE
        print(f"[ORCHESTRATOR] Report {report_id}: Demo Mode = {self.demo_mode}")

        # Agent'ları oluştur - primary ve fallback ayrı
        # TSG Agent (K8s primary, local fallback) - demo_mode ile
        self.tsg_agent_k8s = TSGAgentK8s() if USE_K8S_TSG_AGENT else None
        self.tsg_agent_local = TSGAgent(demo_mode=self.demo_mode)

        # Ihale Agent (K8s primary, local fallback)
        # Demo mode'da 7 gün, normal modda 90 gün tarama
        self.ihale_agent_k8s = IhaleAgentK8s() if USE_K8S_IHALE_AGENT else None
        self.ihale_agent_local = LocalIhaleAgent(demo_mode=self.demo_mode)

        # News Agent (K8s primary, local fallback)
        # Demo mode'da 1 yıl ve 5 haber/kaynak, normal modda 3 yıl ve 15 haber/kaynak
        self.news_agent_k8s = NewsAgentK8s() if USE_K8S_NEWS_AGENT else None
        self.news_agent_local = LocalNewsAgent(demo_mode=self.demo_mode)

        # Council servisi - report_id ve demo_mode ile başlat
        self.council_service = CouncilService(report_id=report_id, demo_mode=self.demo_mode)

        # Progress callback'leri ayarla
        if self.tsg_agent_k8s:
            self.tsg_agent_k8s.set_progress_callback(self._create_progress_handler("tsg_agent"))
        self.tsg_agent_local.set_progress_callback(self._create_progress_handler("tsg_agent"))

        # K8s ve local agent'lar için aynı handler
        if self.ihale_agent_k8s:
            self.ihale_agent_k8s.set_progress_callback(self._create_progress_handler("ihale_agent"))
        self.ihale_agent_local.set_progress_callback(self._create_progress_handler("ihale_agent"))

        if self.news_agent_k8s:
            self.news_agent_k8s.set_progress_callback(self._create_progress_handler("news_agent"))
        self.news_agent_local.set_progress_callback(self._create_progress_handler("news_agent"))

    def _create_progress_handler(self, agent_id: str) -> Callable:
        """Agent progress handler oluştur - sync callback, DB + Redis Pub/Sub"""
        def sync_handler(progress: AgentProgress):
            # 1. DB'ye kaydet (sync, hemen)
            if self.db_callback:
                try:
                    self.db_callback(agent_id, progress.progress, progress.message)
                except Exception as e:
                    print(f"DB progress callback error: {e}")

            # 2. Redis'e publish et (sync, WebSocket'e köprü)
            try:
                from app.services.redis_pubsub import publish_agent_progress
                publish_agent_progress(
                    report_id=self.report_id,
                    agent_id=agent_id,
                    progress=progress.progress,
                    message=progress.message
                )
            except Exception as e:
                print(f"Redis publish error: {e}")

        return sync_handler

    async def _default_ws_callback(self, event_type: str, payload: Dict):
        """Varsayılan WebSocket callback"""
        try:
            await ws_manager.send_event(self.report_id, event_type, payload)
        except Exception as e:
            print(f"WebSocket error: {e}")

    async def _send_event(self, event_type: str, payload: Dict):
        """Event gönder - Redis Pub/Sub ile (Celery worker'dan çalışır)"""
        # Redis Pub/Sub kullan - Celery worker'dan da WebSocket'e ulaşır
        try:
            from app.services.redis_pubsub import publish_agent_event
            publish_agent_event(
                report_id=self.report_id,
                event_type=event_type,
                payload=payload
            )
        except Exception as e:
            print(f"Redis publish error: {e}")

        # Eski callback'i de çağır (backward compatibility)
        try:
            if asyncio.iscoroutinefunction(self.ws_callback):
                await self.ws_callback(event_type, payload)
            else:
                self.ws_callback(event_type, payload)
        except Exception as e:
            print(f"WS callback error: {e}")

    def _prepare_agent_summary(self, agent_id: str, result: AgentResult) -> Dict:
        """
        Agent sonuç özetini hazırla (RAM için sınırlı veri - 16GB MacBook için optimize).
        Her agent için sadece önemli özet bilgileri döndürür.
        """
        if not result.data:
            return {}

        data = result.data

        if agent_id == "tsg":
            # TSG: Firma bilgileri özeti
            tsg_sonuc = data.get("tsg_sonuc", {})
            yapilandirilmis = tsg_sonuc.get("yapilandirilmis_veri", {})
            return {
                "firma_unvani": yapilandirilmis.get("Firma Unvani"),
                "vergi_no": yapilandirilmis.get("Vergi No"),
                "toplam_ilan": tsg_sonuc.get("toplam_ilan", 0),
                "son_ilan_tarihi": tsg_sonuc.get("son_ilan_tarihi")
            }

        elif agent_id == "ihale":
            # İhale: Yasak durumu özeti
            return {
                "yasak_durumu": data.get("yasak_durumu", False),
                "risk_degerlendirmesi": data.get("risk_degerlendirmesi", "dusuk"),
                "taranan_gun_sayisi": data.get("taranan_gun_sayisi", 0),
                "bulunan_toplam_yasaklama": data.get("bulunan_toplam_yasaklama", 0)
            }

        elif agent_id == "news":
            # News: Haber istatistikleri özeti
            ozet = data.get("ozet", {})
            return {
                "toplam_haber": data.get("toplam_haber", ozet.get("toplam", 0)),
                "olumlu": ozet.get("olumlu", 0),
                "olumsuz": ozet.get("olumsuz", 0),
                "sentiment_score": ozet.get("sentiment_score", 0),
                "trend": ozet.get("trend", "notr"),
                "kaynak_sayisi": len(data.get("kaynak_dagilimi", {}))
            }

        return {}

    async def _send_agent_progress(self, agent_id: str, progress: int, message: str):
        """Agent ilerleme bildir"""
        await self._send_event("agent_progress", {
            "agent_id": agent_id,
            "progress": progress,
            "message": message
        })

    def _should_fallback(self, result: AgentResult) -> bool:
        """
        K8s agent sonucu fallback gerektiriyor mu?

        Fallback koşulları:
        1. status == "failed"
        2. Bağlantı hatası (ConnectError, timeout vb.)
        3. Veri boş veya null
        4. Çok kısa sürede (<5sn) tamamlandı ama veri yok
        """
        if result.status == "failed":
            error_str = str(result.error or "").lower()
            # Bağlantı hataları kesinlikle fallback
            if any(x in error_str for x in ["connect", "timeout", "refused", "unreachable", "bağlantı"]):
                return True
            # Diğer hatalar da fallback
            return True

        if result.status == "completed":
            # Veri yoksa veya boşsa fallback
            if result.data is None:
                return True
            if isinstance(result.data, dict) and len(result.data) == 0:
                return True
            # Çok kısa sürede bitip veri boşsa (fake completion)
            if result.duration_seconds and result.duration_seconds < 5:
                # Gerçek veri var mı kontrol et
                if isinstance(result.data, dict):
                    # İhale için: yasaklamalar listesi boş mu?
                    if "yasaklamalar" in result.data and len(result.data.get("yasaklamalar", [])) == 0:
                        if result.data.get("toplam_karar", 0) == 0:
                            # Hiç tarama yapılmadı muhtemelen
                            return True
                    # News için: haberler listesi boş mu?
                    if "haberler" in result.data and len(result.data.get("haberler", [])) == 0:
                        if result.data.get("toplam_haber", 0) == 0:
                            return True

        return False

    async def _run_ihale_with_fallback(self, company_name: str) -> AgentResult:
        """
        İhale Agent'ı fallback mekanizmasıyla çalıştır.
        K8s önce, fail olursa local.
        """
        if self.ihale_agent_k8s:
            print(f"[ORCHESTRATOR] İhale: K8s agent deneniyor...")
            try:
                result = await self.ihale_agent_k8s.execute(company_name)
                if self._should_fallback(result):
                    print(f"[ORCHESTRATOR] İhale: K8s sonuç yetersiz, LOCAL agent'a düşülüyor...")
                    print(f"[ORCHESTRATOR] İhale: K8s status={result.status}, duration={result.duration_seconds}s")
                    return await self.ihale_agent_local.execute(company_name)
                print(f"[ORCHESTRATOR] İhale: K8s başarılı, süre={result.duration_seconds}s")
                return result
            except Exception as e:
                print(f"[ORCHESTRATOR] İhale: K8s HATA: {e}, LOCAL agent'a düşülüyor...")
                return await self.ihale_agent_local.execute(company_name)
        else:
            print(f"[ORCHESTRATOR] İhale: LOCAL agent kullanılıyor (K8s devre dışı)")
            return await self.ihale_agent_local.execute(company_name)

    async def _run_news_with_fallback(self, company_name: str, alternative_names: List[str] = None) -> AgentResult:
        """
        News Agent'ı fallback mekanizmasıyla çalıştır.
        K8s önce, fail olursa local.

        Args:
            company_name: Ana firma adı (kullanıcıdan gelen)
            alternative_names: Alternatif isimler (TSG'den gelen resmi ünvan vb.)
        """
        names_str = f"{company_name}" + (f" + {alternative_names}" if alternative_names else "")
        if self.news_agent_k8s:
            print(f"[ORCHESTRATOR] News: K8s agent deneniyor... ({names_str})")
            try:
                # K8s agent'a da alternative_names geç (local ile tutarlı davranış)
                result = await self.news_agent_k8s.run(company_name, alternative_names=alternative_names)
                if self._should_fallback(result):
                    print(f"[ORCHESTRATOR] News: K8s sonuç yetersiz, LOCAL agent'a düşülüyor...")
                    print(f"[ORCHESTRATOR] News: K8s status={result.status}, duration={result.duration_seconds}s")
                    return await self.news_agent_local.run(company_name, alternative_names=alternative_names)
                print(f"[ORCHESTRATOR] News: K8s başarılı, süre={result.duration_seconds}s")
                return result
            except Exception as e:
                print(f"[ORCHESTRATOR] News: K8s HATA: {e}, LOCAL agent'a düşülüyor...")
                return await self.news_agent_local.run(company_name, alternative_names=alternative_names)
        else:
            print(f"[ORCHESTRATOR] News: LOCAL agent kullanılıyor (K8s devre dışı) - İsimler: {names_str}")
            return await self.news_agent_local.run(company_name, alternative_names=alternative_names)

    async def _run_tsg_with_fallback(self, company_name: str) -> AgentResult:
        """
        TSG Agent'ı fallback mekanizmasıyla çalıştır.
        K8s önce, fail olursa local.
        """
        if self.tsg_agent_k8s:
            print(f"[ORCHESTRATOR] TSG: K8s agent deneniyor...")
            try:
                result = await self.tsg_agent_k8s.execute(company_name)
                if self._should_fallback(result):
                    print(f"[ORCHESTRATOR] TSG: K8s sonuç yetersiz, LOCAL agent'a düşülüyor...")
                    print(f"[ORCHESTRATOR] TSG: K8s status={result.status}, duration={result.duration_seconds}s")
                    return await self.tsg_agent_local.execute(company_name)
                print(f"[ORCHESTRATOR] TSG: K8s başarılı, süre={result.duration_seconds}s")
                return result
            except Exception as e:
                print(f"[ORCHESTRATOR] TSG: K8s HATA: {e}, LOCAL agent'a düşülüyor...")
                return await self.tsg_agent_local.execute(company_name)
        else:
            print(f"[ORCHESTRATOR] TSG: LOCAL agent kullanılıyor (K8s devre dışı)")
            return await self.tsg_agent_local.execute(company_name)

    async def run(self, company_name: str) -> Dict[str, Any]:
        """
        Tam rapor sürecini çalıştır.

        Args:
            company_name: Firma adı

        Returns:
            dict: Agent sonuçları ve council kararı
        """
        start_time = datetime.utcnow()

        # Job başladı event'i
        # ============================================
        # DEMO MODE: TOPLAM 4 dakika HARD LIMIT (tüm ajanlar dahil)
        # FULL MODE: Sınırsız araştırma, sonra council
        # ============================================
        # DEMO: TSG 90s, News+İhale 150s (paralel) = TOPLAM MAX 240s
        estimated_duration = 240 if self.demo_mode else 3600  # Demo: 4dk, Full: 1 saat
        TOTAL_AGENT_LIMIT = 240 if self.demo_mode else 3600  # TOPLAM agent süresi
        TSG_TIMEOUT = 90 if self.demo_mode else 240  # Demo: 1.5dk, Full: 4dk
        PARALLEL_TIMEOUT = 150 if self.demo_mode else 3360  # Demo: 2.5dk, Full: 56dk

        # Global timer başlat
        agent_start_time = datetime.utcnow()

        print(f"[ORCHESTRATOR] Mode: {'DEMO (4dk TOPLAM limit)' if self.demo_mode else 'FULL (sınırsız)'}")
        print(f"[ORCHESTRATOR] TSG Timeout: {TSG_TIMEOUT}s, Parallel Timeout: {PARALLEL_TIMEOUT}s")

        await self._send_event("job_started", {
            "report_id": self.report_id,
            "company_name": company_name,
            "estimated_duration_seconds": estimated_duration
        })

        # ============================================
        # AŞAMA 1: TSG Agent'ı ÖNCE çalıştır
        # Demo: 90s timeout, Full: 240s timeout
        # Firma ünvanı bulunursa diğer agentlar bu ünvanı kullanır
        # ============================================

        # TSG Agent başladı
        await self._send_event("agent_started", {
            "agent_id": "tsg_agent",
            "agent_name": "TSG Agent",
            "agent_description": "Firma ünvanı aranıyor..."
        })

        print(f"[ORCHESTRATOR] TSG Agent başlıyor (timeout: {TSG_TIMEOUT}s) - Firma ünvanı aranıyor...")

        tsg_result = None
        resolved_company_name = company_name  # Default: kullanıcının yazdığı

        try:
            tsg_task = asyncio.create_task(self._run_tsg_with_fallback(company_name))
            done, pending = await asyncio.wait([tsg_task], timeout=TSG_TIMEOUT)

            if tsg_task in done:
                tsg_result = tsg_task.result()

                # TSG'den firma ünvanı bul
                if tsg_result and tsg_result.status == "completed" and tsg_result.data:
                    tsg_data = tsg_result.data
                    # tsg_sonuc içinden Firma Unvani'nı al
                    tsg_sonuc = tsg_data.get("tsg_sonuc", {})
                    yapilandirilmis = tsg_sonuc.get("yapilandirilmis_veri", {})
                    found_name = yapilandirilmis.get("Firma Unvani")

                    if found_name and found_name.strip():
                        resolved_company_name = found_name.strip()
                        print(f"[ORCHESTRATOR] ✅ TSG'den firma ünvanı bulundu: '{resolved_company_name}'")
                        print(f"[ORCHESTRATOR] Diğer agentlar bu ünvanı kullanacak")
                    else:
                        print(f"[ORCHESTRATOR] ⚠️ TSG tamamlandı ama firma ünvanı bulunamadı, orijinal isim kullanılacak: '{company_name}'")
                else:
                    print(f"[ORCHESTRATOR] ⚠️ TSG başarısız veya veri yok, orijinal isim kullanılacak: '{company_name}'")
            else:
                # Timeout
                print(f"[ORCHESTRATOR] ⚠️ TSG {TSG_TIMEOUT}s içinde tamamlanamadı, iptal ediliyor...")
                tsg_task.cancel()
                await asyncio.gather(tsg_task, return_exceptions=True)
                tsg_result = AgentResult(agent_id="tsg_agent", status="failed", error=f"Timeout - {TSG_TIMEOUT}s içinde tamamlanamadı")
                print(f"[ORCHESTRATOR] Orijinal isim kullanılacak: '{company_name}'")

        except Exception as e:
            print(f"[ORCHESTRATOR] TSG Agent hatası: {e}")
            tsg_result = AgentResult(agent_id="tsg_agent", status="failed", error=str(e))

        # TSG completed event'i
        if tsg_result and tsg_result.status == "completed":
            # Toplam ilan sayısını çıkar
            toplam_ilan = 0
            if tsg_result.data:
                tsg_sonuc = tsg_result.data.get("tsg_sonuc", {})
                toplam_ilan = tsg_sonuc.get("toplam_ilan", 0)

            await self._send_event("agent_completed", {
                "agent_id": "tsg_agent",
                "duration_seconds": tsg_result.duration_seconds,
                "summary": tsg_result.summary,  # Text summary
                "key_findings": tsg_result.key_findings,
                "warning_flags": tsg_result.warning_flags,
                "data": {
                    "toplam_ilan": toplam_ilan
                }
            })
        else:
            await self._send_event("agent_failed", {
                "agent_id": "tsg_agent",
                "error_code": "TSG_TIMEOUT_OR_ERROR",
                "error_message": tsg_result.error if tsg_result else "Bilinmeyen hata",
                "will_retry": False
            })

        # ============================================
        # AŞAMA 2: Diğer Agent'ları paralel çalıştır
        # resolved_company_name kullanılacak
        # ============================================

        # News agent için alternatif isimler hazırla
        # Hem kullanıcının girdiği isim hem de TSG'den gelen resmi ünvan kullanılacak
        news_alternative_names = []
        if resolved_company_name != company_name:
            news_alternative_names.append(resolved_company_name)

        print(f"[ORCHESTRATOR] Diğer agentlar başlıyor")
        print(f"[ORCHESTRATOR] - İhale Agent: '{resolved_company_name}'")
        print(f"[ORCHESTRATOR] - News Agent: '{company_name}' + alternatifler: {news_alternative_names}")

        # İhale ve News agent başladı event'leri
        for agent_id, agent_name in [
            ("ihale_agent", "İhale Agent"),
            ("news_agent", "Haber Agent")
        ]:
            await self._send_event("agent_started", {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_description": f"{agent_name} başlatılıyor - Firma: {resolved_company_name}"
            })

        # ============================================
        # Demo modda: Kalan süreyi hesapla (toplam 4dk'dan TSG süresi çıkar)
        # Full modda: PARALLEL_TIMEOUT kullan
        # ============================================
        elapsed_since_start = (datetime.utcnow() - agent_start_time).total_seconds()
        remaining_time = max(30, TOTAL_AGENT_LIMIT - elapsed_since_start)  # Min 30s
        agent_timeout = min(PARALLEL_TIMEOUT, remaining_time) if self.demo_mode else PARALLEL_TIMEOUT
        print(f"[ORCHESTRATOR] Agent timeout: {agent_timeout:.0f}s (elapsed: {elapsed_since_start:.0f}s, remaining: {remaining_time:.0f}s)")

        # Task'ları oluştur
        # İhale: resolved_company_name (TSG'den gelen resmi ünvan)
        # News: company_name (kullanıcı input) + resolved_company_name (TSG alternatif)
        ihale_task = asyncio.create_task(self._run_ihale_with_fallback(resolved_company_name))
        news_task = asyncio.create_task(self._run_news_with_fallback(company_name, alternative_names=news_alternative_names))
        other_tasks = [ihale_task, news_task]

        # Timeout ile bekle
        done, pending = await asyncio.wait(other_tasks, timeout=agent_timeout)

        if pending:
            print(f"[ORCHESTRATOR] {len(pending)} agent timeout oldu, iptal ediliyor...")
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        # Sonuçları topla
        def get_task_result(task, agent_id):
            if task in done and not task.cancelled():
                try:
                    return task.result()
                except Exception as e:
                    return AgentResult(agent_id=agent_id, status="failed", error=str(e))
            else:
                return AgentResult(agent_id=agent_id, status="failed", error="Timeout")

        # TSG sonucu zaten var, diğerlerini al
        ihale_result = get_task_result(ihale_task, "ihale_agent")
        news_result = get_task_result(news_task, "news_agent")

        results = [tsg_result, ihale_result, news_result]

        # Sonuçları işle
        agent_results = {}
        for i, (agent_id, result) in enumerate([
            ("tsg", results[0]),
            ("ihale", results[1]),
            ("news", results[2])
        ]):
            if isinstance(result, Exception):
                agent_results[agent_id] = AgentResult(
                    agent_id=f"{agent_id}_agent",
                    status="failed",
                    error=str(result)
                )
                await self._send_event("agent_failed", {
                    "agent_id": f"{agent_id}_agent",
                    "error_code": "AGENT_ERROR",
                    "error_message": str(result),
                    "will_retry": False
                })
            else:
                agent_results[agent_id] = result
                # Agent sonuç özetini hazırla (RAM için sınırlı veri)
                agent_summary_data = self._prepare_agent_summary(agent_id, result)
                await self._send_event("agent_completed", {
                    "agent_id": f"{agent_id}_agent",
                    "duration_seconds": result.duration_seconds,
                    "summary": result.summary,
                    "key_findings": result.key_findings,
                    "warning_flags": result.warning_flags,
                    "data": agent_summary_data  # Anlık veri gösterimi için
                })

        # ============================================
        # AŞAMA 2: İstihbarat Raporu Üret
        # ============================================

        report_generator = ReportGenerator()
        intelligence_report = report_generator.generate(
            company_name=company_name,
            tsg_data=agent_results["tsg"].data if agent_results["tsg"].status == "completed" else None,
            ihale_data=agent_results["ihale"].data if agent_results["ihale"].status == "completed" else None,
            news_data=agent_results["news"].data if agent_results["news"].status == "completed" else None
        )

        # Rapor oluşturuldu event'i
        await self._send_event("report_generated", {
            "risk_skoru": intelligence_report["risk_ozeti"]["risk_skoru"],
            "karar_onerisi": intelligence_report["risk_ozeti"]["karar_onerisi"],
            "risk_seviyesi": intelligence_report["risk_ozeti"]["risk_seviyesi"]
        })

        # ============================================
        # AŞAMA 3: Council Toplantısı
        # ============================================

        # Toplam agent süresi logu
        total_agent_time = (datetime.utcnow() - agent_start_time).total_seconds()
        print(f"[ORCHESTRATOR] ✅ Tüm ajanlar tamamlandı! Toplam agent süresi: {total_agent_time:.1f}s")
        print(f"[ORCHESTRATOR] Council toplantısı başlıyor...")

        council_result = await self.council_service.run_meeting(
            company_name=company_name,
            agent_data={
                "tsg": agent_results["tsg"].data if agent_results["tsg"].status == "completed" else None,
                "ihale": agent_results["ihale"].data if agent_results["ihale"].status == "completed" else None,
                "news": agent_results["news"].data if agent_results["news"].status == "completed" else None
            },
            intelligence_report=intelligence_report,
            ws_callback=self._send_event
        )

        # ============================================
        # AŞAMA 4: Sonuç
        # ============================================

        end_time = datetime.utcnow()
        duration = int((end_time - start_time).total_seconds())

        # Job tamamlandı event'i
        await self._send_event("job_completed", {
            "report_id": self.report_id,
            "duration_seconds": duration,
            "final_score": council_result.get("final_score", 50),
            "risk_level": council_result.get("risk_level", "orta"),
            "decision": council_result.get("decision", "inceleme_gerek")
        })

        return {
            "agent_results": {
                k: v.to_dict() for k, v in agent_results.items()
            },
            "intelligence_report": intelligence_report,
            "council_decision": council_result,
            "duration_seconds": duration
        }
