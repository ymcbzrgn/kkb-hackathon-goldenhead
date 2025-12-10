"""
Ihale Agent K8s Adapter - Kubernetes Ihale Orchestrator'i cagirir.

Bu adapter mevcut sisteme entegre olur ve K8s'deki ihale-orchestrator
service'ini HTTP ile cagirir.

Toggle: USE_K8S_IHALE_AGENT=true environment variable ile aktif edilir.

Avantajlar:
- Paralel OCR (3 pod)
- 10 dakika hard timeout
- Partial results destegi
- ~60-150s toplam sure (mevcut 200-300s yerine)
"""
import asyncio
import os
from typing import Optional, List, Dict
import httpx

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.progress_simulator import ProgressSimulator, SimulatorConfig


# K8s Ihale Orchestrator URL
IHALE_ORCHESTRATOR_URL = os.getenv(
    "IHALE_ORCHESTRATOR_URL",
    "http://localhost:8081"  # K8s icinde: http://ihale-orchestrator.ihale-agent:8080
)

# Timeout (saniye) - 10 dakika hard limit
K8S_TIMEOUT = int(os.getenv("K8S_IHALE_TIMEOUT", "600"))


class IhaleAgentK8s(BaseAgent):
    """
    Kubernetes Ihale Agent Adapter.

    K8s'deki ihale-orchestrator service'ini cagirarak
    Resmi Gazete yasaklama kararlarini tarar.
    """

    def __init__(self):
        super().__init__(
            agent_id="ihale_agent",
            agent_name="Ihale Yasaklama Agent (K8s)",
            agent_description="Resmi Gazete yasaklama kararlari kontrolu (Kubernetes)"
        )
        self.report_id: Optional[str] = None

    def set_report_id(self, report_id: str):
        """Report ID'yi set et (progress tracking icin)."""
        self.report_id = report_id

    async def run(self, company_name: str, vergi_no: Optional[str] = None) -> AgentResult:
        """
        K8s Ihale Orchestrator'i cagir.

        Args:
            company_name: Firma adi
            vergi_no: Vergi numarasi (opsiyonel)

        Returns:
            AgentResult: Mevcut ihale_agent.py ile uyumlu format
        """
        self.report_progress(5, "K8s Ihale Orchestrator'a baglaniliyor...")

        try:
            # Progress simulator - K8s beklerken gercekci ilerleme goster
            simulator = ProgressSimulator(
                progress_callback=self.report_progress,
                config=SimulatorConfig(
                    start_progress=10,
                    max_progress=85,
                    initial_speed=2.5,
                    decay_rate=0.93,
                    tick_interval=1.5
                ),
                messages=[
                    "Resmi Gazete arsivi taraniyor...",
                    "PDF dokumanlari okunuyor...",
                    "OCR islemi yapiliyor...",
                    "Yasaklama kararlari analiz ediliyor...",
                    "Eslestirme kontrolu yapiliyor...",
                ]
            )

            async with httpx.AsyncClient(timeout=K8S_TIMEOUT) as client:
                # Simulasyonu arka planda baslat
                sim_task = asyncio.create_task(simulator.start())

                try:
                    # K8s Ihale Orchestrator'i cagir
                    response = await client.post(
                        f"{IHALE_ORCHESTRATOR_URL}/api/ihale/check",
                        json={
                            "company_name": company_name,
                            "vergi_no": vergi_no,
                            "days": 90,
                            "request_id": self.report_id
                        }
                    )
                finally:
                    # HTTP tamamlaninca simulasyonu durdur
                    simulator.stop()
                    await sim_task

                if response.status_code != 200:
                    raise Exception(f"Orchestrator HTTP {response.status_code}: {response.text[:200]}")

                result = response.json()

                self.report_progress(90, f"{result.get('toplam_karar', 0)} karar tarandi")

                # Sonuclari mevcut format'a donustur
                yasaklamalar = result.get("yasaklama_kararlari", [])
                yasakli_mi = result.get("yasakli_mi", False)

                # HACKATHON formatina donustur
                yasaklama_list = []
                for y in yasaklamalar:
                    yasaklama_list.append({
                        "kaynak": y.get("kaynak", "Resmi Gazete"),
                        "tarih": y.get("tarih", ""),
                        "yasakli_firma": y.get("yasakli_firma"),
                        "vergi_no": y.get("vergi_no"),
                        "tc_kimlik": y.get("tc_kimlik"),
                        "yasaklayan_kurum": y.get("yasaklayan_kurum"),
                        "yasak_suresi": y.get("yasak_suresi"),
                        "kanun_dayanagi": y.get("kanun_dayanagi"),
                        "eslestirme_skoru": y.get("eslestirme_skoru", 0),
                        "eslestirme_nedeni": y.get("eslestirme_nedeni"),
                        "resmi_gazete_sayi": y.get("resmi_gazete_sayi"),
                        "resmi_gazete_tarih": y.get("resmi_gazete_tarih")
                    })

                # Result data
                result_data = {
                    "yasakli_mi": yasakli_mi,
                    "yasaklamalar": yasaklama_list,
                    "toplam_karar": result.get("toplam_karar", 0),
                    "eslesen_karar": result.get("eslesen_karar", 0),
                    "taranan_gun": result.get("taranan_gun", 0),
                    # K8s metrics
                    "k8s_metrics": {
                        "scraper_duration_ms": result.get("scraper_duration_ms", 0),
                        "ocr_duration_ms": result.get("ocr_duration_ms", 0),
                        "total_duration_seconds": result.get("total_duration_seconds", 0),
                        "partial_results": result.get("partial_results", False)
                    }
                }

                self.report_progress(100, "Ihale kontrolu tamamlandi")

                # Summary olustur
                summary = self._generate_summary(result_data)
                key_findings = self._extract_key_findings(result_data)
                warnings = self._extract_warnings(result_data)

                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data=result_data,
                    summary=summary,
                    key_findings=key_findings,
                    warning_flags=warnings
                )

        except httpx.TimeoutException:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=f"K8s Ihale Orchestrator timeout ({K8S_TIMEOUT}s)"
            )
        except httpx.ConnectError as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=f"K8s Ihale Orchestrator baglanti hatasi: {e}"
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )

    def _generate_summary(self, data: Dict) -> str:
        """Ozet olustur."""
        yasakli_mi = data.get("yasakli_mi", False)
        toplam = data.get("toplam_karar", 0)
        eslesen = data.get("eslesen_karar", 0)
        taranan_gun = data.get("taranan_gun", 0)
        k8s = data.get("k8s_metrics", {})
        duration = k8s.get("total_duration_seconds", 0)

        if yasakli_mi:
            return (
                f"UYARI: Firma ihale yasakli! "
                f"{eslesen}/{toplam} karar eslesti. "
                f"Son {taranan_gun} gun tarandi. "
                f"(K8s: {duration:.1f}s)"
            )
        else:
            return (
                f"Firma ihale yasakli degil. "
                f"{toplam} karar incelendi, hicbiri eslesmiyor. "
                f"Son {taranan_gun} gun tarandi. "
                f"(K8s: {duration:.1f}s)"
            )

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Onemli bulgulari cikar."""
        findings = []

        yasakli_mi = data.get("yasakli_mi", False)
        eslesen = data.get("eslesen_karar", 0)
        yasaklamalar = data.get("yasaklamalar", [])

        if yasakli_mi:
            findings.append(f"IHALE YASAKLI - {eslesen} karar eslesti")

            # En yuksek skorlu esleme
            if yasaklamalar:
                en_yuksek = max(yasaklamalar, key=lambda x: x.get("eslestirme_skoru", 0))
                findings.append(f"En guclu eslestirme: {en_yuksek.get('eslestirme_nedeni', 'Bilinmiyor')}")

                # Yasak suresi
                if en_yuksek.get("yasak_suresi"):
                    findings.append(f"Yasak suresi: {en_yuksek['yasak_suresi']}")
        else:
            findings.append("Ihale yasagi bulunamadi")

        # K8s metrics
        k8s = data.get("k8s_metrics", {})
        if k8s.get("partial_results"):
            findings.append("K8s: Kismi sonuclar (timeout)")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarilari cikar."""
        warnings = []

        yasakli_mi = data.get("yasakli_mi", False)
        yasaklamalar = data.get("yasaklamalar", [])

        if yasakli_mi:
            warnings.append("KRITIK: Firma ihale yasakli!")

            # Yuksek skorlu eslesmeler
            for y in yasaklamalar:
                if y.get("eslestirme_skoru", 0) >= 0.9:
                    warnings.append(f"Kesin eslestirme: {y.get('yasaklayan_kurum', 'Bilinmiyor')}")
                elif y.get("eslestirme_skoru", 0) >= 0.7:
                    warnings.append(f"Yuksek olasilikli eslestirme ({y.get('eslestirme_skoru', 0):.0%})")

        # K8s warnings
        k8s = data.get("k8s_metrics", {})
        if k8s.get("partial_results"):
            warnings.append("K8s: Timeout - tum kararlar incelenemedi")

        return warnings


# Test
if __name__ == "__main__":
    async def test():
        agent = IhaleAgentK8s()

        def progress_callback(progress_info):
            print(f"[{progress_info.progress:3d}%] {progress_info.message}")

        agent.set_progress_callback(progress_callback)

        print("\n" + "="*60)
        print("IHALE AGENT K8S TEST")
        print("="*60 + "\n")

        result = await agent.run("ASELSAN", vergi_no="1234567890")

        print("\n" + "="*60)
        print("SONUC")
        print("="*60)
        print(f"Status: {result.status}")
        print(f"Summary: {result.summary}")
        print(f"Key Findings: {result.key_findings}")
        print(f"Warnings: {result.warning_flags}")

        if result.data:
            k8s = result.data.get("k8s_metrics", {})
            print(f"\nK8s Metrics:")
            print(f"  Duration: {k8s.get('total_duration_seconds', 0)}s")
            print(f"  Scraper: {k8s.get('scraper_duration_ms', 0)}ms")
            print(f"  OCR: {k8s.get('ocr_duration_ms', 0)}ms")
            print(f"  Partial: {k8s.get('partial_results', False)}")

    asyncio.run(test())
