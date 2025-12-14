"""
Ihale PDF Reader - Tesseract OCR ile Yasaklama Karari Okuma

Resmi Gazete'den indirilen yasaklama karari PDF'lerini okur.

ONEMLI:
- PyMuPDF KULLANILMIYOR - Her zaman Tesseract OCR!
- Yatay sayfalar icin 90 derece rotasyon denemesi yapilir
- Vision AI YOK!

Cikarilacak 9 Alan:
1. Ihale Kayit Numarasi (IKN/ISKN)
2. Yasaklama Karari Veren Bakanlik/Kurum
3. Ihaleyi Yapan Idarenin bilgileri (Adi, Adresi, Posta Kodu, Il/Ilce, Tel-Kep, E-Posta)
4. Yasaklanan Gercek/Tuzel Kisinin bilgileri (Adi, TC, Vergi No, Pasaport, Adresi)
5. Ortak Bilgileri (Adi, TC, Vergi No, Adresi)
6. Ortaklik Bilgileri
7. Yasaklama Kanun Dayanagi
8. Yasaklama Kanun Kapsami
9. Yasaklama Suresi

+ Metadata: Resmi Gazete Sayisi, Yayin Tarihi, Yasakli Kayit No
"""
import os
import re
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings
from app.agents.ihale.logger import log, step, success, error, warn, debug, Timer


class IhalePDFReader:
    """
    Ihale Yasaklama Karari PDF okuyucu.

    ONEMLI: PyMuPDF KULLANILMAZ! Her zaman Tesseract OCR kullanilir.
    Yatay sayfalar icin rotasyonlar config'e gore denenir.

    OCR Ayarlari (config.py profile'dan):
    - DPI: light_16gb=150, standard_24gb=200, aggressive=300
    - Rotasyonlar: light_16gb=[0,180], standard_24gb=[0,90,180], aggressive=[0,90,180,270]
    - Diller: light_16gb=["tur"], standard_24gb=["tur"], aggressive=["tur","eng"]

    Kullanim:
        reader = IhalePDFReader()
        result = await reader.read_yasaklama_karari(pdf_path)
    """

    # Regex pattern'lari (yasaklama karari alanlari icin)
    # OCR hatalarina karsi esnek pattern'lar
    PATTERNS = {
        # Yasak Kayit No
        "yasak_kayit_no": [
            r"YASAKLI\s*KAYIT\s*NO[:\s]*(\d+)",
            r"YASAKLI\s*KAY[IT]T\s*N[O0][:\s]*(\d+)",
        ],
        # Ihale Kayit No
        "ihale_kayit_no": [
            r"(?:IKN|ISKN|[IT]HALE\s*KAYIT\s*N)[:\s/]*(\d{4}/\d+)",
            r"1\.?\s*[IT]HALE\s*KAYIT\s*NUMARASI[^0-9]*(\d{4}/\d+)",
            r"(\d{4}/\d{6,})",
        ],
        # Yasaklayan Kurum (2. satir)
        "yasaklayan_kurum": [
            r"2\.?\s*YASAKLAMA\s*KARARI\s*VEREN[^A-Z]*([A-Z][A-Za-z\s/]+(?:Bakanl[il]g[il]|BAKANLI[GĞ]I|M[UÜ]d[UÜ]rl[UÜ][gğ][UÜ]))",
            r"(SA[GĞ]LIK\s*BAKANLI[GĞ]I[^,\n]*)",
            r"([A-Z][A-Za-z\s]+BAKANLI[GĞ]I[^,\n]*)",
        ],
        # Ihaleyi Yapan Idare - Adi
        "idare_adi": [
            r"3\.?\s*[IT]HALEY[IT]\s*YAPAN\s*[IT]DAREN[IT]N[^A-Z]*Ad[il][:\s]*([^\n]+)",
            r"Ad[il][:\s]+([A-Z][A-Z\s]+(?:HASTANES[IT]|BA[SŞ]HEK[IT]ML[IT][GĞ][IT]|M[UÜ]D[UÜ]RL[UÜ][GĞ][UÜ]))",
        ],
        # Ihaleyi Yapan Idare - Adresi
        "idare_adresi": [
            r"3\.?\s*[IT]HALEY[IT]\s*YAPAN.*?Adres[il][:\s]*([^\n]+)",
            r"Adres[il][:\s]+([A-Za-z0-9\s,./]+(?:Mahallesi|Caddesi|Sokak|No)[^\n]*)",
        ],
        # Ihaleyi Yapan Idare - Posta Kodu
        "idare_posta_kodu": [
            r"Posta\s*Kodu[:\s]*(\d{5})",
        ],
        # Ihaleyi Yapan Idare - Il/Ilce
        "idare_il_ilce": [
            r"[IT]l/[IT]l[cç]e[:\s]*([A-Z]+/[A-Z]+)",
            r"[IT]l/[IT]l[cç]e[:\s]*([^\n]+)",
        ],
        # Ihaleyi Yapan Idare - Tel-Kep
        "idare_tel_kep": [
            r"Tel-?Kep\s*Adres[il]?[:\s]*([^\n]+)",
        ],
        # Ihaleyi Yapan Idare - E-Posta
        "idare_eposta": [
            r"E-?Posta[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        ],
        # Yasakli Kisi - Vergi No
        "vergi_no": [
            r"Vergi\s*Kimlik[^0-9]*[:\s]*(\d{3,11})",
            r"M[UÜ]kellefiyet[^0-9]*[:\s]*(\d{3,11})",
            r"Vergi[^0-9]*(\d{10,11})",
            r"V\.?K\.?N\.?[:\s]*(\d{10,11})",
        ],
        # Yasakli Kisi - TC Kimlik
        "tc_kimlik": [
            r"T\.?C\.?\s*Kimlik\s*No[:\s]*(\d{11})",
            r"T\.?C\.?\s*Kimlik[^0-9]*(\d{11})",
        ],
        # Yasakli Kisi - Pasaport No
        "pasaport_no": [
            r"Pasaport\s*No[:\s]*([A-Z0-9]+)",
        ],
        # Yasakli Kisi - Adresi
        "yasakli_adresi": [
            r"4\.?\s*[IT]HALELERE\s*KATILMAKTAN.*?Adres[il][:\s]*([^\n]+)",
        ],
        # Yasak Suresi
        "yasak_suresi": [
            r"9\.?\s*YASAKLAMA\s*S[UÜ]RES[IT][:\s]*(\d+\s*/?\s*(?:YIL|AY|GUN|Y[IT]L))",
            r"YASAKLAMA\s*S[UÜ]RES[IT][:\s]*(\d+\s*/?\s*(?:YIL|AY|G[UÜ]N))",
            r"S[UÜ]RES[IT][:\s]*(\d+)\s*/?\s*(YIL|AY|GUN|Y[IT]L)",
        ],
        # Kanun Dayanagi
        "kanun_dayanagi": [
            r"7\.?\s*YASAKLAMA\s*KANUN\s*DAYANA[GĞ]I[:\s]*([^\n]+)",
            r"(\d{4}\s*Say[il]+[^,\n]*Kanun[u]?)",
        ],
        # Yasak Kapsami
        "yasak_kapsami": [
            r"8\.?\s*YASAKLAMA\s*KANUN\s*KAPSAMI[:\s]*([^\n]+)",
            r"(T[UÜ]m\s*[IT]halelerden)",
            r"(Belirli\s*[IT]halelerden)",
        ],
        # Ortak Bilgileri - Adi
        "ortak_adi": [
            r"5\.?\s*ORTAK\s*B[IT]LG[IT]LER[IT][^A]*Ad[il]/[UÜ]nvan[il][:\s]*([^\n]+)",
        ],
        # Ortak Bilgileri - TC
        "ortak_tc": [
            r"5\.?\s*ORTAK.*?T\.?C\.?\s*Kimlik\s*No[:\s]*(\d{11})",
        ],
        # Ortak Bilgileri - Vergi No
        "ortak_vergi_no": [
            r"5\.?\s*ORTAK.*?Vergi\s*Kimlik[^0-9]*[:\s]*(\d{3,11})",
        ],
        # Ortak Bilgileri - Adresi
        "ortak_adresi": [
            r"5\.?\s*ORTAK.*?Adres[il][:\s]*([^\n]+)",
        ],
    }

    # Firma adi pattern'lari
    FIRMA_PATTERNS = [
        # LIMITED SIRKETI ile biten
        r"Ad[il][:\s]+([A-Z][A-Z\s]+(?:LIMITED|LTD|ANONIM)\s*[SŞ][IT]RKET[IT])",
        # TUZEL KISININ altindaki satir
        r"T[UÜ]ZEL\s*K[IT][SŞ][IT]N[IT]N[^A-Z]*([A-Z][A-Z\s]+(?:LIMITED|LTD|A\.?[SŞ]\.?))",
        # Tum buyuk harfli firma adi
        r"([A-Z][A-Z\s]+(?:GIDA|KOZMET[IT]K|[IT]N[SŞ]AAT|T[IT]CARET|TEKST[IT]L|METAL|PLAST[IT]K)[A-Z\s]*(?:LIMITED|LTD|[SŞ][IT]RKET[IT]))",
    ]

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="ihale_ocr_")
        # OCR ayarlarini config'den al (profil bazli)
        self._ocr_config = settings.profile_config.ihale.ocr
        log(f"OCR Config: DPI={self._ocr_config.dpi}, Rotasyonlar={self._ocr_config.rotations}, Diller={self._ocr_config.languages}")

    async def read_yasaklama_karari(
        self,
        source: str,
        is_url: bool = False,
        gazete_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Yasaklama karari PDF'ini oku ve yapisal veri cikar.

        ONEMLI: PyMuPDF KULLANILMAZ! Her zaman Tesseract OCR kullanilir.

        Args:
            source: PDF dosya yolu veya URL
            is_url: True ise source URL olarak kullanilir
            gazete_metadata: Resmi Gazete bilgileri (sayi, tarih)

        Returns:
            Dict: Yapisal veri (9 alan + metadata)
        """
        step(f"PDF OKUMA (OCR): {source[:50]}...")

        result = {
            "kaynak": source,
            "okuma_tarihi": datetime.now().isoformat(),
            "okuma_yontemi": "Tesseract OCR + Rotasyon",
            "ham_metin": None,
            "yapisal_veri": self._empty_structure(),
            "resmi_gazete": gazete_metadata or {},
            "hata": None
        }

        try:
            # URL ise indir
            pdf_path = source
            if is_url:
                pdf_path = await self._download_pdf(source)
                if not pdf_path:
                    result["hata"] = "PDF indirilemedi"
                    return result

            # DIREKT OCR kullan (PyMuPDF YOK!)
            text = await self._extract_text_ocr_with_rotation(pdf_path)

            if text:
                result["ham_metin"] = text
                log(f"OCR ile {len(text)} karakter cikarildi")
            else:
                result["hata"] = "PDF okunamadi (OCR basarisiz)"
                return result

            # Yapisal veriyi cikar
            result["yapisal_veri"] = self._extract_structured_data(text)

            success("PDF okuma tamamlandi")
            return result

        except Exception as e:
            error(f"PDF okuma hatasi: {e}")
            result["hata"] = str(e)
            return result

    async def read_html_content(
        self,
        html_content: str,
        gazete_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        HTML iceriginden yapisal veri cikar (PDF yerine).

        Bazi ilanlar PDF degil HTML olarak yayinlaniyor.

        Args:
            html_content: HTML veya text icerigi
            gazete_metadata: Resmi Gazete bilgileri

        Returns:
            Dict: Yapisal veri
        """
        result = {
            "kaynak": "HTML",
            "okuma_tarihi": datetime.now().isoformat(),
            "okuma_yontemi": "HTML Parse",
            "ham_metin": html_content,
            "yapisal_veri": self._empty_structure(),
            "resmi_gazete": gazete_metadata or {},
            "hata": None
        }

        try:
            # HTML tag'larini temizle
            clean_text = self._clean_html(html_content)
            result["ham_metin"] = clean_text

            # Yapisal veri cikar
            result["yapisal_veri"] = self._extract_structured_data(clean_text)

            return result

        except Exception as e:
            error(f"HTML okuma hatasi: {e}")
            result["hata"] = str(e)
            return result

    async def _extract_text_ocr_with_rotation(self, pdf_path: str) -> Optional[str]:
        """
        Tesseract OCR ile PDF'den text cikar.

        OCR Ayarlari config.py'den alinir (profil bazli):
        - DPI: light_16gb=150 (hizli), aggressive=300 (kaliteli)
        - Rotasyonlar: light_16gb=[0,180] (2 deneme), aggressive=[0,90,180,270] (4 deneme)
        - Diller: light_16gb=["tur"] (1 dil), aggressive=["tur","eng"] (2 dil)

        Performans: light_16gb = 2 OCR/sayfa, aggressive = 8 OCR/sayfa

        Args:
            pdf_path: PDF dosya yolu

        Returns:
            str: Cikartilan text veya None
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract

            ocr = self._ocr_config
            log(f"PDF → Image donusumu (DPI={ocr.dpi})...")

            # PDF'i goruntulere donustur (profil DPI kullan)
            images = convert_from_path(pdf_path, dpi=ocr.dpi)

            text_parts = []

            for i, image in enumerate(images):
                log(f"OCR: Sayfa {i + 1}/{len(images)} ({len(ocr.rotations)} rotasyon, {len(ocr.languages)} dil)")

                # Her rotasyon icin dene (config'den)
                best_text = ""
                best_rotation = 0

                for rotation in ocr.rotations:
                    # Rotasyon uygula
                    if rotation > 0:
                        rotated_image = image.rotate(rotation, expand=True)
                    else:
                        rotated_image = image

                    # OCR yap (config'deki dilleri dene)
                    page_text = None
                    for lang in ocr.languages:
                        try:
                            page_text = pytesseract.image_to_string(
                                rotated_image,
                                lang=lang
                            )
                            if page_text and len(page_text.strip()) > 50:
                                break
                        except Exception:
                            continue

                    # En iyi sonucu kaydet
                    if page_text and len(page_text.strip()) > len(best_text.strip()):
                        best_text = page_text
                        best_rotation = rotation

                        # Eger yeterince uzun text bulduysa dur (config threshold)
                        if len(best_text.strip()) > ocr.min_text_threshold:
                            break

                if best_text:
                    if best_rotation > 0:
                        debug(f"Sayfa {i+1}: {best_rotation}° rotasyon kullanildi")
                    text_parts.append(f"--- Sayfa {i + 1} ---\n{best_text}")

            return "\n\n".join(text_parts) if text_parts else None

        except ImportError as e:
            warn(f"OCR kutuphanesi eksik: {e}")
            warn("pip install pdf2image pytesseract gerekli")
            return None
        except Exception as e:
            warn(f"Tesseract OCR hatasi: {e}")
            return None

    async def _download_pdf(self, url: str) -> Optional[str]:
        """PDF'i URL'den indir."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30)

                if response.status_code == 200:
                    filename = f"download_{hash(url) % 10000}.pdf"
                    filepath = os.path.join(self._temp_dir, filename)

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    return filepath

        except Exception as e:
            warn(f"PDF indirme hatasi: {e}")

        return None

    def _clean_html(self, html: str) -> str:
        """HTML tag'larini temizle."""
        # Script ve style tag'larini kaldir
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Tum HTML tag'larini kaldir
        text = re.sub(r'<[^>]+>', ' ', text)

        # HTML entity'leri coz
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # Coklu bosluklari teke indir
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _empty_structure(self) -> Dict[str, Any]:
        """Bos yapisal veri sablonu - TUM 9 ALAN + METADATA."""
        return {
            # Meta
            "yasak_kayit_no": None,

            # 1. Ihale Kayit No
            "ihale_kayit_no": None,

            # 2. Yasaklayan Kurum
            "yasaklayan_kurum": None,

            # 3. Ihaleyi Yapan Idare (6 alt alan)
            "ihale_idaresi": {
                "adi": None,
                "adresi": None,
                "posta_kodu": None,
                "il_ilce": None,
                "tel_kep": None,
                "eposta": None
            },

            # 4. Yasaklanan Gercek/Tuzel Kisi (5 alt alan)
            "yasakli_kisi": {
                "adi": None,
                "tc_kimlik": None,
                "vergi_no": None,
                "pasaport_no": None,
                "adresi": None
            },

            # 5. Ortak Bilgileri (liste)
            "ortaklar": [],

            # 6. Ortaklik Bilgileri
            "ortaklik_bilgileri": None,

            # 7. Kanun Dayanagi
            "kanun_dayanagi": None,

            # 8. Yasak Kapsami
            "yasak_kapsami": None,

            # 9. Yasak Suresi
            "yasak_suresi": None
        }

    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """
        Ham metinden yapisal veri cikar.

        TUM 9 ALAN + METADATA icin regex pattern'lari kullanir.
        OCR hatalarina karsi esnek pattern'lar kullanilir.

        Args:
            text: OCR ile cikartilan ham metin

        Returns:
            Dict: Yapisal veri
        """
        data = self._empty_structure()

        if not text:
            return data

        # Normalize et - satir sonlarini koru (regex icin onemli)
        text_with_newlines = text
        text_single_line = text.replace('\n', ' ').replace('\r', ' ')

        # ========== META ==========
        # Yasak Kayit No
        for pattern in self.PATTERNS.get("yasak_kayit_no", []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["yasak_kayit_no"] = match.group(1)
                break

        # ========== 1. IHALE KAYIT NO ==========
        for pattern in self.PATTERNS["ihale_kayit_no"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["ihale_kayit_no"] = match.group(1)
                break

        # ========== 2. YASAKLAYAN KURUM ==========
        for pattern in self.PATTERNS["yasaklayan_kurum"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["yasaklayan_kurum"] = match.group(1).strip()
                break

        # ========== 3. IHALEYI YAPAN IDARE ==========
        # Adi
        for pattern in self.PATTERNS["idare_adi"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                data["ihale_idaresi"]["adi"] = match.group(1).strip()
                break

        # Adresi
        for pattern in self.PATTERNS["idare_adresi"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                data["ihale_idaresi"]["adresi"] = match.group(1).strip()
                break

        # Posta Kodu
        for pattern in self.PATTERNS["idare_posta_kodu"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["ihale_idaresi"]["posta_kodu"] = match.group(1)
                break

        # Il/Ilce
        for pattern in self.PATTERNS["idare_il_ilce"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["ihale_idaresi"]["il_ilce"] = match.group(1).strip()
                break

        # Tel-Kep
        for pattern in self.PATTERNS["idare_tel_kep"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE)
            if match:
                data["ihale_idaresi"]["tel_kep"] = match.group(1).strip()
                break

        # E-Posta
        for pattern in self.PATTERNS["idare_eposta"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["ihale_idaresi"]["eposta"] = match.group(1).strip()
                break

        # ========== 4. YASAKLI KISI ==========
        # Vergi No
        for pattern in self.PATTERNS["vergi_no"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["yasakli_kisi"]["vergi_no"] = match.group(1)
                break

        # TC Kimlik
        for pattern in self.PATTERNS["tc_kimlik"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["yasakli_kisi"]["tc_kimlik"] = match.group(1)
                break

        # Pasaport No
        for pattern in self.PATTERNS["pasaport_no"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val and val.upper() not in ['NO', 'YOK', '-']:
                    data["yasakli_kisi"]["pasaport_no"] = val
                break

        # Adresi
        for pattern in self.PATTERNS["yasakli_adresi"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                data["yasakli_kisi"]["adresi"] = match.group(1).strip()
                break

        # Firma Adi
        for pattern in self.FIRMA_PATTERNS:
            match = re.search(pattern, text)
            if match:
                firma_adi = match.group(1).strip()
                if len(firma_adi) > 10:
                    data["yasakli_kisi"]["adi"] = firma_adi
                    break

        # ========== 5. ORTAK BILGILERI ==========
        ortak = {}

        # Ortak Adi
        for pattern in self.PATTERNS["ortak_adi"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                ortak["adi"] = match.group(1).strip()
                break

        # Ortak TC
        for pattern in self.PATTERNS["ortak_tc"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                ortak["tc_kimlik"] = match.group(1)
                break

        # Ortak Vergi No
        for pattern in self.PATTERNS["ortak_vergi_no"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                ortak["vergi_no"] = match.group(1)
                break

        # Ortak Adresi
        for pattern in self.PATTERNS["ortak_adresi"]:
            match = re.search(pattern, text_with_newlines, re.IGNORECASE | re.DOTALL)
            if match:
                ortak["adresi"] = match.group(1).strip()
                break

        if ortak.get("adi"):
            data["ortaklar"].append(ortak)

        # ========== 7. KANUN DAYANAGI ==========
        for pattern in self.PATTERNS["kanun_dayanagi"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["kanun_dayanagi"] = match.group(1).strip()
                break

        # ========== 8. YASAK KAPSAMI ==========
        for pattern in self.PATTERNS["yasak_kapsami"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["yasak_kapsami"] = match.group(1).strip()
                break

        # ========== 9. YASAK SURESI ==========
        for pattern in self.PATTERNS["yasak_suresi"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    data["yasak_suresi"] = f"{match.group(1)} / {match.group(2).upper()}"
                else:
                    data["yasak_suresi"] = match.group(1).strip()
                break

        return data


# Test
async def test_pdf_reader():
    """PDF Reader test fonksiyonu."""
    print("\n" + "="*60)
    print("Ihale PDF Reader Test (OCR + Rotasyon)")
    print("="*60)

    reader = IhalePDFReader()

    # Test: HTML content okuma
    test_html = """
    <html>
    <body>
    <h1>SAĞLIK BAKANLIĞI</h1>
    <p>YASAKLI KAYIT NO: 251823</p>
    <p>1. İhale Kayıt No: 2024/1234567</p>
    <p>2. Yasaklama Kararı Veren: SAĞLIK BAKANLIĞI / Kamu Hastaneleri</p>
    <p>3. İhaleyi Yapan İdarenin</p>
    <p>Adı: KONYA BEYHEKİM HASTANESİ</p>
    <p>Adresi: Beyhekim Mahallesi No:14</p>
    <p>Posta Kodu: 42000</p>
    <p>İl/İlçe: KONYA/SELÇUKLU</p>
    <p>4. Yasaklanan Firma: ABC İNŞAAT LİMİTED ŞİRKETİ</p>
    <p>Vergi Kimlik: 1234567890</p>
    <p>9. Yasaklama Süresi: 1 / YIL</p>
    <p>7. 4735 Sayılı Kamu İhale Sözleşmeleri Kanunu</p>
    <p>8. Tüm İhalelerden</p>
    </body>
    </html>
    """

    result = await reader.read_html_content(
        test_html,
        gazete_metadata={"sayi": "33081", "tarih": "18 Kasım 2025"}
    )

    print(f"\nOkuma Yontemi: {result['okuma_yontemi']}")
    print(f"Resmi Gazete: {result['resmi_gazete']}")
    print(f"\nYapisal Veri:")

    def print_dict(d, indent=2):
        for key, value in d.items():
            if isinstance(value, dict):
                print(" " * indent + f"{key}:")
                print_dict(value, indent + 2)
            elif isinstance(value, list) and value:
                print(" " * indent + f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        print_dict(item, indent + 2)
            elif value:
                print(" " * indent + f"{key}: {value}")

    print_dict(result['yapisal_veri'])


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_pdf_reader())
