"""
Base Agent
Tüm agent'ların temel sınıfı
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class AgentProgress:
    """Agent ilerleme durumu"""
    agent_id: str
    progress: int  # 0-100
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class AgentResult:
    """Agent sonucu"""
    agent_id: str
    status: str  # completed, failed
    data: Optional[Dict] = None
    error: Optional[str] = None
    duration_seconds: int = 0
    summary: Optional[str] = None
    key_findings: list = field(default_factory=list)
    warning_flags: list = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "warning_flags": self.warning_flags
        }


class BaseAgent(ABC):
    """
    Temel Agent sınıfı.
    Tüm agent'lar bu sınıftan türetilir.
    """

    def __init__(self, agent_id: str, agent_name: str, agent_description: str = ""):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.progress_callback: Optional[Callable[[AgentProgress], None]] = None
        self.start_time: Optional[float] = None

    def set_progress_callback(self, callback: Callable[[AgentProgress], None]):
        """Progress callback'ini ayarla"""
        self.progress_callback = callback

    def report_progress(self, progress: int, message: str):
        """İlerleme bildir"""
        if self.progress_callback:
            self.progress_callback(AgentProgress(
                agent_id=self.agent_id,
                progress=progress,
                message=message
            ))

    def _start_timer(self):
        """Zamanlayıcıyı başlat"""
        self.start_time = time.time()

    def _get_duration(self) -> int:
        """Geçen süreyi hesapla"""
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0

    @abstractmethod
    async def run(self, company_name: str) -> AgentResult:
        """
        Agent'ı çalıştır.
        Alt sınıflar bu metodu implement etmeli.

        Args:
            company_name: Firma adı

        Returns:
            AgentResult: Agent sonucu
        """
        pass

    async def execute(self, company_name: str) -> AgentResult:
        """
        Agent'ı çalıştır (wrapper).
        Timing ve error handling ekler.
        """
        self._start_timer()
        self.report_progress(0, f"{self.agent_name} başlatılıyor...")

        try:
            result = await self.run(company_name)
            result.duration_seconds = self._get_duration()
            self.report_progress(100, f"{self.agent_name} tamamlandı")
            return result

        except Exception as e:
            self.report_progress(0, f"{self.agent_name} hata aldı: {str(e)}")
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e),
                duration_seconds=self._get_duration()
            )
