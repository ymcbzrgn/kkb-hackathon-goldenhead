"""
Resmi Gazete Scraper - Ihale Yasaklama Kararlari

Playwright ile https://www.resmigazete.gov.tr sitesini tarar.
Cesitli Ilanlar bolumunden "Ihalelere Katilmaktan Yasaklama Karari" iceren
ilanlari bulur ve PDF'lerini indirir.

Ozellikler:
- Tarih araligi destegi (date_from, date_to)
- Son N gun tarama (profil bazli: light=60, standard=90, aggressive=180)
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

from app.core.config import settings
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

    # Yasaklama kelime filtreleri (legacy - fallback için)
    YASAKLAMA_KEYWORDS = [
        "yasaklama",
        "ihalelere katilmaktan yasaklama",
        "ihale yasak",
        "yasaklanmis",
    ]

    # Fuzzy Yasaklama Pattern'leri (regex-based - daha kapsamlı)
    YASAKLAMA_PATTERNS = [
        r"yasak(lama|lanm[ıi][şs]|l[ıi])",  # yasaklama, yasaklanmış, yasaklı
        r"ihale(ler)?e?\s*(kat[ıi]l)?m?a?k?tan\s*yasak",  # ihalelere katılmaktan yasak
        r"kamu\s*ihale(ler)?i?(ne|nden)?\s*yasak",  # kamu ihalelerine yasak
        r"4734\s*say[ıi]l[ıi]\s*kanun",  # 4734 sayılı kanun
        r"58\.?\s*madde",  # 58. madde (yasaklama maddesi)
        r"ihalelerden\s*(men|uzakla[şs]t[ıi]r)",  # ihalelerden men/uzaklaştırma
        r"ihaleye\s*kat[ıi]lma\s*yasa[gğ][ıi]",  # ihaleye katılma yasağı
    ]

    # Minimum text threshold for OCR fallback
    MIN_TEXT_THRESHOLD = 200

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
        self._temp_dir = tempfile.mkdtemp(prefix="ihale_pdf_")

        # Config'den ayarlari al (profil bazli)
        ihale_config = settings.profile_config.ihale
        self._page_timeout = ihale_config.page_timeout_ms  # 30000ms
        self._request_delay = ihale_config.request_delay_sec  # 1.5s
        self._default_days = ihale_config.search_days_default  # 60/90/180
        self._full_days = ihale_config.search_days_full  # 1095 (3 yil)

        log(f"Scraper Config: timeout={self._page_timeout}ms, delay={self._request_delay}s, days={self._default_days}")

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
        self.page.set_default_timeout(self._page_timeout)

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

    def _generate_date_list(
        self,
        days: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[datetime]:
        """
        Tarih listesi olustur.

        Mod 1: date_from + date_to parametreleri verilmisse, o aralik
        Mod 2: Sadece days verilmisse, son N gun

        Args:
            days: Kac gun geriye gidilecek (varsayilan: config'den)
            date_from: Baslangic tarihi (YYYY-MM-DD format)
            date_to: Bitis tarihi (YYYY-MM-DD format)

        Returns:
            List[datetime]: Tarih listesi (en yeniden eskiye)
        """
        dates = []

        if date_from and date_to:
            # Mod 1: Tarih araligi
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
                end_date = datetime.strptime(date_to, "%Y-%m-%d")

                # Tarihleri sirala (en yeni -> en eski)
                if start_date > end_date:
                    start_date, end_date = end_date, start_date

                log(f"Tarih araligi: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")

                current = end_date
                while current >= start_date:
                    # Hafta sonu kontrolu (Resmi Gazete Cumartesi-Pazar yayinlanmiyor)
                    if current.weekday() < 5:  # 0=Pazartesi, 4=Cuma
                        dates.append(current)
                    current -= timedelta(days=1)

            except ValueError as e:
                warn(f"Tarih format hatasi: {e}. Son {self._default_days} gun kullaniliyor.")
                return self._generate_date_list(days=self._default_days)

        else:
            # Mod 2: Son N gun
            if days is None:
                days = self._default_days

            today = datetime.now()

            for i in range(days):
                date = today - timedelta(days=i)
                # Hafta sonu kontrolu
                if date.weekday() < 5:
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
        days: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        company_name: Optional[str] = None,
        vergi_no: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Yasaklama kararlarini ara.

        Mod 1: date_from + date_to verilmisse -> belirli tarih araligi
        Mod 2: days verilmisse -> son N gun
        Mod 3: Hicbiri verilmemisse -> config'den varsayilan gun sayisi

        Args:
            days: Kac gun geriye taranacak (varsayilan: config'den)
            date_from: Baslangic tarihi (YYYY-MM-DD format)
            date_to: Bitis tarihi (YYYY-MM-DD format)
            company_name: Aranacak firma adi (opsiyonel)
            vergi_no: Aranacak vergi numarasi (opsiyonel)
            progress_callback: Progress callback fonksiyonu (progress_pct, message)

        Returns:
            Dict: Bulunan yasaklama kararlari
        """
        # Tarama modunu belirle
        if date_from and date_to:
            mode_desc = f"Tarih araligi: {date_from} - {date_to}"
        else:
            actual_days = days if days is not None else self._default_days
            mode_desc = f"Son {actual_days} gun"

        step(f"RESMI GAZETE TARAMASI BASLIYOR ({mode_desc})")

        results = {
            "taranan_gun_sayisi": 0,
            "bulunan_ilan_sayisi": 0,
            "yasaklama_kararlari": [],
            "hatalar": [],
            "tarama_tarihi": datetime.now().isoformat(),
            "tarama_modu": mode_desc
        }

        # Tarih listesi olustur (date_from/date_to veya days)
        dates = self._generate_date_list(days=days, date_from=date_from, date_to=date_to)
        log(f"{len(dates)} is gunu taranacak")

        # HYPER MODE: Paralel date scraping (10 browser)
        if progress_callback:
            progress_callback(15, f"HYPER MODE: {len(dates)} gün paralel taranıyor...")

        all_yasaklamalar = await self._parallel_date_scraping(dates, progress_callback)

        results["yasaklama_kararlari"] = all_yasaklamalar
        results["bulunan_ilan_sayisi"] = len(all_yasaklamalar)
        results["taranan_gun_sayisi"] = len(dates)

        # Final progress
        if progress_callback:
            progress_callback(45, f"Tarama tamamlandi: {results['bulunan_ilan_sayisi']} yasaklama karari")

        success(f"Tarama tamamlandi: {results['bulunan_ilan_sayisi']} yasaklama karari")
        return results

    async def _parallel_date_scraping(
        self,
        dates: List[datetime],
        progress_callback: Optional[callable] = None,
        num_connections: int = 50,  # 50 paralel bağlantı (HTML + PDF'ler)
        max_time_seconds: int = 200  # 4 dakika - 40s analiz rezervi
    ) -> List[Dict[str, Any]]:
        """
        ULTRA HYPER MODE: Paralel HTTP ile ÇEŞİTLİ İLANLAR taraması.

        DOĞRU YAKLAŞIM:
        1. Her tarih için Çeşitli İlanlar HTML sayfasını indir
        2. HTML'den PDF linklerini parse et (YYYYMMDD-4-N.pdf)
        3. Her PDF'i indir ve yasaklama kontrolü yap

        Yasaklama kararları SADECE Çeşitli İlanlar bölümünde yayınlanır!
        Ana Resmi Gazete PDF'inde değil!

        Args:
            dates: Taranacak tarih listesi (en yeniden eskiye sıralı)
            progress_callback: Progress callback
            num_connections: Paralel connection sayısı (default: 50)
            max_time_seconds: Maksimum tarama süresi (default: 200s)

        Returns:
            List[Dict]: Yasaklama içeren PDF'ler
        """
        import httpx
        import time as time_module
        import re
        from bs4 import BeautifulSoup

        if not dates:
            return []

        start_time = time_module.time()
        batch_size = 50  # Her batch'te 50 tarih (HTML + PDF'ler için)

        log(f"ÇEŞİTLİ İLANLAR TARAMASI: {len(dates)} gün, {num_connections} paralel, max {max_time_seconds}s")

        # Semaphore ile concurrent limit
        semaphore = asyncio.Semaphore(num_connections)
        all_results = []
        processed_count = [0]  # List to make it mutable in nested function
        total = len(dates)

        # TEK bir client - connection pooling ile
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=50)
        timeout = httpx.Timeout(15.0, connect=5.0)

        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as client:

            async def scrape_cesitli_ilanlar(date: datetime) -> List[Dict]:
                """Tek bir günün Çeşitli İlanlar sayfasını tara."""
                async with semaphore:
                    results = []

                    # Çeşitli İlanlar HTML URL'i
                    html_url = self.CESITLI_ILANLAR_URL_TEMPLATE.format(
                        year=date.year,
                        month=date.month,
                        day=date.day
                    )

                    try:
                        # HTML sayfasını indir
                        response = await client.get(html_url)

                        if response.status_code == 404:
                            # Hafta sonu veya tatil
                            processed_count[0] += 1
                            return []

                        if response.status_code != 200:
                            debug(f"[{date.strftime('%Y-%m-%d')}] HTML HTTP {response.status_code}")
                            processed_count[0] += 1
                            return []

                        # HTML'den PDF linklerini parse et
                        html_content = response.text
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # Tüm PDF linklerini bul (YYYYMMDD-4-N.pdf formatında)
                        pdf_links = []
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            if href.endswith('.pdf'):
                                # Relative URL'i absolute yap
                                if href.startswith('/'):
                                    pdf_url = f"https://www.resmigazete.gov.tr{href}"
                                elif not href.startswith('http'):
                                    # Same directory
                                    base_path = f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/{date.year}/{date.month:02d}/"
                                    pdf_url = base_path + href
                                else:
                                    pdf_url = href

                                link_text = link.get_text(strip=True)
                                pdf_links.append({
                                    'url': pdf_url,
                                    'text': link_text
                                })

                        if not pdf_links:
                            debug(f"[{date.strftime('%Y-%m-%d')}] PDF link bulunamadı")
                            processed_count[0] += 1
                            return []

                        debug(f"[{date.strftime('%Y-%m-%d')}] {len(pdf_links)} PDF bulundu")

                        # Her PDF'i indir ve yasaklama kontrolü yap
                        for pdf_info in pdf_links:
                            pdf_url = pdf_info['url']
                            link_text = pdf_info['text']

                            try:
                                pdf_response = await client.get(pdf_url)

                                if pdf_response.status_code != 200:
                                    continue

                                # PDF'i temp dosyaya kaydet
                                pdf_filename = pdf_url.split('/')[-1]
                                filepath = os.path.join(self._temp_dir, f"{date.strftime('%Y%m%d')}_{pdf_filename}")

                                with open(filepath, "wb") as f:
                                    f.write(pdf_response.content)

                                # Hızlı yasaklama kontrolü (PyMuPDF ile)
                                content = await self._quick_pdf_read_no_ocr(filepath)

                                # Fuzzy keyword match
                                has_yasaklama, confidence = self._fuzzy_keyword_match(content)

                                if has_yasaklama:
                                    log(f"[{date.strftime('%Y-%m-%d')}] YASAKLAMA BULUNDU: {link_text[:50]}... (conf={confidence:.2f})")
                                    results.append({
                                        "tarih": date.strftime("%d.%m.%Y"),
                                        "tarih_iso": date.strftime("%Y-%m-%d"),
                                        "kurum": link_text,
                                        "pdf_url": pdf_url,
                                        "pdf_path": filepath,
                                        "pdf_content": content[:50000],  # Max 50K karakter
                                        "match_confidence": confidence,
                                        "pdf_size_kb": len(pdf_response.content) // 1024,
                                        "gazete_metadata": {
                                            "tarih": date.strftime("%d %B %Y"),
                                            "cesitli_ilanlar_url": html_url,
                                            "url": pdf_url
                                        }
                                    })
                                else:
                                    # Yasaklama yok - temp dosyayı sil
                                    try:
                                        os.remove(filepath)
                                    except:
                                        pass

                            except httpx.TimeoutException:
                                debug(f"[{date.strftime('%Y-%m-%d')}] PDF timeout: {pdf_url}")
                                continue
                            except Exception as e:
                                debug(f"[{date.strftime('%Y-%m-%d')}] PDF error: {e}")
                                continue

                        processed_count[0] += 1
                        return results

                    except httpx.TimeoutException:
                        debug(f"[{date.strftime('%Y-%m-%d')}] HTML Timeout")
                        processed_count[0] += 1
                        return []
                    except Exception as e:
                        debug(f"[{date.strftime('%Y-%m-%d')}] Error: {e}")
                        processed_count[0] += 1
                        return []

            # BATCH İŞLEME: Tarihleri batch'lere böl, zaman dolunca dur
            log(f"Başlatılıyor: {total} gün batch'li paralel taranıyor (batch={batch_size})...")

            total_processed = 0
            batch_number = 0

            # Tarihleri batch'lere böl
            for batch_start in range(0, total, batch_size):
                # Zaman kontrolü - her batch öncesi
                elapsed = time_module.time() - start_time
                if elapsed >= max_time_seconds:
                    log(f"ZAMAN DOLDU: {elapsed:.0f}s >= {max_time_seconds}s, {total_processed}/{total} gün tarandı")
                    break

                batch_number += 1
                batch_end = min(batch_start + batch_size, total)
                batch_dates = dates[batch_start:batch_end]

                remaining_time = max_time_seconds - elapsed
                log(f"Batch {batch_number}: {len(batch_dates)} gün ({batch_start+1}-{batch_end}/{total}), kalan süre: {remaining_time:.0f}s")

                # Bu batch için task'ları oluştur
                tasks = [scrape_cesitli_ilanlar(date) for date in batch_dates]

                # Batch'i paralel işle - kalan süre kadar timeout
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=min(remaining_time, 90)  # Max 90s per batch
                    )

                    # Sonuçları birleştir (her task bir liste döndürür)
                    for result in results:
                        if isinstance(result, list):
                            all_results.extend(result)
                        elif isinstance(result, Exception):
                            debug(f"Task exception: {result}")

                    total_processed += len(batch_dates)

                except asyncio.TimeoutError:
                    log(f"Batch {batch_number} timeout, devam ediliyor...")
                    total_processed += len(batch_dates)

                # Progress güncelle
                if progress_callback:
                    pct = int((total_processed / total) * 30) + 15  # 15-45 arası
                    progress_callback(pct, f"{total_processed}/{total} gün tarandı, {len(all_results)} yasaklama bulundu")

        elapsed_total = time_module.time() - start_time
        log(f"ÇEŞİTLİ İLANLAR TARAMASI tamamlandı: {len(all_results)} yasaklama ({total_processed}/{total} gün, {elapsed_total:.0f}s)")

        return all_results

    async def _quick_pdf_read_no_ocr(self, pdf_path: str) -> str:
        """
        Ultra-fast PDF text extraction - OCR DISABLED.
        Sadece PyMuPDF ile text extraction (hız için).
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
            warn(f"PDF read error: {e}")
            return ""

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

                    # PDF'i click ile indir (retry mekanizması ile)
                    pdf_result = await self._download_pdf_with_retry(link, date)

                    if pdf_result:
                        yasaklama["pdf_path"] = pdf_result.get("path")
                        yasaklama["pdf_content"] = pdf_result.get("content")

                        # Fuzzy keyword matching ile yasaklama kontrolü
                        content = pdf_result.get("content", "")
                        has_yasaklama, confidence = self._fuzzy_keyword_match(content)

                        if has_yasaklama:
                            yasaklama["match_confidence"] = confidence
                            log(f"  YASAKLAMA BULUNDU (conf={confidence}): {text_clean[:50]}...")
                            yasaklamalar.append(yasaklama)
                        else:
                            debug(f"  (yasaklama yok): {text_clean[:30]}...")

                except Exception as e:
                    warn(f"Link isleme hatasi: {e}")
                    continue

        except Exception as e:
            error(f"Sayfa tarama hatasi: {e}")

        return yasaklamalar

    async def _download_pdf_with_retry(
        self,
        link_element,
        date: datetime,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        PDF download with exponential backoff retry.

        Args:
            link_element: Playwright link elementi
            date: Tarih (dosya adi icin)
            max_retries: Maksimum deneme sayısı

        Returns:
            Dict: PDF bilgileri (path, content) veya None
        """
        for attempt in range(max_retries):
            try:
                result = await self._download_pdf_via_click(link_element, date)

                if result and result.get("content"):
                    return result

                # Boş sonuç - bekle ve tekrar dene
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1, 2, 4 saniye
                    debug(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                warn(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        warn(f"PDF download failed after {max_retries} attempts")
        return None

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
        PDF'den text cikart (yasaklama kontrolu icin).

        Multi-strategy extraction:
        1. PyMuPDF ile text extraction
        2. Text < MIN_TEXT_THRESHOLD ise OCR fallback
        3. Her sayfa için ayrı ayrı OCR kontrolü
        """
        import re

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            text = ""
            pages_with_ocr = 0

            # Strategy 1: PyMuPDF text extraction
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text

            # Strategy 2: OCR fallback - text çok kısa ise tüm PDF'i OCR yap
            if len(text.strip()) < self.MIN_TEXT_THRESHOLD:
                log(f"Text çok kısa ({len(text.strip())} < {self.MIN_TEXT_THRESHOLD}), OCR başlatılıyor...")

                try:
                    from PIL import Image
                    import pytesseract
                    import io

                    ocr_text = ""
                    for page_num, page in enumerate(doc):
                        # Sayfayı görüntüye çevir (150 DPI)
                        pix = page.get_pixmap(dpi=150)
                        img = Image.open(io.BytesIO(pix.tobytes("png")))

                        # Tesseract OCR (Türkçe)
                        page_ocr = pytesseract.image_to_string(img, lang='tur')
                        ocr_text += page_ocr
                        pages_with_ocr += 1

                    # OCR daha fazla text çıkardıysa kullan
                    if len(ocr_text.strip()) > len(text.strip()):
                        log(f"OCR başarılı: {len(ocr_text)} karakter ({pages_with_ocr} sayfa)")
                        text = ocr_text
                    else:
                        debug(f"OCR text'ten daha az çıkardı, orijinal korunuyor")

                except ImportError as e:
                    warn(f"OCR kütüphanesi eksik (pytesseract/PIL): {e}")
                except Exception as e:
                    warn(f"OCR hatası: {e}")

            doc.close()
            return text

        except Exception as e:
            warn(f"PDF okuma hatasi: {e}")
            return ""

    def _normalize_turkish(self, text: str) -> str:
        """
        Türkçe karakterleri normalize et (case-insensitive matching için).
        """
        # Türkçe -> ASCII mapping
        tr_map = {
            'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
            'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
            'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
        }
        for tr, en in tr_map.items():
            text = text.replace(tr, en)
        return text.lower()

    def _fuzzy_keyword_match(self, content: str) -> tuple:
        """
        Regex-based fuzzy keyword matching.

        Returns: (is_match: bool, confidence: float)

        Confidence levels:
        - 1.0: 2+ pattern match (kesinlikle yasaklama)
        - 0.7: 1 pattern match (muhtemelen yasaklama)
        - 0.4: Fallback keyword match (olabilir)
        - 0.0: Eşleşme yok
        """
        import re

        content_normalized = self._normalize_turkish(content)

        match_count = 0
        matched_patterns = []

        for pattern in self.YASAKLAMA_PATTERNS:
            if re.search(pattern, content_normalized, re.IGNORECASE):
                match_count += 1
                matched_patterns.append(pattern)

        if match_count >= 2:
            debug(f"Fuzzy match: {match_count} pattern ({matched_patterns[:2]})")
            return (True, 1.0)
        elif match_count == 1:
            debug(f"Fuzzy match: 1 pattern ({matched_patterns[0][:30]})")
            return (True, 0.7)
        else:
            # Fallback: basit keyword kontrolü
            fallback_keywords = ["yasak", "ihale", "4734", "58. madde"]
            for kw in fallback_keywords:
                if kw in content_normalized:
                    debug(f"Fallback match: '{kw}'")
                    return (True, 0.4)
            return (False, 0.0)

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
            links = await self.page.query_selector_all(self.LINK_SELECTOR)
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
