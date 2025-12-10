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
from typing import Callable, Dict, Optional, Any
from datetime import datetime

from app.agents.tsg.agent import TSGAgent

# K8s configuration
USE_K8S_IHALE_AGENT = os.getenv("USE_K8S_IHALE_AGENT", "true").lower() == "true"
USE_K8S_NEWS_AGENT = os.getenv("USE_K8S_NEWS_AGENT", "true").lower() == "true"

# Her iki agent türünü de import et (fallback için)
from app.agents.ihale_agent_k8s import IhaleAgentK8s
from app.agents.ihale_agent import IhaleAgent as LocalIhaleAgent
from app.agents.news_agent_k8s import NewsAgentK8s
from app.agents.news_agent import NewsAgent as LocalNewsAgent

print(f"[ORCHESTRATOR] K8s Ihale Agent: {'ENABLED' if USE_K8S_IHALE_AGENT else 'DISABLED'} (fallback to local on failure)")
print(f"[ORCHESTRATOR] K8s News Agent: {'ENABLED' if USE_K8S_NEWS_AGENT else 'DISABLED'} (fallback to local on failure)")
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
        db_callback: Optional[Callable] = None
    ):
        self.report_id = report_id
        self.ws_callback = ws_callback or self._default_ws_callback
        self.db_callback = db_callback  # Progress'i DB'ye kaydetmek için

        # Agent'ları oluştur - primary ve fallback ayrı
        self.tsg_agent = TSGAgent()

        # Ihale Agent (K8s primary, local fallback)
        self.ihale_agent_k8s = IhaleAgentK8s() if USE_K8S_IHALE_AGENT else None
        self.ihale_agent_local = LocalIhaleAgent()

        # News Agent (K8s primary, local fallback)
        self.news_agent_k8s = NewsAgentK8s() if USE_K8S_NEWS_AGENT else None
        self.news_agent_local = LocalNewsAgent()

        # Council servisi - report_id ile başlat (Redis Pub/Sub için gerekli)
        self.council_service = CouncilService(report_id=report_id)

        # Progress callback'leri ayarla
        self.tsg_agent.set_progress_callback(self._create_progress_handler("tsg_agent"))

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

    async def _run_news_with_fallback(self, company_name: str) -> AgentResult:
        """
        News Agent'ı fallback mekanizmasıyla çalıştır.
        K8s önce, fail olursa local.
        """
        if self.news_agent_k8s:
            print(f"[ORCHESTRATOR] News: K8s agent deneniyor...")
            try:
                result = await self.news_agent_k8s.execute(company_name)
                if self._should_fallback(result):
                    print(f"[ORCHESTRATOR] News: K8s sonuç yetersiz, LOCAL agent'a düşülüyor...")
                    print(f"[ORCHESTRATOR] News: K8s status={result.status}, duration={result.duration_seconds}s")
                    return await self.news_agent_local.execute(company_name)
                print(f"[ORCHESTRATOR] News: K8s başarılı, süre={result.duration_seconds}s")
                return result
            except Exception as e:
                print(f"[ORCHESTRATOR] News: K8s HATA: {e}, LOCAL agent'a düşülüyor...")
                return await self.news_agent_local.execute(company_name)
        else:
            print(f"[ORCHESTRATOR] News: LOCAL agent kullanılıyor (K8s devre dışı)")
            return await self.news_agent_local.execute(company_name)

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
        await self._send_event("job_started", {
            "report_id": self.report_id,
            "company_name": company_name,
            "estimated_duration_seconds": 2400
        })

        # ============================================
        # AŞAMA 1: Agent'ları paralel çalıştır
        # ============================================

        # Agent başladı event'leri
        for agent_id, agent_name in [
            ("tsg_agent", "TSG Agent"),
            ("ihale_agent", "İhale Agent"),
            ("news_agent", "Haber Agent")
        ]:
            await self._send_event("agent_started", {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_description": f"{agent_name} başlatılıyor"
            })

        # Paralel çalıştır - Fallback mekanizmalı wrapper metodları kullan
        results = await asyncio.gather(
            self.tsg_agent.execute(company_name),
            self._run_ihale_with_fallback(company_name),
            self._run_news_with_fallback(company_name),
            return_exceptions=True
        )

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
                await self._send_event("agent_completed", {
                    "agent_id": f"{agent_id}_agent",
                    "duration_seconds": result.duration_seconds,
                    "summary": {
                        "key_findings": result.key_findings,
                        "warning_flags": result.warning_flags
                    }
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
