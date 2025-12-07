"""
Orchestrator - Agent ve Council Koordinasyonu
Tüm süreci yönetir
"""
import asyncio
from typing import Callable, Dict, Optional, Any
from datetime import datetime

from app.agents.tsg import TSGAgent
from app.agents.ihale_agent import IhaleAgent
from app.agents.news_agent import NewsAgent
from app.agents.base_agent import AgentResult, AgentProgress
from app.council.council_service import CouncilService
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

    def __init__(self, report_id: str, ws_callback: Optional[Callable] = None):
        self.report_id = report_id
        self.ws_callback = ws_callback or self._default_ws_callback

        # Agent'ları oluştur
        self.tsg_agent = TSGAgent()
        self.ihale_agent = IhaleAgent()
        self.news_agent = NewsAgent()

        # Council servisi
        self.council_service = CouncilService()

        # Progress callback'leri ayarla
        self.tsg_agent.set_progress_callback(self._create_progress_handler("tsg_agent"))
        self.ihale_agent.set_progress_callback(self._create_progress_handler("ihale_agent"))
        self.news_agent.set_progress_callback(self._create_progress_handler("news_agent"))

    def _create_progress_handler(self, agent_id: str) -> Callable:
        """Agent progress handler oluştur"""
        async def handler(progress: AgentProgress):
            await self._send_agent_progress(agent_id, progress.progress, progress.message)
        return lambda p: asyncio.create_task(handler(p))

    async def _default_ws_callback(self, event_type: str, payload: Dict):
        """Varsayılan WebSocket callback"""
        try:
            await ws_manager.send_event(self.report_id, event_type, payload)
        except Exception as e:
            print(f"WebSocket error: {e}")

    async def _send_event(self, event_type: str, payload: Dict):
        """Event gönder"""
        if asyncio.iscoroutinefunction(self.ws_callback):
            await self.ws_callback(event_type, payload)
        else:
            self.ws_callback(event_type, payload)

    async def _send_agent_progress(self, agent_id: str, progress: int, message: str):
        """Agent ilerleme bildir"""
        await self._send_event("agent_progress", {
            "agent_id": agent_id,
            "progress": progress,
            "message": message
        })

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

        # Paralel çalıştır
        results = await asyncio.gather(
            self.tsg_agent.execute(company_name),
            self.ihale_agent.execute(company_name),
            self.news_agent.execute(company_name),
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
        # AŞAMA 2: Council Toplantısı
        # ============================================

        council_result = await self.council_service.run_meeting(
            company_name=company_name,
            agent_data={
                "tsg": agent_results["tsg"].data if agent_results["tsg"].status == "completed" else None,
                "ihale": agent_results["ihale"].data if agent_results["ihale"].status == "completed" else None,
                "news": agent_results["news"].data if agent_results["news"].status == "completed" else None
            },
            ws_callback=self._send_event
        )

        # ============================================
        # AŞAMA 3: Sonuç
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
            "council_decision": council_result,
            "duration_seconds": duration
        }
