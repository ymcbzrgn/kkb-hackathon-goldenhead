"""
Resmi Gazete Scraper - Ihale Yasaklama Kararlari

Playwright ile https://www.resmigazete.gov.tr sitesini tarar.
Cesitli Ilanlar bolumunden "Ihalelere Katilmaktan Yasaklama Karari" iceren
ilanlari bulur ve PDF'lerini indirir.

Ozellikler:
- Son 90 gun tarama (On-Demand)
- "Yasaklama" kelimesi iceren ilanlari filtreleme
- PDF indirme
- Rate limiting (1-2 saniye delay)
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from app.agents.ihale.logger import log, step, success, error, warn, debug, Timer


class ResmiGazeteScraper:
    """
    Resmi Gazete - Cesitli Ilanlar Scraper.

    Kullanim:
        async with ResmiGazeteScraper() as scraper:
            results = await scraper.search_yasaklama_kararlari(
                days=90,
                company_name="ABC INSAAT"
            )
    """

    # URL'ler
    BASE_URL = "https://www.resmigazete.gov.tr"

    # Cesitli Ilanlar URL formati
    # https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/YYYY/MM/YYYYMMDD-4.htm
    CESITLI_ILANLAR_URL_TEMPLATE = (
        "https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/"
        "{year}/{month:02d}/{year}{month:02d}{day:02d}-4.htm"
    )

    # Ilan detay URL formati
    ILAN_DETAY_URL_TEMPLATE = (
        "https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/"
        "{year}/{month:02d}/{year}{month:02d}{day:02d}-4-{index}.htm"
    )

    # HTML Selector'lar (Resmi Gazete - Word HTML format)
    # NOT: .fihrist-item yok, direkt <a> tag'lari kullaniliyor
    LINK_SELECTOR = "a"
    CONTENT_CONTAINER = "body"

    # Yasaklama kelime filtreleri
    YASAKLAMA_KEYWORDS = [
        "yasaklama",
        "ihalelere katilmaktan yasaklama",
        "ihale yasak",
        "yasaklanmis",
    ]

    # Timeout ayarlari
    PAGE_TIMEOUT = 30000  # 30 saniye
    REQUEST_DELAY = 1.5  # Rate limiting (saniye)

    # Tarama ayarlari
    DEFAULT_DAYS = 90  # Son 90 gun

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
        self._temp_dir = tempfile.mkdtemp(prefix="ihale_pdf_")

    async def __aenter__(self):
        """Context manager girisi - browser baslat."""
        await self._start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager cikisi - browser kapat."""
        await self._close_browser()
        return False

    async def _start_browser(self):
        """Playwright browser'i baslat."""
        from playwright.async_api import async_playwright

        step("BROWSER BASLATILIYOR")

        self._playwright = await async_playwright().start()

        # Headless mode
        self.browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )

        # Context (accept_downloads=True for PDF download)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='tr-TR',
            accept_downloads=True,
        )

        # Sayfa olustur
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.PAGE_TIMEOUT)

        success("Browser baslatildi")

    async def _close_browser(self):
        """Browser'i kapat."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            success("Browser kapatildi")
        except Exception as e:
            error(f"Browser kapatma hatasi: {e}")

    def _generate_date_list(self, days: int = 90) -> List[datetime]:
        """
        Son N gun icin tarih listesi olustur.

        Args:
            days: Kac gun geriye gidilecek

        Returns:
            List[datetime]: Tarih listesi (en yeniden eskiye)
        """
        today = datetime.now()
        dates = []

        for i in range(days):
            date = today - timedelta(days=i)
            # Hafta sonu kontrolu (Resmi Gazete Cumartesi-Pazar yayinlanmiyor)
            if date.weekday() < 5:  # 0=Pazartesi, 4=Cuma
                dates.append(date)

        return dates

    def _build_cesitli_ilanlar_url(self, date: datetime) -> str:
        """Belirli tarih icin Cesitli Ilanlar URL'i olustur."""
        return self.CESITLI_ILANLAR_URL_TEMPLATE.format(
            year=date.year,
            month=date.month,
            day=date.day
        )

    async def search_yasaklama_kararlari(
        self,
        days: int = 90,
        company_name: Optional[str] = None,
        vergi_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Son N gundeki yasaklama kararlarini ara.

        Args:
            days: Kac gun geriye taranacak (default: 90)
            company_name: Aranacak firma adi (opsiyonel)
            vergi_no: Aranacak vergi numarasi (opsiyonel)

        Returns:
            Dict: Bulunan yasaklama kararlari
        """
        step(f"RESMI GAZETE TARAMASI BASLIYOR (Son {days} gun)")

        results = {
            "taranan_gun_sayisi": 0,
            "bulunan_ilan_sayisi": 0,
            "yasaklama_kararlari": [],
            "hatalar": [],
            "tarama_tarihi": datetime.now().isoformat()
        }

        # Tarih listesi olustur
        dates = self._generate_date_list(days)
        log(f"{len(dates)} is gunu taranacak")

        for i, date in enumerate(dates):
            try:
                date_str = date.strftime("%d.%m.%Y")
                log(f"[{i+1}/{len(dates)}] Tarih: {date_str}")

                # Cesitli Ilanlar sayfasini ac
                yasaklamalar = await self._scrape_date(date)

                if yasaklamalar:
                    results["yasaklama_kararlari"].extend(yasaklamalar)
                    results["bulunan_ilan_sayisi"] += len(yasaklamalar)
                    log(f"  -> {len(yasaklamalar)} yasaklama karari bulundu")

                results["taranan_gun_sayisi"] += 1

                # Rate limiting
                await asyncio.sleep(self.REQUEST_DELAY)

            except Exception as e:
                error(f"Tarih tarama hatasi ({date_str}): {e}")
                results["hatalar"].append({
                    "tarih": date_str,
                    "hata": str(e)
                })

        success(f"Tarama tamamlandi: {results['bulunan_ilan_sayisi']} yasaklama karari")
        return results

    async def _scrape_date(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Belirli bir tarihteki yasaklama kararlarini tara.

        NOT: Resmi Gazete sayfasi Word HTML formatinda.
        Linkler direkt <a> tag'lari ve PDF'lere isaret ediyor.
        PDF icerigi OCR ile okunacak.

        Args:
            date: Taranacak tarih

        Returns:
            List[Dict]: Bulunan yasaklama kararlari
        """
        url = self._build_cesitli_ilanlar_url(date)
        yasaklamalar = []

        try:
            # Sayfaya git
            response = await self.page.goto(url, wait_until="networkidle")

            # 404 kontrolu
            if response and response.status == 404:
                debug(f"Sayfa bulunamadi: {url}")
                return []

            await asyncio.sleep(1)  # Sayfa yuklenmesini bekle

            # Resmi Gazete metadata'sini cikart (Sayi ve Tarih)
            gazete_metadata = await self._extract_gazete_metadata(date)
            debug(f"Gazete metadata: {gazete_metadata}")

            # Tum linkleri al (Word HTML formatinda direkt <a> tag'lari)
            links = await self.page.query_selector_all(self.LINK_SELECTOR)

            for link in links:
                try:
                    # Link textini ve href'i al
                    text = await link.inner_text()
                    href = await link.get_attribute("href")

                    # Sadece PDF linkleri (YYYYMMDD-4-N.pdf formatinda)
                    if not href or not href.endswith(".pdf"):
                        continue

                    text_clean = text.strip() if text else ""

                    # Her PDF'i indir ve icinde yasaklama var mi kontrol et
                    yasaklama = {
                        "tarih": date.strftime("%d.%m.%Y"),
                        "kurum": text_clean,
                        "href": href,
                        "url": url,
                        "pdf_path": None,
                        "pdf_content": None,
                        "gazete_metadata": gazete_metadata  # Resmi Gazete Sayisi + Tarih
                    }

                    # PDF'i click ile indir (403 engelini asma)
                    pdf_result = await self._download_pdf_via_click(link, date)

                    if pdf_result:
                        yasaklama["pdf_path"] = pdf_result.get("path")
                        yasaklama["pdf_content"] = pdf_result.get("content")

                        # Icerikte yasaklama var mi kontrol et
                        content = pdf_result.get("content", "").lower()
                        has_yasaklama = any(
                            keyword in content
                            for keyword in self.YASAKLAMA_KEYWORDS
                        )

                        if has_yasaklama:
                            log(f"  YASAKLAMA BULUNDU: {text_clean[:50]}...")
                            yasaklamalar.append(yasaklama)
                        else:
                            debug(f"  (yasaklama yok): {text_clean[:30]}...")

                except Exception as e:
                    warn(f"Link isleme hatasi: {e}")
                    continue

        except Exception as e:
            error(f"Sayfa tarama hatasi: {e}")

        return yasaklamalar

    async def _download_pdf_via_click(
        self,
        link_element,
        date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        PDF'i link'e tiklayarak indir (403 engelini asma).

        Resmi Gazete direkt URL erisimini engelliyor,
        bu yuzden browser uzerinden tikla + download kullaniyoruz.

        Args:
            link_element: Playwright link elementi
            date: Tarih (dosya adi icin)

        Returns:
            Dict: PDF bilgileri (path, content) veya None
        """
        try:
            # Download beklemeye basla
            async with self.page.expect_download(timeout=30000) as download_info:
                await link_element.click()

            download = await download_info.value

            # Gecici dosyaya kaydet
            filename = f"yasaklama_{date.strftime('%Y%m%d')}_{download.suggested_filename}"
            filepath = os.path.join(self._temp_dir, filename)
            await download.save_as(filepath)

            log(f"PDF indirildi: {filename}")

            # PyMuPDF ile text cikar (hizli kontrol icin)
            content = await self._quick_pdf_read(filepath)

            return {
                "path": filepath,
                "content": content
            }

        except Exception as e:
            warn(f"PDF click-download hatasi: {e}")
            return None

    async def _quick_pdf_read(self, pdf_path: str) -> str:
        """
        PDF'den hizli text cikart (yasaklama kontrolu icin).

        PyMuPDF ile text extraction - OCR yapilmaz.
        Detayli OCR, pdf_reader.py tarafindan yapilacak.
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            text = ""

            for page in doc:
                text += page.get_text()

            doc.close()
            return text

        except Exception as e:
            warn(f"PDF okuma hatasi: {e}")
            return ""

    async def _extract_gazete_metadata(self, date: datetime) -> Dict[str, str]:
        """
        Resmi Gazete metadata'sini cikart (Sayi ve Tarih).

        Cesitli Ilanlar sayfasinda:
        - "18 Kasim 2025 SALI" ve "Sayi : 33081" formatinda bilgiler var

        Args:
            date: Tarih

        Returns:
            Dict: {sayi, tarih} veya bos dict
        """
        metadata = {
            "sayi": None,
            "tarih": date.strftime("%d %B %Y")  # Default: tarihten uret
        }

        try:
            # Sayfa iceriginden Sayi bilgisini cikart
            page_content = await self.page.content()

            # Sayi pattern'i: "Sayı : 33081" veya "Sayi: 33081"
            import re
            sayi_match = re.search(r'Say[iı]\s*:\s*(\d{5})', page_content)
            if sayi_match:
                metadata["sayi"] = sayi_match.group(1)
                debug(f"Resmi Gazete Sayisi: {metadata['sayi']}")

            # Tarih pattern'i: "18 Kasım 2025 SALI" veya "18 Kasim 2025"
            tarih_patterns = [
                r'(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})',
                r'(\d{1,2}\s+(?:Ocak|Subat|Mart|Nisan|Mayis|Haziran|Temmuz|Agustos|Eylul|Ekim|Kasim|Aralik)\s+\d{4})',
            ]
            for pattern in tarih_patterns:
                tarih_match = re.search(pattern, page_content)
                if tarih_match:
                    metadata["tarih"] = tarih_match.group(1)
                    break

        except Exception as e:
            warn(f"Gazete metadata cikarma hatasi: {e}")

        return metadata

    async def _download_pdf_from_page(
        self,
        page_url: str,
        date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Ilan detay sayfasindan PDF indir.

        Args:
            page_url: Ilan detay sayfasi URL'i
            date: Ilan tarihi

        Returns:
            Dict: PDF bilgileri (path, content) veya None
        """
        try:
            # Detay sayfasina git
            await self.page.goto(page_url, wait_until="networkidle")
            await asyncio.sleep(1)

            # Sayfa icerigini al (HTML olarak)
            content = await self.page.content()
            text_content = await self.page.inner_text("body")

            # PDF linki ara (eger varsa)
            pdf_links = await self.page.query_selector_all('a[href$=".pdf"]')

            pdf_path = None
            if pdf_links:
                for pdf_link in pdf_links:
                    href = await pdf_link.get_attribute("href")
                    if href:
                        pdf_url = urljoin(self.BASE_URL, href)
                        pdf_path = await self._download_pdf(pdf_url, date)
                        if pdf_path:
                            break

            return {
                "path": pdf_path,
                "content": text_content[:5000] if text_content else None,
                "html": content[:10000] if content else None
            }

        except Exception as e:
            warn(f"PDF indirme hatasi: {e}")
            return None

    async def _download_pdf(self, pdf_url: str, date: datetime) -> Optional[str]:
        """
        PDF dosyasini indir.

        Args:
            pdf_url: PDF URL'i
            date: Tarih (dosya adi icin)

        Returns:
            str: Indirilen PDF'in dosya yolu veya None
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(pdf_url, timeout=30)

                if response.status_code == 200:
                    # Dosya adi olustur
                    filename = f"yasaklama_{date.strftime('%Y%m%d')}_{hash(pdf_url) % 10000}.pdf"
                    filepath = os.path.join(self._temp_dir, filename)

                    # Dosyaya yaz
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    log(f"PDF indirildi: {filepath}")
                    return filepath

        except Exception as e:
            warn(f"PDF indirme hatasi ({pdf_url}): {e}")

        return None

    async def get_single_date_content(self, date: datetime) -> Dict[str, Any]:
        """
        Tek bir tarihin icerigini al (test icin).

        Args:
            date: Tarih

        Returns:
            Dict: Sayfa icerigi
        """
        url = self._build_cesitli_ilanlar_url(date)

        try:
            await self.page.goto(url, wait_until="networkidle")
            await asyncio.sleep(1)

            content = await self.page.content()
            text = await self.page.inner_text("body")

            # Linkleri al
            links = await self.page.query_selector_all(self.FIHRIST_ITEM)
            link_texts = []

            for link in links:
                text_content = await link.inner_text()
                href = await link.get_attribute("href")
                link_texts.append({
                    "text": text_content.strip(),
                    "href": href
                })

            return {
                "url": url,
                "date": date.strftime("%d.%m.%Y"),
                "links": link_texts,
                "link_count": len(link_texts),
                "html_preview": content[:2000]
            }

        except Exception as e:
            error(f"Sayfa okuma hatasi: {e}")
            return {"error": str(e)}


# Test
async def test_resmi_gazete_scraper():
    """Resmi Gazete Scraper test fonksiyonu."""
    print("\n" + "="*60)
    print("Resmi Gazete Scraper Test")
    print("="*60)

    async with ResmiGazeteScraper() as scraper:
        # Test 1: Tek tarih icerigi
        today = datetime.now()
        result = await scraper.get_single_date_content(today)

        print(f"\nTarih: {result.get('date')}")
        print(f"Link sayisi: {result.get('link_count')}")
        print(f"Linkler:")
        for link in result.get('links', [])[:5]:
            print(f"  - {link['text'][:50]}...")

        # Test 2: Yasaklama taramasi (sadece 3 gun)
        print("\n" + "-"*40)
        print("Yasaklama taramasi (son 3 gun):")
        results = await scraper.search_yasaklama_kararlari(days=3)

        print(f"Taranan gun: {results['taranan_gun_sayisi']}")
        print(f"Bulunan yasaklama: {results['bulunan_ilan_sayisi']}")

        if results['yasaklama_kararlari']:
            print("\nBulunan yasaklamalar:")
            for y in results['yasaklama_kararlari'][:3]:
                print(f"  - {y['tarih']}: {y['kurum'][:50]}...")


if __name__ == "__main__":
    asyncio.run(test_resmi_gazete_scraper())
