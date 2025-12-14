"""
TSG Agent v9.3 - Multi-PDF + 5dk Time Limit
Ticaret Sicili Gazetesi - CAPTCHA cozme + Multi-PDF Indirme + 5 Baslik Format

v9.3 Degisiklikler:
- 5 dakika (300 saniye) time limit eklendi
- Hackathon icin sonsuz dongu riski engellendi

v9.2 Degisiklikler:
- 5/5 alan dolana kadar PDF indirme stratejisi
- YONETIM -> KURULUS -> SERMAYE sirasiyla PDF indir
- Her PDF sonrasi 5/5 kontrolu, dolu ise erken cik
- _download_until_complete(), _is_complete(), _merge_analysis() fonksiyonlari

v9.1 Degisiklikler:
- System + User prompt ayrimi (prompt engineering fix)
- TSG_SYSTEM_PROMPT sabiti
- extract_ilan_from_page() yeniden yazildi

v3.5 Degisiklikler:
- Tablo kolonlari dogru sirayla parse ediliyor (8 kolon)
- unvan: Firma adi, sicil_no, sicil_mudurlugu, ilan_tipi artik mevcut
- LLM'ye zengin veri gonderiliyor
- Herhangi bir firma icin calisabilir (defensive coding)

HACKATHON GEREKSINIMLERI:
1. Parametrik firma adi ile TSG ilanlarina ulas
2. Ilan icerigini EN AZ 5 BASLIK olarak ayir
3. Calisilan ilanin gazete sayfasini da ilet
"""
import asyncio
import json
import base64
import httpx
import time
from typing import List, Dict, Optional, Any
from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.tsg.scraper import TSGScraper
from app.agents.tsg.ocr import GazeteOCR
from app.agents.tsg.pdf_generator import TSGPDFGenerator
from app.agents.tsg.city_finder import TSGCityFinder
from app.llm.client import LLMClient
from app.agents.tsg.logger import log, step, success, error, warn, debug, Timer


# v9.1 - System Prompt (Prompt Engineering Fix)
TSG_SYSTEM_PROMPT = """Sen bir Ticaret Sicili Gazetesi (TSG) analiz uzmanisin.

GOREV:
Verilen TSG ilanindan sirket bilgilerini cikar ve JSON formatinda dondur.

ZORUNLU ALANLAR (8 Baslik):
1. Firma Unvani: Sirketin tam resmi adi
2. Tescil Konusu: Islem turu (kurulus, sermaye artirimi, yonetici degisikligi vb.)
3. Mersis Numarasi: 16 haneli numara (varsa)
4. Yoneticiler: Yonetim kurulu uyeleri / mudur isimleri (liste)
5. Imza Yetkilisi: Sirketi temsile yetkili kisi(ler)
6. Sermaye: Sirket sermayesi (ornegin: "10.000.000 TL")
7. Kurulus_Tarihi: Sirketin kurulus tarihi (ornegin: "15.03.2018")
8. Faaliyet_Konusu: Sirketin faaliyet alani (kisa ozet)

KURALLAR:
- SADECE metinde ACIKCA yazan bilgileri cikar
- Tahmin yapma, varsayimda bulunma!
- Bulunamayan alanlar icin null dondur
- Turkce karakterleri dogru kullan

CIKTI FORMATI:
Sadece JSON dondur, aciklama yapma!

{
    "Firma Unvani": "string veya null",
    "Tescil Konusu": "string veya null",
    "Mersis Numarasi": "string veya null",
    "Yoneticiler": ["isim1", "isim2"] veya null,
    "Imza Yetkilisi": "string veya null",
    "Sermaye": "string veya null",
    "Kurulus_Tarihi": "string veya null",
    "Faaliyet_Konusu": "string veya null"
}"""

# v9.1 - MULTI_ILAN_PROMPT kaldirildi, TSG_SYSTEM_PROMPT kullaniliyor


class TSGAgent(BaseAgent):
    """
    TSG Agent v9.5 - Demo/Full Mode Destekli

    Yetenekler:
    1. Tesseract OCR ile CAPTCHA cozme
    2. Otomatik TSG login
    3. Akilli ilan secimi (kurulus/tescil oncelikli)
    4. Gazete sayfasi screenshot
    5. Tesseract OCR ile gazete okuma
    6. LLM ile 8 baslik formatinda veri cikarma
    7. Demo/Full mode time limits
    8. PDF Generator ile profesyonel gazete sayfasi olusturma

    HACKATHON OUTPUT:
    - Firma Unvani (tablodaki unvan kolonundan)
    - Tescil Konusu (tablodaki ilan_tipi kolonundan)
    - Mersis Numarasi (LLM ile zenginlestirme)
    - Yoneticiler (LLM ile zenginlestirme)
    - Imza Yetkilisi (LLM ile zenginlestirme)
    - Sicil No, Sicil Mudurlugu (tablodaki yeni kolonlar)
    - + Profesyonel Gazete PDF sayfasi
    """

    DEBUG_DIR = "/tmp/tsg_debug"

    # PDF Servisi URL (Docker network veya localhost)
    PDF_SERVICE_URL = "http://localhost:8001"  # Local test
    # PDF_SERVICE_URL = "http://pdf-downloader:8001"  # Docker network

    # ============================================
    # FULL MODE: Sınırsız süre, MAX araştırma
    # ============================================
    DEFAULT_MAX_TIME_SECONDS = 900  # 15 dakika (kapsamlı tarama)

    # ============================================
    # DEMO MODE: 90 saniye (orchestrator 90s verir)
    # ============================================
    DEMO_MAX_TIME_SECONDS = 90  # 1.5 dakika - orchestrator tarafından kontrol edilir

    def __init__(self, demo_mode: bool = False):
        super().__init__(
            agent_id="tsg_agent",
            agent_name="TSG Agent",
            agent_description="Ticaret Sicili Gazetesi - Demo/Full Mode Destekli"
        )
        self.llm = LLMClient()
        self.pdf_generator = TSGPDFGenerator(self.DEBUG_DIR)
        self.city_finder = TSGCityFinder()
        self.demo_mode = demo_mode

        # Demo/Full mode time limits
        if demo_mode:
            self.max_time_seconds = self.DEMO_MAX_TIME_SECONDS
            log(f"TSGAgent: DEMO MODE - Max {self.max_time_seconds}s")
        else:
            self.max_time_seconds = self.DEFAULT_MAX_TIME_SECONDS
            log(f"TSGAgent: FULL MODE - Max {self.max_time_seconds}s")

    async def run(self, company_name: str) -> AgentResult:
        """
        Ana calistirma metodu - Hackathon uyumlu.

        Args:
            company_name: Aranacak firma adi

        Returns:
            AgentResult: Hackathon formatinda sonuc
        """
        step(f"TSG AGENT v6.0 BASLIYOR: {company_name}")
        self.report_progress(5, "TSG Agent baslatiliyor...")

        try:
            with Timer("TSG Agent toplam sure"):
                # v6.0: Önce şehri bul (WebSearch ile)
                step("SEHIR BULMA (v6.0)")
                self.report_progress(8, "Firma merkezi sehri araniyor...")

                company_city = await self.city_finder.find_city(company_name)
                log(f"Firma merkezi sehri: {company_city}")
                self.report_progress(12, f"Sehir: {company_city}")

                async with TSGScraper() as scraper:
                    # 1. Login
                    log("Login asamasina geciliyor...")
                    self.report_progress(15, "TSG'ye giris yapiliyor...")

                    login_success = await scraper.login(max_retries=3)

                    if not login_success:
                        error("Login basarisiz!")
                        return self._create_error_result(
                            company_name,
                            "TSG giris yapilamadi - CAPTCHA cozulemedi"
                        )

                    success("Login basarili!")
                    self.report_progress(25, "Giris basarili! Firma araniyor...")

                    # 2. Firma ara (şehir parametresi ile) - HOTFIX: Multi-city retry
                    log(f"Firma araniyor: {company_name} (sehir: {company_city})")
                    search_results = await scraper.search_company(company_name, city=company_city)

                    # HOTFIX: İlk şehirde bulunamazsa diğer şehirleri dene
                    if not search_results:
                        fallback_cities = ["İSTANBUL", "ANKARA", "İZMİR", "BURSA", "ANTALYA", "KOCAELİ", "GAZİANTEP", "KONYA"]
                        # Zaten denenen şehri çıkar
                        fallback_cities = [c for c in fallback_cities if c.upper() != (company_city or "").upper()]

                        for fallback_city in fallback_cities[:4]:  # Max 4 şehir dene (hız için)
                            log(f"Fallback arama: {fallback_city}")
                            self.report_progress(30, f"Araniyor: {fallback_city}...")
                            search_results = await scraper.search_company(company_name, city=fallback_city)
                            if search_results:
                                log(f"Firma {fallback_city}'de bulundu!")
                                break

                    if not search_results:
                        warn("TSG'de kayit bulunamadi (tum sehirler denendi)")
                        return self._create_not_found_result(company_name)

                    success(f"{len(search_results)} ilan bulundu!")
                    self.report_progress(40, f"{len(search_results)} ilan bulundu!")

                    # 3. v4.0: MULTI-ILAN GRUPLAMA
                    step("MULTI-ILAN GRUPLAMA (v4.0)")
                    grouped_ilanlar = TSGScraper.group_ilanlar_by_type(search_results)
                    priority_ilanlar = TSGScraper.select_priority_ilanlar(grouped_ilanlar)

                    log(f"Gruplar: KURULUS={len(grouped_ilanlar.get('KURULUS', []))}, "
                        f"YONETIM={len(grouped_ilanlar.get('YONETIM', []))}, "
                        f"SERMAYE={len(grouped_ilanlar.get('SERMAYE', []))}")
                    self.report_progress(45, "Ilanlar gruplandir!")

                    # v9.2: En iyi ilani belirle (gazete_info icin)
                    best_ilan = (
                        priority_ilanlar.get("YONETIM") or
                        priority_ilanlar.get("KURULUS") or
                        priority_ilanlar.get("SERMAYE") or
                        search_results[0]
                    )
                    log(f"Referans ilan: tip={best_ilan.get('ilan_tipi', 'N/A')}")
                    self.report_progress(50, "PDF indirme basliyor...")

                    # 4. v9.2: MULTI-PDF INDIRME (5/5 Dolana Kadar)
                    step("MULTI-PDF INDIRME (v9.2)")

                    gazete_info = {
                        "gazete_no": best_ilan.get("gazete_no", ""),
                        "tarih": best_ilan.get("tarih", ""),
                        "ilan_tipi": best_ilan.get("ilan_tipi", ""),
                        "screenshot_path": None,
                        "pdf_path": None,
                    }

                    # v9.2: 5/5 alan dolana kadar PDF indir ve analiz et
                    yapilandirilmis_veri = await self._download_until_complete(
                        scraper, priority_ilanlar, search_results, company_name
                    )

                    # Sonucu kontrol et
                    if self._is_complete(yapilandirilmis_veri):
                        success("5/5 alan DOLU!")
                    else:
                        # Fallback: Tablo verilerinden zenginlestir
                        warn("Multi-PDF ile 5/5 dolmadi, tablo verilerinden takviye...")
                        if not yapilandirilmis_veri.get("Firma Unvani"):
                            yapilandirilmis_veri["Firma Unvani"] = best_ilan.get("unvan", company_name)

                    self.report_progress(85, "Analiz tamamlandi!")

                    self.report_progress(90, "PDF olusturuluyor...")

                    # 7. PROFESYONEL PDF OLUSTUR
                    step("PDF GENERATOR CALISIYOR")
                    pdf_screenshot_path = None
                    pdf_path = None

                    try:
                        # PDF icin veri hazirla
                        pdf_data = {
                            **yapilandirilmis_veri,
                            "gazete_no": gazete_info.get("gazete_no", best_ilan.get("gazete_no", "")),
                            "tarih": gazete_info.get("tarih", best_ilan.get("tarih", "")),
                        }

                        # PDF olustur
                        pdf_path = self.pdf_generator.generate(
                            data=pdf_data,
                            output_path=f"{self.DEBUG_DIR}/tsg_rapor.pdf"
                        )
                        log(f"PDF olusturuldu: {pdf_path}")

                        # PNG'ye cevir (screenshot olarak)
                        try:
                            pdf_screenshot_path = self.pdf_generator.to_image(pdf_path)
                            success(f"PDF screenshot: {pdf_screenshot_path}")
                        except Exception as png_err:
                            warn(f"PNG donusumu basarisiz: {png_err}")
                            # PDF var ama PNG yok - sorun degil

                    except Exception as pdf_err:
                        error(f"PDF olusturma hatasi: {pdf_err}")
                        # PDF olusturulamadi - scraper screenshot'i kullan

                    # Screenshot path: PDF PNG > Scraper screenshot > None
                    final_screenshot = (
                        pdf_screenshot_path or
                        gazete_info.get("screenshot_path") or
                        None
                    )

                    # Gazete info'yu guncelle
                    gazete_info["screenshot_path"] = final_screenshot
                    gazete_info["pdf_path"] = pdf_path

                    self.report_progress(95, "Sonuclar hazirlaniyor...")

                    # 8. HACKATHON UYUMLU OUTPUT OLUSTUR
                    # v9.2: ilan_index artik multi-PDF icin kullanilmiyor
                    best_ilan_index = self._find_ilan_index(best_ilan, search_results)
                    final_data = self._create_hackathon_output(
                        company_name=company_name,
                        search_results=search_results,
                        selected_ilan=best_ilan,
                        ilan_index=best_ilan_index if best_ilan_index >= 0 else 0,
                        gazete_info=gazete_info,
                        yapilandirilmis_veri=yapilandirilmis_veri
                    )

                    self.report_progress(100, "TSG analizi tamamlandi!")
                    step("TSG AGENT TAMAMLANDI")

                    return AgentResult(
                        agent_id=self.agent_id,
                        status="completed",
                        data=final_data,
                        summary=self._generate_hackathon_summary(final_data),
                        key_findings=self._extract_hackathon_findings(yapilandirilmis_veri),
                        warning_flags=[]
                    )

        except Exception as e:
            import traceback
            traceback.print_exc()
            error(f"TSG Agent hatasi: {e}")
            return self._create_error_result(company_name, str(e))

    async def _analyze_hackathon_format(self, ilan_metni: str, company_name: str) -> Dict:
        """
        LLM ile Hackathon formatinda (5 baslik) analiz.

        v9.1: System + User prompt ayrimi (prompt engineering fix)

        Args:
            ilan_metni: OCR veya liste verisi
            company_name: Firma adi

        Returns:
            Dict: 5 baslik formatinda veri
        """
        log("Hackathon format LLM analizi basladi (v9.1)")

        if not ilan_metni:
            warn("Analiz icin metin yok")
            return self._empty_hackathon_format()

        # v9.1: System prompt + User prompt ayrimi
        # System: Uzman persona + kurallar + JSON formati
        # User: SADECE OCR metni
        messages = [
            {"role": "system", "content": TSG_SYSTEM_PROMPT},
            {"role": "user", "content": f"Bu TSG ilanini analiz et:\n\n{ilan_metni[:6000]}"}
        ]

        try:
            response = await self._llm_with_retry(
                messages=messages,
                model="gpt-oss-120b",
                temperature=0.1,
                max_tokens=1024
            )

            # JSON temizle ve parse et
            response_clean = self._clean_json_response(response)
            data = json.loads(response_clean)

            # Zorunlu alanlari kontrol et (v9.3 - 8 alan)
            required_fields = [
                "Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Yoneticiler", "Imza Yetkilisi",
                "Sermaye", "Kurulus_Tarihi", "Faaliyet_Konusu"
            ]
            for field in required_fields:
                if field not in data:
                    data[field] = None

            success("Hackathon format analizi tamamlandi")
            return data

        except json.JSONDecodeError as e:
            error(f"JSON parse hatasi: {e}")
            return self._empty_hackathon_format()

        except Exception as e:
            error(f"LLM hatasi: {e}")
            return self._empty_hackathon_format()

    def _empty_hackathon_format(self) -> Dict:
        """Bos hackathon formati dondur."""
        return {
            "Firma Unvani": None,
            "Tescil Konusu": None,
            "Mersis Numarasi": None,
            "Yoneticiler": [],
            "Imza Yetkilisi": None,
            # v9.3 - Council icin ek alanlar
            "Sermaye": None,
            "Kurulus_Tarihi": None,
            "Faaliyet_Konusu": None,
        }

    # =====================================================
    # v9.2 - Multi-PDF Helper Functions (5/5 Garanti)
    # =====================================================

    def _is_complete(self, data: Dict) -> bool:
        """
        v9.4: ESNEK KONTROL - 3/5 alan dolu mu kontrol et.

        BUG FIX: 5/5 zorunlu çok katıydı:
        - Mersis neredeyse hiç bulunmuyor
        - Yöneticiler çoğu zaman listelenemez

        Yeni kural:
        - Firma Unvani ZORUNLU
        - Tescil Konusu veya Imza Yetkilisi'nden en az 1'i
        - Toplamda 3+ alan dolu

        Returns:
            bool: Yeterli veri var mı
        """
        # Kritik alan: Firma Unvani mutlaka olmalı
        if not data.get("Firma Unvani"):
            return False

        # Tüm alanları say
        all_fields = ["Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Yoneticiler", "Imza Yetkilisi"]
        filled_count = 0

        for field in all_fields:
            value = data.get(field)
            if field == "Yoneticiler":
                if value and len(value) > 0:
                    filled_count += 1
            elif value and value != "":
                filled_count += 1

        # 3/5 alan dolu ise yeterli
        if filled_count >= 3:
            debug(f"_is_complete: {filled_count}/5 alan dolu - YETERLI")
            return True

        return False

    def _find_ilan_index(self, target_ilan: Dict, search_results: List[Dict]) -> int:
        """
        Target ilan'in search_results icerisindeki index'ini bul.

        Eslestirme: gazete_no + tarih

        Args:
            target_ilan: Aranan ilan
            search_results: Tum ilan listesi

        Returns:
            int: Index (bulunamazsa -1)
        """
        target_gazete = target_ilan.get("gazete_no", "")
        target_tarih = target_ilan.get("tarih", "")

        for i, ilan in enumerate(search_results):
            if (ilan.get("gazete_no") == target_gazete and
                ilan.get("tarih") == target_tarih):
                return i

        warn(f"Ilan index bulunamadi: gazete={target_gazete}, tarih={target_tarih}")
        return -1

    def _merge_analysis(self, existing: Dict, new: Dict) -> Dict:
        """
        Iki analiz sonucunu birlestir.

        Strateji: null olmayanlar korunur, yeni degerler eksikleri doldurur.

        Args:
            existing: Mevcut sonuc
            new: Yeni analiz sonucu

        Returns:
            Dict: Birlestirilmis sonuc
        """
        result = existing.copy()

        # Basit alanlar: null degilse koru, bossa yenisini al
        for field in ["Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Imza Yetkilisi"]:
            if not result.get(field) and new.get(field):
                result[field] = new[field]
                debug(f"Merge: {field} eklendi")

        # Yoneticiler: Liste birlestirme (null degilse koru)
        existing_yon = result.get("Yoneticiler") or []
        new_yon = new.get("Yoneticiler") or []

        if not existing_yon and new_yon:
            result["Yoneticiler"] = new_yon
            debug(f"Merge: Yoneticiler eklendi ({len(new_yon)} kisi)")

        return result

    async def _download_until_complete(
        self,
        scraper: 'TSGScraper',
        priority_ilanlar: Dict[str, Dict],
        search_results: List[Dict],
        company_name: str
    ) -> Dict:
        """
        5/5 alan dolana kadar PDF indir ve analiz et.

        v9.2 Ana Fonksiyon - Akilli Multi-PDF

        Sira: YONETIM -> KURULUS -> SERMAYE
        Her adimda 5/5 kontrolu, dolu ise erken cik!

        Args:
            scraper: Aktif TSGScraper instance
            priority_ilanlar: Her gruptan secilen ilanlar
            search_results: Tum ilanlar (index icin)
            company_name: Firma adi

        Returns:
            Dict: 5 baslik formatinda sonuc (mumkun olan en dolu)
        """
        step("MULTI-PDF INDIRME (v9.5 - Demo/Full Mode Time Limit)")

        # v9.5: Demo/Full mode time limit
        start_time = time.time()
        MAX_TIME_SECONDS = self.max_time_seconds  # Demo: 480s, Full: 900s

        merged_result = self._empty_hackathon_format()
        # v9.4: Genişletilmiş ilan tipleri - daha fazla veri için
        priority_order = [
            "YONETIM",      # Güncel yöneticiler
            "KURULUS",      # Kuruluş bilgileri, MERSIS
            "SERMAYE",      # Sermaye artışları
            "GENEL_KURUL",  # Genel kurul kararları
            "TESCIL",       # Tescil işlemleri
            "DIGER"         # Diğer önemli ilanlar
        ]
        downloaded_count = 0

        for ilan_type in priority_order:
            # v9.4: Time limit kontrolu
            elapsed = time.time() - start_time
            if elapsed > MAX_TIME_SECONDS:
                warn(f"8 dakika limiti asildi! ({int(elapsed)}s)")
                break
            ilan = priority_ilanlar.get(ilan_type)
            if not ilan:
                debug(f"{ilan_type} grubu bos, atlaniyor")
                continue

            # Ilan index'ini bul
            ilan_index = self._find_ilan_index(ilan, search_results)
            if ilan_index < 0:
                warn(f"{ilan_type} ilan index bulunamadi")
                continue

            log(f"{ilan_type} PDF indiriliyor (index: {ilan_index})...")
            self.report_progress(55 + downloaded_count * 10, f"{ilan_type} PDF indiriliyor...")

            # PDF indir
            pdf_bytes = await scraper.click_and_download_pdf(ilan_index)
            if not pdf_bytes:
                warn(f"{ilan_type} PDF indirilemedi")
                continue

            downloaded_count += 1
            log(f"{ilan_type} PDF indirildi: {len(pdf_bytes)} bytes")

            # OCR ile metin cikar
            ocr_text = self._extract_text_from_pdf(pdf_bytes)
            if not ocr_text or len(ocr_text) < 100:
                warn(f"{ilan_type} OCR yetersiz metin ({len(ocr_text) if ocr_text else 0} karakter)")
                # Boş OCR'ı da sonuca ekle (en azından PDF indirildi)
                merged_result["ocr_failures"] = merged_result.get("ocr_failures", 0) + 1
                continue

            # Firma ile ilgili bolumu filtrele
            ocr_text = GazeteOCR.extract_ilan_from_page(ocr_text, company_name)
            log(f"{ilan_type} OCR: {len(ocr_text)} karakter")

            # LLM Analizi
            self.report_progress(60 + downloaded_count * 10, f"{ilan_type} analiz ediliyor...")
            analysis = await self._analyze_hackathon_format(ocr_text, company_name)

            # Merge
            merged_result = self._merge_analysis(merged_result, analysis)

            # 5/5 dolu mu kontrol et
            if self._is_complete(merged_result):
                success(f"5/5 TAMAMLANDI! ({ilan_type} PDF ile, {downloaded_count} PDF indirildi)")
                break
            else:
                # Eksik alanlari logla
                missing = []
                for field in ["Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Yoneticiler", "Imza Yetkilisi"]:
                    val = merged_result.get(field)
                    if not val or (field == "Yoneticiler" and len(val) == 0):
                        missing.append(field)
                log(f"{ilan_type} sonrasi eksik alanlar: {missing}")

        # Sonuc
        filled_count = sum(1 for f in ["Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Imza Yetkilisi"]
                          if merged_result.get(f))
        if merged_result.get("Yoneticiler"):
            filled_count += 1

        # v9.3: Toplam sure
        total_time = int(time.time() - start_time)
        log(f"Multi-PDF sonucu: {filled_count}/5 alan dolu, {downloaded_count} PDF indirildi, {total_time}s")
        return merged_result

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        PDF bytes'dan metin cikar.

        v9.0 Strateji:
        1. pdfplumber/PyPDF2 dene (text-based PDF)
        2. Basarisizsa -> GazeteOCR ile OCR (scanned PDF)

        Args:
            pdf_bytes: PDF dosya icerigi

        Returns:
            str: Cikarilan metin
        """
        import tempfile

        if not pdf_bytes or len(pdf_bytes) < 100:
            warn("PDF bytes bos veya cok kisa")
            return ""

        # Temp dosyaya kaydet
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            pdf_path = f.name

        log(f"PDF temp dosyaya kaydedildi: {pdf_path} ({len(pdf_bytes)} bytes)")

        text = ""

        # 1. pdfplumber dene (text-based PDF icin)
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

            if len(text.strip()) > 200:  # Yeterli metin varsa
                success(f"pdfplumber basarili: {len(text)} karakter")
                return text.strip()
            else:
                log("pdfplumber yetersiz metin cikardi, OCR deneniyor...")

        except ImportError:
            warn("pdfplumber yuklu degil")
        except Exception as e:
            warn(f"pdfplumber hatasi: {e}")

        # 2. OCR ile dene (scanned PDF icin - v9.0)
        step("PDF OCR BASLIYOR (Tesseract)")
        try:
            ocr_text = GazeteOCR.read_pdf_file(pdf_path)

            if ocr_text and len(ocr_text) > 100:
                success(f"OCR basarili: {len(ocr_text)} karakter")
                return ocr_text
            else:
                warn("OCR yetersiz metin cikardi")

        except Exception as e:
            error(f"OCR hatasi: {e}")

        # 3. Bos dondu
        warn("PDF'den metin cikarilmadi (pdfplumber + OCR basarisiz)")
        return ""

    # =====================================================
    # v8.0 - LLM ile Yapilandirilmis Veri Cikarimi
    # =====================================================

    async def _parse_gazete_with_llm(self, raw_text: str, ilan_type: str) -> Dict[str, Any]:
        """
        Gazete metninden yapilandirilmis veri cikar.

        LLM'e ham metin verilir, yapilandirilmis JSON doner.
        SIFIR halucinasyon - sadece metinde olan bilgiler!

        Args:
            raw_text: PDF'den cikarilan ham metin
            ilan_type: Ilan tipi (KURULUS, YONETIM, SERMAYE, vb.)

        Returns:
            Dict: Yapilandirilmis firma bilgileri
        """
        step(f"LLM PARSE: {ilan_type}")

        if not raw_text or len(raw_text) < 50:
            warn("Ham metin cok kisa, parse atlanıyor")
            return {}

        # Metin cok uzunsa kes (token limiti)
        max_chars = 8000
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + "\n... [METIN KESILDI]"

        prompt = f"""Sen bir Ticaret Sicili Gazetesi analiz uzmanisin.

Asagidaki gazete metnini analiz et ve yapilandirilmis bilgi cikar.

KURALLAR:
1. SADECE metinde acikca yazili bilgileri cikar
2. Tahmin yapma, varsayimda bulunma
3. Bulunamayan alanlar icin null dondur
4. Tarih formati: DD.MM.YYYY
5. Para formati: 1.234.567,89 TL

ILAN TIPI: {ilan_type}

HAM METIN:
{raw_text}

JSON FORMATI:
{{
  "firma_unvani": "string veya null",
  "mersis_no": "string veya null - 16 haneli numara",
  "sicil_no": "string veya null",
  "ticaret_sicil_mudurlugu": "string veya null",
  "tescil_tarihi": "string veya null",
  "ilan_tarihi": "string veya null",
  "sermaye": "string veya null",
  "adres": "string veya null",
  "yoneticiler": [
    {{
      "ad_soyad": "string",
      "gorev": "string (Yonetim Kurulu Baskani, Uye, Murahhas Aza, vb.)",
      "tc_kimlik": "string veya null"
    }}
  ],
  "imza_yetkilileri": [
    {{
      "ad_soyad": "string",
      "yetki_turu": "munferit/musterek/sinirli",
      "yetki_siniri": "string veya null"
    }}
  ],
  "faaliyet_konusu": "string veya null - max 200 karakter",
  "tescil_konusu_ozet": "string - max 100 karakter"
}}

SADECE JSON dondur, baska aciklama yapma!"""

        try:
            from app.llm.client import LLMClient

            client = LLMClient()
            response = await client.chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-oss-120b"
            )

            # JSON parse
            import re

            # JSON blogunu bul
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                success(f"LLM parse tamamlandi: {len(data)} alan")
                return data

            warn("JSON bulunamadi")
            return {}

        except json.JSONDecodeError as e:
            error(f"JSON parse hatasi: {e}")
            return {}
        except Exception as e:
            error(f"LLM parse hatasi: {e}")
            return {}

    # =====================================================
    # v4.0 - Multi-Ilan Birlestirme Fonksiyonlari
    # =====================================================

    def _prepare_multi_ilan_context(
        self,
        priority_ilanlar: Dict[str, Dict],
        all_results: List[Dict],
        company_name: str
    ) -> str:
        """
        Birden fazla ilan tipi icin LLM context hazirla.

        Her ilan tipinden alinacak veriler:
        - KURULUS: MERSIS No, kurucu ortaklar, ilk YK
        - YONETIM: Guncel yoneticiler, imza yetkilileri
        - SERMAYE: Ortaklar, pay dagitimi

        Args:
            priority_ilanlar: {"KURULUS": ilan, "YONETIM": ilan, ...}
            all_results: Tum ilan sonuclari
            company_name: Firma adi

        Returns:
            str: LLM icin formatlanmis metin
        """
        step("MULTI-ILAN CONTEXT HAZIRLAMA (v4.0)")

        lines = [
            f"FIRMA: {company_name}",
            f"KAYNAK: Turkiye Ticaret Sicili Gazetesi",
            f"TOPLAM ILAN: {len(all_results)}",
            "",
            "=" * 50,
            "ILAN TIPI BAZLI VERILER:",
            "=" * 50,
        ]

        TYPE_INSTRUCTIONS = {
            "KURULUS": "MERSIS no, kurucu ortaklar, ilk yonetim kurulu",
            "YONETIM": "Guncel yoneticiler, imza yetkilileri",
            "SERMAYE": "Ortaklar, pay oranlari",
        }

        for group_name, instruction in TYPE_INSTRUCTIONS.items():
            ilan = priority_ilanlar.get(group_name)
            if ilan:
                lines.extend([
                    "",
                    f"--- {group_name} ILANI ---",
                    f"Aradigimiz Bilgiler: {instruction}",
                    f"Unvan: {ilan.get('unvan', 'N/A')}",
                    f"Ilan Tipi: {ilan.get('ilan_tipi', 'N/A')}",
                    f"Tarih: {ilan.get('tarih', 'N/A')}",
                    f"Gazete No: {ilan.get('gazete_no', 'N/A')}",
                    f"Sicil No: {ilan.get('sicil_no', 'N/A')}",
                    f"Sicil Mudurlugu: {ilan.get('sicil_mudurlugu', 'N/A')}",
                ])

        # Ek: Tum ilanlarin ozeti (referans icin)
        lines.extend([
            "",
            "=" * 50,
            "TUM ILANLAR OZETI (Referans):",
            "=" * 50,
        ])

        for i, ilan in enumerate(all_results[:15], 1):
            lines.append(
                f"{i}. {ilan.get('ilan_tipi', 'N/A')[:30]} | "
                f"{ilan.get('tarih', 'N/A')} | "
                f"Gazete: {ilan.get('gazete_no', 'N/A')}"
            )

        result = "\n".join(lines)
        debug(f"Multi-ilan context: {len(result)} karakter")
        return result

    async def _analyze_multi_ilan_format(
        self,
        multi_ilan_context: str,
        company_name: str
    ) -> Dict:
        """
        Multi-ilan context ile LLM analizi.

        v9.1: System + User prompt ayrimi (prompt engineering fix)

        Farkli ilan tiplerinden gelen verileri birlestir.

        Args:
            multi_ilan_context: Hazirlanmis context
            company_name: Firma adi

        Returns:
            Dict: 5 baslik formatinda veri
        """
        step("MULTI-ILAN LLM ANALIZI (v9.1)")

        if not multi_ilan_context:
            warn("Analiz icin context yok")
            return self._empty_hackathon_format()

        # v9.1: System prompt + User prompt ayrimi
        messages = [
            {"role": "system", "content": TSG_SYSTEM_PROMPT},
            {"role": "user", "content": f"Bu TSG ilanlarini analiz et:\n\n{multi_ilan_context[:8000]}"}
        ]

        try:
            response = await self._llm_with_retry(
                messages=messages,
                model="gpt-oss-120b",
                temperature=0.1,
                max_tokens=1024
            )

            # JSON temizle ve parse et
            response_clean = self._clean_json_response(response)
            data = json.loads(response_clean)

            # Zorunlu alanlari kontrol et
            required_fields = ["Firma Unvani", "Tescil Konusu", "Mersis Numarasi", "Yoneticiler", "Imza Yetkilisi"]
            for field in required_fields:
                if field not in data:
                    data[field] = None

            # Fallback: Firma unvani yoksa company_name kullan
            if not data.get("Firma Unvani"):
                data["Firma Unvani"] = company_name

            success("Multi-ilan LLM analizi tamamlandi")
            return data

        except json.JSONDecodeError as e:
            error(f"JSON parse hatasi: {e}")
            return self._empty_hackathon_format()

        except Exception as e:
            error(f"LLM hatasi: {e}")
            return self._empty_hackathon_format()

    def _format_ilan_for_llm(self, best_ilan: Dict, all_results: List[Dict], company_name: str) -> str:
        """
        Liste verilerini LLM icin formatla.
        PDF 404 hatasi aldiginda bu metod kullanilir.

        v3.5: Yeni kolon isimleri kullaniliyor:
        - unvan: Firma adi
        - sicil_no: Ticaret sicil numarasi
        - sicil_mudurlugu: Kayitli oldugu il
        - ilan_tipi: Tescil konusu

        Args:
            best_ilan: Secilen ilan
            all_results: Tum ilan sonuclari
            company_name: Firma adi

        Returns:
            str: LLM icin formatlanmis metin
        """
        # Yeni kolon isimleri ile zengin veri
        unvan = best_ilan.get('unvan', company_name)
        sicil_no = best_ilan.get('sicil_no', 'N/A')
        sicil_mudurlugu = best_ilan.get('sicil_mudurlugu', 'N/A')
        ilan_tipi = best_ilan.get('ilan_tipi', 'N/A')
        tarih = best_ilan.get('tarih', 'N/A')
        gazete_no = best_ilan.get('gazete_no', 'N/A')
        sayfa = best_ilan.get('sayfa', 'N/A')

        lines = [
            f"FIRMA: {unvan}",
            f"KAYNAK: Turkiye Ticaret Sicili Gazetesi",
            f"TOPLAM ILAN: {len(all_results)}",
            "",
            "SECILEN ILAN - TABLO VERILERI:",
            f"  Firma Unvani: {unvan}",
            f"  Sicil No: {sicil_no}",
            f"  Sicil Mudurlugu: {sicil_mudurlugu}",
            f"  Ilan Turu/Tescil Konusu: {ilan_tipi}",
            f"  Yayin Tarihi: {tarih}",
            f"  Gazete No: {gazete_no}",
            f"  Sayfa: {sayfa}",
        ]

        lines.append("")
        lines.append("DIGER ILANLAR (ayni firma):")

        for i, ilan in enumerate(all_results[:5], 1):
            i_unvan = ilan.get('unvan', 'N/A')
            i_ilan_tipi = ilan.get('ilan_tipi', 'N/A')
            i_tarih = ilan.get('tarih', 'N/A')
            i_gazete_no = ilan.get('gazete_no', 'N/A')
            lines.append(f"  {i}. {i_unvan[:40]} | {i_ilan_tipi} | {i_tarih} | Gazete: {i_gazete_no}")

        return "\n".join(lines)

    def _create_hackathon_output(
        self,
        company_name: str,
        search_results: List[Dict],
        selected_ilan: Dict,
        ilan_index: int,
        gazete_info: Dict,
        yapilandirilmis_veri: Dict
    ) -> Dict:
        """
        Hackathon uyumlu final output olustur.

        Hackathon gereksinimleri:
        1. Yapilandirilmis veri (8 baslik - v9.3)
        2. Gazete sayfasi screenshot path
        3. Meta bilgiler
        4. Sicil bilgisi (tablo verisinden)
        """
        return {
            "firma_adi": company_name,
            "tsg_sonuc": {
                "toplam_ilan": len(search_results),
                "secilen_ilan_index": ilan_index,
                "gazete_bilgisi": {
                    "gazete_no": gazete_info.get("gazete_no", ""),
                    "tarih": gazete_info.get("tarih", ""),
                    "ilan_tipi": gazete_info.get("ilan_tipi", ""),
                    "sayfa_no": gazete_info.get("sayfa_no", ""),
                    "screenshot_path": gazete_info.get("screenshot_path"),
                    "pdf_path": gazete_info.get("pdf_path"),
                    "detay_url": gazete_info.get("detay_url", ""),
                },
                "yapilandirilmis_veri": yapilandirilmis_veri,
                # v9.3 - Council icin sicil bilgisi (tablo verisinden)
                "sicil_bilgisi": {
                    "sicil_no": selected_ilan.get("sicil_no"),
                    "sicil_mudurlugu": selected_ilan.get("sicil_mudurlugu"),
                },
            },
            "veri_kaynagi": "TSG",
            "status": "completed"
        }

    def _generate_hackathon_summary(self, data: Dict) -> str:
        """Hackathon ozeti olustur."""
        veri = data.get("tsg_sonuc", {}).get("yapilandirilmis_veri", {})

        parts = []

        # Firma unvani
        unvan = veri.get("Firma Unvani")
        if unvan:
            parts.append(f"Unvan: {unvan}")
        else:
            parts.append(f"Firma: {data.get('firma_adi', 'N/A')}")

        # Tescil konusu
        konu = veri.get("Tescil Konusu")
        if konu:
            parts.append(f"Islem: {konu}")

        # Ilan sayisi
        toplam = data.get("tsg_sonuc", {}).get("toplam_ilan", 0)
        parts.append(f"{toplam} TSG ilani")

        # Screenshot
        screenshot = data.get("tsg_sonuc", {}).get("gazete_bilgisi", {}).get("screenshot_path")
        if screenshot:
            parts.append("Gazete sayfasi mevcut")

        return " | ".join(parts)

    def _extract_hackathon_findings(self, veri: Dict) -> List[str]:
        """Hackathon bulgularini cikar."""
        findings = []

        if veri.get("Firma Unvani"):
            findings.append(f"Firma: {veri['Firma Unvani']}")

        if veri.get("Tescil Konusu"):
            findings.append(f"Tescil Konusu: {veri['Tescil Konusu']}")

        if veri.get("Mersis Numarasi"):
            findings.append(f"Mersis: {veri['Mersis Numarasi']}")

        yoneticiler = veri.get("Yoneticiler", [])
        if yoneticiler:
            if isinstance(yoneticiler, list):
                findings.append(f"Yoneticiler: {', '.join(yoneticiler[:3])}")
            else:
                findings.append(f"Yoneticiler: {yoneticiler}")

        if veri.get("Imza Yetkilisi"):
            findings.append(f"Imza Yetkilisi: {veri['Imza Yetkilisi']}")

        return findings

    def _create_error_result(self, company_name: str, error_msg: str) -> AgentResult:
        """Hata sonucu olustur."""
        self.report_progress(100, f"Hata: {error_msg}")
        return AgentResult(
            agent_id=self.agent_id,
            status="failed",
            data={"firma_adi": company_name, "error": error_msg},
            error=error_msg,
            summary=f"TSG hatasi: {error_msg}",
            key_findings=[],
            warning_flags=[error_msg]
        )

    def _create_not_found_result(self, company_name: str) -> AgentResult:
        """Kayit bulunamadi sonucu olustur."""
        self.report_progress(100, "TSG'de kayit bulunamadi")
        return AgentResult(
            agent_id=self.agent_id,
            status="completed",
            data={
                "firma_adi": company_name,
                "tsg_sonuc": {
                    "toplam_ilan": 0,
                    "yapilandirilmis_veri": self._empty_hackathon_format(),
                },
                "veri_kaynagi": "TSG",
                "status": "not_found"
            },
            summary=f"{company_name} icin TSG kaydi bulunamadi",
            key_findings=[],
            warning_flags=["TSG kaydi bulunamadi"]
        )

    async def _llm_with_retry(self, messages: List[Dict], max_retries: int = 3, **kwargs) -> str:
        """Rate limit aware LLM call with retry."""
        for attempt in range(max_retries):
            try:
                debug(f"LLM deneme {attempt + 1}/{max_retries}")
                return await self.llm.chat(messages, **kwargs)

            except Exception as e:
                error_str = str(e).lower()

                if "rate" in error_str or "limit" in error_str or "429" in error_str:
                    wait_time = (attempt + 1) * 5
                    warn(f"Rate limit, {wait_time}s bekleniyor...")
                    await asyncio.sleep(wait_time)
                else:
                    if attempt < max_retries - 1:
                        warn(f"LLM hatasi, tekrar deneniyor: {e}")
                        await asyncio.sleep(2)
                    else:
                        raise

        raise Exception(f"LLM max retry ({max_retries}) asildi")

    def _clean_json_response(self, response: str) -> str:
        """JSON yaniti temizle."""
        if not response:
            return "{}"
        response_clean = response.strip()

        if "```json" in response_clean:
            start = response_clean.find("```json") + 7
            end = response_clean.find("```", start)
            response_clean = response_clean[start:end].strip()
        elif "```" in response_clean:
            start = response_clean.find("```") + 3
            newline = response_clean.find("\n", start)
            if newline != -1:
                start = newline + 1
            end = response_clean.find("```", start)
            response_clean = response_clean[start:end].strip()

        return response_clean

    # =====================================================
    # v6.0 - PDF Servisi Client
    # =====================================================

    async def _download_pdf_from_service(
        self,
        pdf_url: str,
        company_name: str
    ) -> Optional[Dict]:
        """
        İzole PDF servisinden PDF indir ve metin al.

        v6.0 Yeni özellik: Ana sistemi bloke etmeden paralel PDF indirme.

        Args:
            pdf_url: TSG PDF viewer URL
            company_name: Firma adi (filtreleme icin)

        Returns:
            Dict: {
                "text": str,           # PDF metni (pdfplumber/PyPDF2)
                "pdf_base64": str,     # Binary PDF (OCR icin fallback)
                "pdf_path": str,       # Indirilen PDF yolu
                "extraction_method": str  # "pdfplumber", "pypdf2", "binary"
            }
        """
        step("PDF SERVISI CAGIRILIYOR (v6.0)")

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.PDF_SERVICE_URL}/download",
                    json={
                        "pdf_url": pdf_url,
                        "company_name": company_name,
                        "return_binary_on_failure": True  # OCR fallback icin
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("success"):
                        # Metin veya binary dondu
                        text = data.get("text", "")
                        char_count = data.get("char_count", 0)
                        method = data.get("extraction_method", "unknown")

                        if text and char_count > 100:
                            success(f"PDF servisi basarili: {char_count} karakter ({method})")
                            return {
                                "text": text,
                                "pdf_base64": None,
                                "pdf_path": data.get("pdf_path"),
                                "extraction_method": method
                            }
                        elif data.get("pdf_base64"):
                            # Metin çıkarılamadı ama binary PDF var
                            warn("PDF metin çıkarılamadı, binary PDF alındı (OCR için)")
                            return {
                                "text": None,
                                "pdf_base64": data.get("pdf_base64"),
                                "pdf_path": data.get("pdf_path"),
                                "extraction_method": "binary"
                            }

                    warn(f"PDF servisi basarisiz: {data.get('error')}")
                    return None

                else:
                    error(f"PDF servisi HTTP hatasi: {response.status_code}")
                    return None

        except httpx.ConnectError:
            warn("PDF servisi baglantilamadi (localhost:8001) - fallback kullanilacak")
            return None
        except httpx.TimeoutException:
            warn("PDF servisi timeout - fallback kullanilacak")
            return None
        except Exception as e:
            error(f"PDF servisi hatasi: {e}")
            return None

    async def _ocr_pdf_binary(self, pdf_base64: str, company_name: str) -> str:
        """
        Binary PDF'i OCR ile oku.

        PDF servisi metin cikaramadiysa bu metod kullanilir.
        Local Tesseract veya Vision API ile.

        Args:
            pdf_base64: Base64 encoded PDF
            company_name: Firma adi

        Returns:
            str: OCR ile okunan metin
        """
        step("PDF BINARY OCR (Fallback)")

        try:
            import tempfile
            from pathlib import Path

            # PDF'i temp dosyaya kaydet
            pdf_bytes = base64.b64decode(pdf_base64)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_bytes)
                temp_pdf_path = f.name

            log(f"PDF kaydedildi: {temp_pdf_path} ({len(pdf_bytes)} bytes)")

            # Tesseract OCR ile dene
            try:
                from app.agents.tsg.ocr import GazeteOCR

                # PDF'in her sayfasini PNG'ye cevir ve OCR yap
                # (Bu kısım mevcut GazeteOCR'ı kullanır)
                text = GazeteOCR.read_pdf_file(temp_pdf_path)

                if text and len(text) > 100:
                    text = GazeteOCR.extract_ilan_from_page(text, company_name)
                    success(f"OCR basarili: {len(text)} karakter")
                    return text

            except Exception as ocr_err:
                warn(f"Tesseract OCR hatasi: {ocr_err}")

            # Fallback: pdfplumber (binary PDF icin)
            try:
                import pdfplumber

                text = ""
                with pdfplumber.open(temp_pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"

                if text and len(text) > 100:
                    success(f"pdfplumber (local) basarili: {len(text)} karakter")
                    return text

            except Exception as pdf_err:
                warn(f"Local pdfplumber hatasi: {pdf_err}")

            return ""

        except Exception as e:
            error(f"PDF binary OCR hatasi: {e}")
            return ""


# Standalone test
if __name__ == "__main__":
    import sys

    async def test():
        company = sys.argv[1] if len(sys.argv) > 1 else "Turkcell"
        step(f"TSG Agent v3.4 Hackathon Test: {company}")

        agent = TSGAgent()

        def progress_callback(progress_info):
            log(f"[{progress_info.progress:3d}%] {progress_info.message}")

        agent.set_progress_callback(progress_callback)

        step("AGENT CALISIYOR")
        result = await agent.run(company)

        step("SONUCLAR")
        log(f"STATUS: {result.status}")
        log(f"SUMMARY: {result.summary}")

        if result.key_findings:
            log("KEY FINDINGS (5 BASLIK):")
            for finding in result.key_findings:
                log(f"  * {finding}")

        if result.warning_flags:
            warn("WARNINGS:")
            for warning in result.warning_flags:
                warn(f"  ! {warning}")

        if result.error:
            error(f"ERROR: {result.error}")

        # Hackathon output
        log("\nHACKATHON OUTPUT:")
        print(json.dumps(result.data, indent=2, ensure_ascii=False, default=str))

        # Screenshot path
        screenshot = result.data.get("tsg_sonuc", {}).get("gazete_bilgisi", {}).get("screenshot_path")
        if screenshot:
            success(f"\nGAZETE SCREENSHOT: {screenshot}")
        else:
            warn("\nGAZETE SCREENSHOT: Alinamadi")

        step("TEST TAMAMLANDI")

    asyncio.run(test())
