"""
TSG Agent K8s Adapter - Kubernetes TSG Scraper'i cagirir.

Bu adapter mevcut sisteme entegre olur ve K8s'deki tsg-scraper
service'ini HTTP ile cagirir.

Toggle: USE_K8S_TSG_AGENT=true environment variable ile aktif edilir.

Avantajlar:
- ARM64 Mac uyumlulugu (Playwright K8s icinde calisir)
- Izole browser pool
- 5 dakika hard timeout
"""
import asyncio
import os
from typing import Optional, List, Dict
import httpx

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.progress_simulator import ProgressSimulator, SimulatorConfig


# K8s TSG Scraper URL
TSG_SCRAPER_URL = os.getenv(
    "TSG_SCRAPER_URL",
    "http://localhost:8083"  # K8s icinde: http://tsg-scraper.tsg-agent:8080
)

# Timeout (saniye) - 5 dakika hard limit
K8S_TIMEOUT = int(os.getenv("K8S_TSG_TIMEOUT", "300"))


class TSGAgentK8s(BaseAgent):
    """
    Kubernetes TSG Agent Adapter.

    K8s'deki tsg-scraper service'ini cagirarak
    Ticaret Sicili Gazetesi ilanlarini tarar.
    """

    def __init__(self):
        super().__init__(
            agent_id="tsg_agent",
            agent_name="TSG Agent (K8s)",
            agent_description="Ticaret Sicili Gazetesi ilanlari kontrolu (Kubernetes)"
        )
        self.report_id: Optional[str] = None

    def set_report_id(self, report_id: str):
        """Report ID'yi set et (progress tracking icin)."""
        self.report_id = report_id

    async def run(self, company_name: str) -> AgentResult:
        """
        K8s TSG Scraper'i cagir.

        Args:
            company_name: Firma adi

        Returns:
            AgentResult: Mevcut tsg_agent.py ile uyumlu format
        """
        self.report_progress(5, "K8s TSG Scraper'a baglaniliyor...")

        try:
            # Progress simulator - K8s beklerken gercekci ilerleme goster
            simulator = ProgressSimulator(
                progress_callback=self.report_progress,
                config=SimulatorConfig(
                    start_progress=10,
                    max_progress=85,
                    initial_speed=2.0,
                    decay_rate=0.92,
                    tick_interval=2.0
                ),
                messages=[
                    "TSG sitesine baglaniliyor...",
                    "Login yapiliyor...",
                    "CAPTCHA cozuluyor...",
                    "Firma araniyor...",
                    "Ilanlar listeleniyor...",
                    "PDF indiriliyor...",
                    "OCR islemi yapiliyor...",
                    "Veri analizi yapiliyor...",
                ]
            )

            async with httpx.AsyncClient(timeout=K8S_TIMEOUT) as client:
                # Simulasyonu arka planda baslat
                sim_task = asyncio.create_task(simulator.start())

                try:
                    # K8s TSG Scraper'i cagir
                    response = await client.post(
                        f"{TSG_SCRAPER_URL}/api/tsg/search",
                        json={
                            "company_name": company_name,
                            "request_id": self.report_id
                        }
                    )

                finally:
                    # Simulasyonu durdur
                    simulator.stop()
                    await sim_task

                # Response'u isle
                if response.status_code != 200:
                    self.report_progress(100, "K8s TSG hatasi!")
                    return AgentResult(
                        agent_id=self.agent_id,
                        status="failed",
                        data=None,
                        summary=f"K8s TSG HTTP hatasi: {response.status_code}",
                        key_findings=[],
                        warning_flags=[f"HTTP {response.status_code}"],
                        error=f"HTTP {response.status_code}: {response.text[:200]}"
                    )

                data = response.json()

                # K8s response -> AgentResult donusumu
                return self._convert_to_agent_result(data, company_name)

        except httpx.TimeoutException:
            self.report_progress(100, "K8s TSG timeout!")
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                data=None,
                summary=f"K8s TSG timeout ({K8S_TIMEOUT}s)",
                key_findings=[],
                warning_flags=["TIMEOUT"],
                error=f"K8s TSG Scraper timeout ({K8S_TIMEOUT}s)"
            )

        except httpx.ConnectError as e:
            self.report_progress(100, "K8s TSG baglanti hatasi!")
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                data=None,
                summary=f"K8s TSG baglanti hatasi",
                key_findings=[],
                warning_flags=["CONNECTION_ERROR"],
                error=f"K8s TSG Scraper baglanti hatasi: {e}"
            )

        except Exception as e:
            self.report_progress(100, f"K8s TSG hatasi: {str(e)[:50]}")
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                data=None,
                summary=f"K8s TSG beklenmeyen hata",
                key_findings=[],
                warning_flags=["UNEXPECTED_ERROR"],
                error=str(e)
            )

    def _convert_to_agent_result(self, data: Dict, company_name: str) -> AgentResult:
        """
        K8s TSG response'unu AgentResult formatina donustur.

        Args:
            data: K8s TSG Scraper response JSON
            company_name: Aranan firma adi

        Returns:
            AgentResult: Mevcut TSG Agent ile uyumlu format
        """
        status = data.get("status", "failed")
        tsg_sonuc = data.get("tsg_sonuc", {})
        error = data.get("error")

        # Veri cikar
        gazete_bilgisi = tsg_sonuc.get("gazete_bilgisi", {}) if tsg_sonuc else {}
        yapilandirilmis_veri = tsg_sonuc.get("yapilandirilmis_veri", {}) if tsg_sonuc else {}
        sicil_bilgisi = tsg_sonuc.get("sicil_bilgisi", {}) if tsg_sonuc else {}

        # Hackathon formatinda data olustur
        result_data = {
            "firma_adi": company_name,
            "tsg_sonuc": {
                "toplam_ilan": tsg_sonuc.get("toplam_ilan", 0) if tsg_sonuc else 0,
                "secilen_ilan_index": tsg_sonuc.get("secilen_ilan_index", 0) if tsg_sonuc else 0,
                "gazete_bilgisi": {
                    "gazete_no": gazete_bilgisi.get("gazete_no"),
                    "tarih": gazete_bilgisi.get("tarih"),
                    "ilan_tipi": gazete_bilgisi.get("ilan_tipi"),
                    "screenshot_path": None,  # Base64 olarak gelir, path yok
                    "pdf_path": None,
                    "detay_url": gazete_bilgisi.get("detay_url"),
                },
                "yapilandirilmis_veri": {
                    "Firma Unvani": yapilandirilmis_veri.get("firma_unvani"),
                    "Tescil Konusu": yapilandirilmis_veri.get("tescil_konusu"),
                    "Mersis Numarasi": yapilandirilmis_veri.get("mersis_numarasi"),
                    "Yoneticiler": yapilandirilmis_veri.get("yoneticiler"),
                    "Imza Yetkilisi": yapilandirilmis_veri.get("imza_yetkilisi"),
                    "Sermaye": yapilandirilmis_veri.get("sermaye"),
                    "Kurulus_Tarihi": yapilandirilmis_veri.get("kurulus_tarihi"),
                    "Faaliyet_Konusu": yapilandirilmis_veri.get("faaliyet_konusu"),
                },
                "sicil_bilgisi": sicil_bilgisi,
            },
            "veri_kaynagi": "TSG_K8s",
            "status": status,
            # K8s metrics
            "k8s_metrics": {
                "duration_seconds": data.get("duration_seconds", 0),
                "scraper_url": TSG_SCRAPER_URL,
            }
        }

        # Base64 verileri ayri olarak ekle (buyuk olabilir)
        if gazete_bilgisi.get("screenshot_base64"):
            result_data["screenshot_base64"] = gazete_bilgisi["screenshot_base64"]
        if gazete_bilgisi.get("pdf_base64"):
            result_data["pdf_base64"] = gazete_bilgisi["pdf_base64"]

        # Key findings
        key_findings = data.get("key_findings", [])
        if not key_findings and yapilandirilmis_veri:
            if yapilandirilmis_veri.get("firma_unvani"):
                key_findings.append(f"Firma: {yapilandirilmis_veri['firma_unvani']}")
            if yapilandirilmis_veri.get("tescil_konusu"):
                key_findings.append(f"Tescil: {yapilandirilmis_veri['tescil_konusu']}")

        # Summary
        summary = data.get("summary", "")
        if not summary:
            toplam = tsg_sonuc.get("toplam_ilan", 0) if tsg_sonuc else 0
            if status == "completed":
                summary = f"{company_name} icin TSG'de {toplam} ilan bulundu."
            elif status == "not_found":
                summary = f"{company_name} icin TSG'de ilan bulunamadi."
            else:
                summary = f"TSG arama basarisiz: {error or 'Bilinmeyen hata'}"

        # Warning flags
        warning_flags = data.get("warning_flags", [])
        if status == "not_found":
            warning_flags.append("TSG_ILAN_YOK")

        self.report_progress(100, "TSG analizi tamamlandi")

        return AgentResult(
            agent_id=self.agent_id,
            status=status if status != "not_found" else "completed",
            data=result_data,
            summary=summary,
            key_findings=key_findings,
            warning_flags=warning_flags,
            error=error
        )


# Test
if __name__ == "__main__":
    async def test():
        agent = TSGAgentK8s()

        def progress_callback(progress_info):
            print(f"[{progress_info.progress:3d}%] {progress_info.message}")

        agent.set_progress_callback(progress_callback)

        print("=" * 50)
        print("TSG Agent K8s Test")
        print("=" * 50)

        result = await agent.run("Koç Holding")

        print(f"\nStatus: {result.status}")
        print(f"Summary: {result.summary}")
        print(f"Key Findings: {result.key_findings}")
        print(f"Warning Flags: {result.warning_flags}")

        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(test())
