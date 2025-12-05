"""
İhale Agent - EKAP Yasaklı Listesi
Kamu ihalelerinden yasaklı olup olmadığını kontrol eder
"""
import asyncio
from typing import Optional, List, Dict
from app.agents.base_agent import BaseAgent, AgentResult


class IhaleAgent(BaseAgent):
    """
    İhale/EKAP Agent'ı.

    Görevleri:
    - EKAP sisteminde firma ara
    - Yasaklılık durumunu kontrol et
    - Aktif ve geçmiş yasakları listele
    """

    def __init__(self):
        super().__init__(
            agent_id="ihale_agent",
            agent_name="İhale Agent",
            agent_description="EKAP yasaklı listesi kontrolü"
        )

    async def run(self, company_name: str) -> AgentResult:
        """EKAP'ta firma ara ve yasaklılık durumunu kontrol et"""

        self.report_progress(10, "EKAP sisteminde aranıyor...")

        try:
            # 1. EKAP'ta ara
            await asyncio.sleep(0.5)  # Simüle gecikme
            self.report_progress(50, "Yasaklılık durumu kontrol ediliyor...")

            # 2. Yasaklılık kontrolü
            result_data = await self._check_ban_status(company_name)
            self.report_progress(100, "EKAP kontrolü tamamlandı")

            # 3. Sonuçları döndür
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

    async def _check_ban_status(self, company_name: str) -> Dict:
        """Yasaklılık durumunu kontrol et"""
        # TODO: Gerçek EKAP scraping implementasyonu

        await asyncio.sleep(0.5)  # Simüle gecikme

        # Mock data - çoğu firma yasaklı değil
        return {
            "yasak_durumu": False,
            "aktif_yasak": None,
            "gecmis_yasaklar": [],
            "kontrol_tarihi": "2024-12-06T10:00:00Z",
            "kaynak": "EKAP - Elektronik Kamu Alımları Platformu"
        }

    def _generate_summary(self, data: Dict) -> str:
        """Özet oluştur"""
        if data["yasak_durumu"]:
            yasak = data["aktif_yasak"]
            return f"DİKKAT: Firma aktif ihale yasağı altında! Sebep: {yasak.get('sebep', 'Bilinmiyor')}. Süre: {yasak.get('bitis', 'Belirsiz')} tarihine kadar."
        else:
            gecmis = len(data.get("gecmis_yasaklar", []))
            if gecmis > 0:
                return f"Aktif yasak yok, ancak geçmişte {gecmis} yasak kaydı mevcut."
            return "İhale yasağı bulunmamaktadır."

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Önemli bulguları çıkar"""
        findings = []

        if not data["yasak_durumu"]:
            findings.append("İhale yasağı yok")

        if data.get("gecmis_yasaklar"):
            findings.append(f"Geçmişte {len(data['gecmis_yasaklar'])} yasak kaydı")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarıları çıkar"""
        warnings = []

        if data["yasak_durumu"]:
            warnings.append("AKTİF İHALE YASAĞI")

        if data.get("gecmis_yasaklar"):
            warnings.append("Geçmiş ihale yasağı kaydı")

        return warnings


class YasakBilgisi:
    """Yasak bilgisi yapısı"""

    def __init__(
        self,
        sebep: str,
        baslangic: str,
        bitis: str,
        kurum: str,
        aciklama: Optional[str] = None
    ):
        self.sebep = sebep
        self.baslangic = baslangic
        self.bitis = bitis
        self.kurum = kurum
        self.aciklama = aciklama

    def to_dict(self) -> Dict:
        return {
            "sebep": self.sebep,
            "baslangic": self.baslangic,
            "bitis": self.bitis,
            "kurum": self.kurum,
            "aciklama": self.aciklama
        }
