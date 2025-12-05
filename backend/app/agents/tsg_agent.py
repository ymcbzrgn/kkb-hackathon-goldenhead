"""
TSG Agent - Ticaret Sicili Gazetesi
PDF'leri okuyup firma bilgilerini çıkarır
"""
import asyncio
from typing import Optional, List, Dict
from app.agents.base_agent import BaseAgent, AgentResult
from app.llm.client import LLMClient


class TSGAgent(BaseAgent):
    """
    Ticaret Sicili Gazetesi Agent'ı.

    Görevleri:
    - TSG web sitesinde firma ara
    - İlgili PDF'leri bul ve indir
    - Vision AI ile PDF'leri oku
    - Yapısal veri çıkar (ortaklar, sermaye, yönetim, vb.)
    """

    def __init__(self):
        super().__init__(
            agent_id="tsg_agent",
            agent_name="TSG Agent",
            agent_description="Ticaret Sicili Gazetesi tarama ve analiz"
        )
        self.llm = LLMClient()

    async def run(self, company_name: str) -> AgentResult:
        """TSG'de firma ara ve bilgileri çıkar"""

        self.report_progress(10, "TSG'de firma aranıyor...")

        try:
            # 1. TSG'de ara
            search_results = await self._search_tsg(company_name)
            self.report_progress(30, f"{len(search_results)} ilan bulundu")

            if not search_results:
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "TSG'de kayıt bulunamadı"},
                    summary="Ticaret Sicili Gazetesi'nde firma kaydı bulunamadı",
                    key_findings=[],
                    warning_flags=["TSG kaydı yok"]
                )

            # 2. PDF'leri işle
            self.report_progress(50, "PDF'ler analiz ediliyor...")
            processed_data = await self._process_pdfs(search_results)
            self.report_progress(80, "Veriler yapılandırılıyor...")

            # 3. Sonuçları derle
            result_data = self._compile_results(processed_data)
            self.report_progress(100, "TSG analizi tamamlandı")

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                data=result_data,
                summary=self._generate_summary(result_data),
                key_findings=self._extract_key_findings(result_data),
                warning_flags=self._extract_warnings(result_data)
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )

    async def _search_tsg(self, company_name: str) -> List[Dict]:
        """TSG'de firma ara"""
        # TODO: Gerçek TSG scraping implementasyonu
        # Şimdilik mock data

        await asyncio.sleep(1)  # Simüle gecikme

        # Mock search results
        return [
            {"type": "kurulus", "date": "2018-03-15", "pdf_url": "mock_url_1"},
            {"type": "sermaye_artisi", "date": "2024-03-01", "pdf_url": "mock_url_2"},
            {"type": "yonetici_degisikligi", "date": "2024-06-15", "pdf_url": "mock_url_3"},
        ]

    async def _process_pdfs(self, search_results: List[Dict]) -> List[Dict]:
        """PDF'leri Vision AI ile işle"""
        # TODO: Gerçek PDF işleme implementasyonu
        # qwen3-omni-30b ile Vision API kullanılacak

        processed = []
        for i, result in enumerate(search_results):
            await asyncio.sleep(0.5)  # Simüle gecikme
            self.report_progress(
                50 + int((i + 1) / len(search_results) * 30),
                f"{i + 1}/{len(search_results)} PDF işlendi"
            )

            # Mock processed data
            processed.append({
                "type": result["type"],
                "date": result["date"],
                "extracted_data": {}
            })

        return processed

    def _compile_results(self, processed_data: List[Dict]) -> Dict:
        """Sonuçları derle"""
        # TODO: Gerçek veri derleme

        return {
            "kurulus_tarihi": "2018-03-15",
            "sermaye": 5000000,
            "sermaye_para_birimi": "TRY",
            "adres": "Maslak, İstanbul",
            "faaliyet_konusu": "Yazılım geliştirme, yapay zeka",
            "ortaklar": [
                {"ad": "Ahmet Yılmaz", "pay_orani": 40},
                {"ad": "XYZ Yatırım A.Ş.", "pay_orani": 20},
                {"ad": "Mehmet Demir", "pay_orani": 40}
            ],
            "yonetim_kurulu": [
                {"ad": "Ahmet Yılmaz", "gorev": "Başkan"},
                {"ad": "Ayşe Kaya", "gorev": "Üye"}
            ],
            "sermaye_degisiklikleri": [
                {"tarih": "2024-03-01", "eski": 3000000, "yeni": 5000000}
            ],
            "yonetici_degisiklikleri": [
                {"tarih": "2024-01-15", "eski": "Ali Veli", "yeni": "Ayşe Kaya", "gorev": "Genel Müdür"},
                {"tarih": "2024-04-20", "eski": "Can Demir", "yeni": "Emre Yıldız", "gorev": "Genel Müdür"},
                {"tarih": "2024-06-15", "eski": "Emre Yıldız", "yeni": "Fatma Öz", "gorev": "Genel Müdür"}
            ],
            "tsg_ilan_sayisi": len(processed_data)
        }

    def _generate_summary(self, data: Dict) -> str:
        """Özet oluştur"""
        return f"Firma {data['kurulus_tarihi']} tarihinde kurulmuş, sermayesi {data['sermaye']:,} TL. {len(data['ortaklar'])} ortağı var. Son dönemde {len(data['yonetici_degisiklikleri'])} yönetici değişikliği tespit edildi."

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Önemli bulguları çıkar"""
        findings = []

        if data.get("sermaye_degisiklikleri"):
            findings.append("Sermaye artışı tespit edildi")

        if len(data.get("yonetici_degisiklikleri", [])) >= 3:
            findings.append(f"{len(data['yonetici_degisiklikleri'])} yönetici değişikliği (dikkat!)")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarıları çıkar"""
        warnings = []

        yonetici_degisiklikleri = data.get("yonetici_degisiklikleri", [])
        if len(yonetici_degisiklikleri) >= 3:
            warnings.append("Yüksek yönetici sirkülasyonu")

        return warnings
