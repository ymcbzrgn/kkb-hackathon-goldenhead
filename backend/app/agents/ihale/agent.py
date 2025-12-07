"""
Ihale Agent - Resmi Gazete Yasaklama Karari Kontrolu

TSG Agent tarzi agentic yapi:
- LLM destekli analiz (temperature=0.1)
- System + User prompt ayrimi (token tasarrufu)
- Halusnasyon korumali
- Progress reporting
- Moduler yapi (scraper, pdf_reader, company_matcher ayri)

HACKATHON GEREKSINIMLERI:
1. Resmi Gazete'den gercek yasak verisi cek
2. LLM ile analiz et
3. 12 baslik formatinda sonuc dondur

KAYNAK: resmigazete.gov.tr -> Cesitli Ilanlar -> Yasaklama Kararlari
"""
import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.ihale.scraper import ResmiGazeteScraper
from app.agents.ihale.pdf_reader import IhalePDFReader
from app.agents.ihale.company_matcher import IhaleCompanyMatcher
from app.agents.ihale.logger import log, step, success, error, warn, Timer
from app.llm.client import LLMClient


# ============================================
# SYSTEM PROMPT (Sabit - Cache'lenir)
# ============================================
IHALE_SYSTEM_PROMPT = """Sen bir Ihale Yasakli Listesi analiz uzmanisin.

ROL: Resmi Gazete'den PDF formatinda yayinlanan "Ihalelere Katilmaktan
Yasaklama Karari" belgelerini analiz ediyorsun.

ZORUNLU CIKTI ALANLARI (12 Baslik):
1. yasak_durumu: true/false (aktif yasak var mi?)
2. yasak_kayit_no: Yasakli Kayit No
3. ihale_kayit_no: IKN/ISKN numarasi
4. yasaklayan_kurum: Karar veren bakanlik/kurum
5. ihale_idaresi: Ihaleyi yapan idare bilgileri (adi, adresi)
6. yasakli_kisi: Yasaklanan gercek/tuzel kisi bilgileri (adi, vergi_no, tc, adresi)
7. ortaklar: Ortak bilgileri listesi
8. kanun_dayanagi: Yasaklama kanun dayanagi (ornek: 4735 Sayili Kanun)
9. yasak_kapsami: "Tum Ihalelerden" veya "Belirli Ihalelerden"
10. yasak_suresi: Sure (ornek: "1 / YIL", "6 / AY")
11. resmi_gazete: Resmi Gazete sayi ve tarih bilgisi
12. risk_degerlendirmesi: "dusuk" / "orta" / "yuksek"

RISK DEGERLENDIRME KURALLARI:
- Yasak yok = "dusuk"
- Gecmis yasak var, aktif yok = "orta"
- Aktif yasak VAR = "yuksek"

KURALLAR:
- SADECE Resmi Gazete verisini kullan
- ASLA tahmin yapma, varsayimda bulunma!
- Bulunamayan alanlar icin null dondur
- Turkce karakterleri dogru kullan

CIKTI FORMATI:
Sadece JSON dondur, aciklama yapma!

{
    "yasak_durumu": true veya false,
    "yasak_kayit_no": "..." veya null,
    "ihale_kayit_no": "..." veya null,
    "yasaklayan_kurum": "..." veya null,
    "ihale_idaresi": {"adi": "...", "adresi": "..."} veya null,
    "yasakli_kisi": {"adi": "...", "vergi_no": "...", "tc": "...", "adresi": "..."} veya null,
    "ortaklar": [...] veya [],
    "kanun_dayanagi": "..." veya null,
    "yasak_kapsami": "..." veya null,
    "yasak_suresi": "..." veya null,
    "resmi_gazete": {"sayi": "...", "tarih": "..."} veya null,
    "risk_degerlendirmesi": "dusuk" veya "orta" veya "yuksek"
}"""


# ============================================
# USER PROMPT TEMPLATE (Dinamik)
# ============================================
IHALE_USER_PROMPT_TEMPLATE = """RESMI GAZETE - IHALE YASAKLI KARARI

Firma Sorgusu: {company_name}
Vergi No: {vergi_no}
Sorgu Tarihi: {sorgu_tarihi}

BULUNAN YASAKLAMA KARARI:
{yasaklama_verisi}

HAM METIN (PDF/HTML):
{ham_metin}

RESMI GAZETE BILGISI:
- Tarih: {gazete_tarih}
- Kurum: {kurum}

Yukaridaki yasaklama kararini analiz et ve JSON formatinda dondur."""


# User prompt - yasak bulunamadi
IHALE_USER_PROMPT_NO_BAN = """RESMI GAZETE - IHALE YASAKLI KARARI

Firma Sorgusu: {company_name}
Vergi No: {vergi_no}
Sorgu Tarihi: {sorgu_tarihi}
Taranan Gun Sayisi: {taranan_gun}

SONUC: Bu firma icin son {taranan_gun} gun icinde yasaklama karari BULUNAMADI.

Yukaridaki bilgiye gore JSON formatinda dondur (yasak_durumu: false)."""


class IhaleAgent(BaseAgent):
    """
    Ihale Agent - Resmi Gazete yasak kontrolu.

    TSG Agent tarzi agentic yapi:
    - ResmiGazeteScraper: Playwright ile web scraping
    - IhalePDFReader: PyMuPDF + Tesseract OCR
    - IhaleCompanyMatcher: LLM ile firma eslestirme
    - LLMClient: Sonuc analizi

    HACKATHON OUTPUT (12 Baslik):
    1. yasak_durumu
    2. yasak_kayit_no
    3. ihale_kayit_no
    4. yasaklayan_kurum
    5. ihale_idaresi
    6. yasakli_kisi
    7. ortaklar
    8. kanun_dayanagi
    9. yasak_kapsami
    10. yasak_suresi
    11. resmi_gazete
    12. risk_degerlendirmesi
    """

    # Timeout (hackathon guvenligi)
    MAX_EXECUTION_TIME = 300  # 5 dakika (90 gun tarama icin)

    # Varsayilan tarama suresi
    DEFAULT_SEARCH_DAYS = 90

    def __init__(self):
        super().__init__(
            agent_id="ihale_agent",
            agent_name="Ihale Agent",
            agent_description="Resmi Gazete ihale yasak kontrolu - Agentic yapida"
        )
        self.llm = LLMClient()
        self.company_matcher = IhaleCompanyMatcher()
        self.pdf_reader = IhalePDFReader()

    async def run(
        self,
        company_name: str,
        vergi_no: Optional[str] = None,
        mersis_no: Optional[str] = None,
        search_days: int = 90
    ) -> AgentResult:
        """
        Ana calistirma metodu - TSG tarzi.

        Args:
            company_name: Aranacak firma adi
            vergi_no: TSG'den alinan Vergi Numarasi (opsiyonel)
            mersis_no: TSG'den alinan Mersis Numarasi (opsiyonel)
            search_days: Kac gun geriye taranacak (default: 90)

        Returns:
            AgentResult: Hackathon formatinda sonuc
        """
        step(f"IHALE AGENT BASLIYOR: {company_name}")
        self.report_progress(5, "Ihale Agent baslatiliyor...")

        try:
            with Timer("Ihale Agent toplam sure"):
                # 1. TSG firma bilgilerini hazirla
                tsg_company = {
                    "firma_adi": company_name,
                    "vergi_no": vergi_no,
                    "mersis_no": mersis_no
                }

                self.report_progress(10, "Firma bilgileri hazirlandi")

                # 2. Resmi Gazete Taramasi
                step("RESMI GAZETE TARAMASI")
                self.report_progress(15, f"Resmi Gazete taranıyor (son {search_days} gün)...")

                async with ResmiGazeteScraper() as scraper:
                    scrape_result = await scraper.search_yasaklama_kararlari(
                        days=search_days
                    )

                self.report_progress(50, f"Tarama tamamlandi: {scrape_result['bulunan_ilan_sayisi']} yasaklama karari")

                # 3. Yasaklama kararlari icinden firma ara
                step("FIRMA ESLESTIRME")
                self.report_progress(55, "Firma eslestirme yapiliyor...")

                yasaklama_listesi = scrape_result.get("yasaklama_kararlari", [])
                eslesen_yasaklama = None

                if yasaklama_listesi:
                    # PDF/HTML iceriklerini oku ve yapisal veri cikar
                    processed_list = []
                    for i, yasaklama in enumerate(yasaklama_listesi):
                        self.report_progress(
                            55 + int((i / len(yasaklama_listesi)) * 20),
                            f"PDF okuma {i+1}/{len(yasaklama_listesi)}..."
                        )

                        # PDF veya HTML icerigini isle
                        if yasaklama.get("pdf_path"):
                            pdf_result = await self.pdf_reader.read_yasaklama_karari(
                                yasaklama["pdf_path"]
                            )
                            yasaklama["yapisal_veri"] = pdf_result.get("yapisal_veri", {})
                            yasaklama["ham_metin"] = pdf_result.get("ham_metin", "")

                        elif yasaklama.get("pdf_content"):
                            html_result = await self.pdf_reader.read_html_content(
                                yasaklama["pdf_content"]
                            )
                            yasaklama["yapisal_veri"] = html_result.get("yapisal_veri", {})
                            yasaklama["ham_metin"] = html_result.get("ham_metin", "")

                        processed_list.append(yasaklama)

                    # Firma eslestirme
                    eslesen_yasaklama = await self.company_matcher.find_matching_yasaklama(
                        tsg_company,
                        processed_list
                    )

                self.report_progress(80, "Firma eslestirme tamamlandi")

                # 4. LLM ile analiz
                step("LLM ANALIZI")
                self.report_progress(85, "LLM ile analiz ediliyor...")

                analysis = await self._analyze_with_llm(
                    company_name,
                    vergi_no,
                    eslesen_yasaklama,
                    scrape_result["taranan_gun_sayisi"]
                )

                self.report_progress(95, "Analiz tamamlandi")

                # 5. Sonuc olustur
                step("SONUC HAZIRLANIYOR")

                result_data = {
                    "firma_adi": company_name,
                    "vergi_no": vergi_no,
                    "taranan_gun_sayisi": scrape_result["taranan_gun_sayisi"],
                    "bulunan_toplam_yasaklama": scrape_result["bulunan_ilan_sayisi"],
                    **analysis,
                    "sorgu_tarihi": datetime.now().isoformat(),
                    "kaynak": "Resmi Gazete - resmigazete.gov.tr"
                }

                self.report_progress(100, "Ihale kontrolu tamamlandi")

                success(f"Ihale Agent tamamlandi: yasak_durumu={analysis.get('yasak_durumu')}")

                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data=result_data,
                    summary=self._generate_summary(analysis),
                    key_findings=self._extract_key_findings(analysis),
                    warning_flags=self._extract_warnings(analysis)
                )

        except asyncio.TimeoutError:
            error("Ihale Agent TIMEOUT!")
            return self._create_timeout_result(company_name)

        except Exception as e:
            error(f"Ihale Agent HATA: {e}")
            return self._create_error_result(company_name, str(e))

    async def _analyze_with_llm(
        self,
        company_name: str,
        vergi_no: Optional[str],
        eslesen_yasaklama: Optional[Dict[str, Any]],
        taranan_gun: int
    ) -> Dict[str, Any]:
        """
        LLM ile yasaklama kararini analiz et.

        System + User prompt ayrimi ile token tasarrufu.
        temperature=0.1 ile halusnasyon engelleme.
        """
        log("LLM analizi basliyor...")

        if eslesen_yasaklama:
            # Yasaklama bulundu - detayli analiz
            yapisal = eslesen_yasaklama.get("yapisal_veri", {})
            ham_metin = eslesen_yasaklama.get("ham_metin", "")[:3000]

            user_prompt = IHALE_USER_PROMPT_TEMPLATE.format(
                company_name=company_name,
                vergi_no=vergi_no or "Bilinmiyor",
                sorgu_tarihi=datetime.now().strftime("%d.%m.%Y %H:%M"),
                yasaklama_verisi=json.dumps(yapisal, ensure_ascii=False, indent=2),
                ham_metin=ham_metin,
                gazete_tarih=eslesen_yasaklama.get("tarih", "Bilinmiyor"),
                kurum=eslesen_yasaklama.get("kurum", "Bilinmiyor")
            )
        else:
            # Yasaklama bulunamadi
            user_prompt = IHALE_USER_PROMPT_NO_BAN.format(
                company_name=company_name,
                vergi_no=vergi_no or "Bilinmiyor",
                sorgu_tarihi=datetime.now().strftime("%d.%m.%Y %H:%M"),
                taranan_gun=taranan_gun
            )

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": IHALE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-oss-120b",
                temperature=0.1,  # Dusuk - halusnasyon engelleme
                max_tokens=1500
            )

            # JSON parse
            analysis = self._parse_json_response(response)

            if analysis:
                success("LLM analizi basarili")
                return analysis

        except Exception as e:
            error(f"LLM analiz hatasi: {e}")

        # Fallback: Basit analiz
        warn("LLM basarisiz, fallback analiz kullaniliyor")
        return self._fallback_analysis(eslesen_yasaklama)

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM yanitindan JSON cikar."""
        if not response:
            return None

        try:
            # Direkt JSON dene
            return json.loads(response)
        except:
            pass

        # Code block icinde olabilir
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
        except:
            pass

        # { } arasini bul
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass

        return None

    def _fallback_analysis(self, eslesen_yasaklama: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """LLM basarisiz olursa basit analiz."""
        if eslesen_yasaklama:
            yapisal = eslesen_yasaklama.get("yapisal_veri", {})
            return {
                "yasak_durumu": True,
                "yasak_kayit_no": None,
                "ihale_kayit_no": yapisal.get("ihale_kayit_no"),
                "yasaklayan_kurum": yapisal.get("yasaklayan_kurum"),
                "ihale_idaresi": yapisal.get("ihale_idaresi"),
                "yasakli_kisi": yapisal.get("yasakli_kisi"),
                "ortaklar": yapisal.get("ortaklar", []),
                "kanun_dayanagi": yapisal.get("kanun_dayanagi"),
                "yasak_kapsami": yapisal.get("yasak_kapsami"),
                "yasak_suresi": yapisal.get("yasak_suresi"),
                "resmi_gazete": {
                    "tarih": eslesen_yasaklama.get("tarih")
                },
                "risk_degerlendirmesi": "yuksek"
            }
        else:
            return {
                "yasak_durumu": False,
                "yasak_kayit_no": None,
                "ihale_kayit_no": None,
                "yasaklayan_kurum": None,
                "ihale_idaresi": None,
                "yasakli_kisi": None,
                "ortaklar": [],
                "kanun_dayanagi": None,
                "yasak_kapsami": None,
                "yasak_suresi": None,
                "resmi_gazete": None,
                "risk_degerlendirmesi": "dusuk"
            }

    def _generate_summary(self, analysis: Dict[str, Any]) -> str:
        """Ozet metin olustur."""
        yasak = analysis.get('yasak_durumu', False)
        risk = analysis.get('risk_degerlendirmesi', 'bilinmiyor')
        kurum = analysis.get('yasaklayan_kurum', '')
        sure = analysis.get('yasak_suresi', '')

        if yasak:
            parts = ["DIKKAT: Firma ihale yasagi altinda!"]
            if kurum:
                parts.append(f"Yasaklayan: {kurum}")
            if sure:
                parts.append(f"Sure: {sure}")
            parts.append(f"Risk: {risk.upper()}")
            return " ".join(parts)
        else:
            return f"Ihale yasagi bulunmamaktadir. Risk: {risk.upper()}"

    def _extract_key_findings(self, analysis: Dict[str, Any]) -> List[str]:
        """Onemli bulgulari liste olarak dondur."""
        findings = []

        yasak = analysis.get('yasak_durumu', False)
        risk = analysis.get('risk_degerlendirmesi', 'bilinmiyor')

        if yasak:
            findings.append("AKTIF IHALE YASAGI")

            if analysis.get('yasaklayan_kurum'):
                findings.append(f"Yasaklayan: {analysis['yasaklayan_kurum']}")

            if analysis.get('yasak_suresi'):
                findings.append(f"Yasak suresi: {analysis['yasak_suresi']}")

            if analysis.get('kanun_dayanagi'):
                findings.append(f"Kanun: {analysis['kanun_dayanagi']}")
        else:
            findings.append("Ihale yasagi yok")

        findings.append(f"Risk degerlendirmesi: {risk.upper()}")

        return findings

    def _extract_warnings(self, analysis: Dict[str, Any]) -> List[str]:
        """Uyari bayraklarini dondur."""
        warnings = []

        if analysis.get('yasak_durumu'):
            warnings.append("AKTIF IHALE YASAGI")

        if analysis.get('risk_degerlendirmesi') == 'yuksek':
            warnings.append("YUKSEK RISK")

        return warnings

    def _create_error_result(self, company_name: str, error_msg: str) -> AgentResult:
        """Hata sonucu olustur."""
        return AgentResult(
            agent_id=self.agent_id,
            status="failed",
            data={
                "firma_adi": company_name,
                "hata": error_msg,
                "sorgu_tarihi": datetime.now().isoformat()
            },
            error=error_msg
        )

    def _create_timeout_result(self, company_name: str) -> AgentResult:
        """Timeout sonucu olustur."""
        return AgentResult(
            agent_id=self.agent_id,
            status="failed",
            data={
                "firma_adi": company_name,
                "hata": "Islem zaman asimina ugradi",
                "sorgu_tarihi": datetime.now().isoformat()
            },
            error="TIMEOUT: 5 dakika icinde tamamlanamadi"
        )


# Test
async def test_ihale_agent():
    """Ihale Agent test fonksiyonu."""
    print("\n" + "="*60)
    print("Ihale Agent Test")
    print("="*60)

    agent = IhaleAgent()

    # Progress callback
    def on_progress(progress):
        print(f"[{progress.percentage}%] {progress.message}")

    # Test firmasi (sadece 3 gun tara - hizli test)
    result = await agent.execute(
        company_name="TEST FIRMA A.S.",
        search_days=3,
        progress_callback=on_progress
    )

    print(f"\nDurum: {result.status}")
    print(f"Ozet: {result.summary}")
    print(f"Bulgular: {result.key_findings}")
    print(f"Uyarilar: {result.warning_flags}")


if __name__ == "__main__":
    asyncio.run(test_ihale_agent())
