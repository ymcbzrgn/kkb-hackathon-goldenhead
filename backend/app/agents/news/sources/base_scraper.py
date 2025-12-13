"""
Base News Scraper - Tum news scraper'larin temel sinifi
TSG/Ihale pattern: Playwright + async + error handling
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from app.agents.news.logger import log, step, success, error, warn, debug, Timer
from app.agents.news.extraction import get_extractor
from app.agents.news.ocr import get_ocr


# HACKATHON: Kaynak bazlı OCR profilleri (10 GÜVENİLİR KAYNAK)
# LLM extraction fail olduğunda OCR kullanılsın mı?
SOURCE_PROFILES = {
    # Devlet Kaynakları (OCR backup önemli)
    "Anadolu Ajansı": {"ocr_on_fail": True},   # JS-heavy, OCR backup
    "TRT Haber": {"ocr_on_fail": True},        # Devlet sitesi, OCR backup
    # Demirören Grubu (LLM genelde OK)
    "Hürriyet": {"ocr_on_fail": False},        # LLM OK
    "Milliyet": {"ocr_on_fail": False},        # LLM OK (70+ yıllık arşiv!)
    "CNN Türk": {"ocr_on_fail": False},        # LLM OK
    # Ekonomi/Finans (LLM OK)
    "Dünya Gazetesi": {"ocr_on_fail": False},  # LLM OK
    "Ekonomim": {"ocr_on_fail": False},        # LLM OK
    "Bigpara": {"ocr_on_fail": False},         # LLM OK
    # Diğer Güvenilir (LLM OK)
    "NTV": {"ocr_on_fail": False},             # LLM OK
    "Sözcü": {"ocr_on_fail": False},           # LLM OK
}


class BaseNewsScraper(ABC):
    """Temel haber scraper sinifi."""
    
    BASE_URL: str = ""
    SEARCH_URL: str = ""
    NAME: str = "Base Scraper"
    
    PAGE_TIMEOUT = 45000
    NAVIGATION_TIMEOUT = 30000  # 20s -> 30s (daha güvenli)
    ELEMENT_TIMEOUT = 15000
    REQUEST_DELAY = 2.0
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self.name = self.NAME or self.__class__.__name__
    
    async def __aenter__(self):
        await self._start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_browser()
        return False
    
    async def _start_browser(self):
        step(f"BROWSER BASLATIYOR ({self.name})")
        try:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                locale='tr-TR'
            )
            self.page = await context.new_page()
            self.page.set_default_timeout(self.PAGE_TIMEOUT)
            success(f"Browser baslatildi ({self.name})")
        except Exception as e:
            error(f"Playwright baslatilamadi: {e}")
            raise
    
    async def _close_browser(self):
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            error(f"Browser kapatma hatasi: {e}")
    
    async def _delay(self, seconds: Optional[float] = None):
        await asyncio.sleep(seconds if seconds else self.REQUEST_DELAY)
    
    async def _safe_goto(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        Güvenli sayfa navigasyonu.

        networkidle yerine domcontentloaded kullanılıyor çünkü:
        - networkidle bazı sitelerde asla tamamlanmıyor (infinite polling)
        - domcontentloaded + manual delay daha güvenilir
        """
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=self.NAVIGATION_TIMEOUT)
            await self._delay(2.0)  # Extra wait for JS rendering
            return True
        except Exception as e:
            warn(f"Navigation error: {url} - {e}")
            return False
    
    async def _safe_type(self, selector: str, text: str) -> bool:
        try:
            await self.page.wait_for_selector(selector, timeout=self.ELEMENT_TIMEOUT)
            await self.page.fill(selector, text)
            return True
        except Exception:
            return False
    
    async def _get_attribute(self, selector: str, attr: str) -> Optional[str]:
        try:
            element = await self.page.query_selector(selector)
            return await element.get_attribute(attr) if element else None
        except Exception:
            return None
    
    @abstractmethod
    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        pass
    
    async def get_article_detail(self, url: str) -> Optional[Dict]:
        try:
            if not await self._safe_goto(url):
                return None

            await self._delay(2.0)
            html_content = await self.page.content()
            text_content = await self.page.inner_text("body")
            og_image = await self._get_opengraph_image()

            extractor = get_extractor()
            article = await extractor.extract_article(
                url=url,
                html_content=html_content,
                text_content=text_content,
                source_name=self.name
            )

            if not article:
                # HACKATHON: Akıllı OCR karar - kaynak profiline göre
                profile = SOURCE_PROFILES.get(self.name, {"ocr_on_fail": False})
                if profile.get("ocr_on_fail"):
                    warn(f"LLM extraction failed, OCR fallback aktif: {self.name}")
                    article = await self._ocr_fallback(url)
                    if not article:
                        return None
                else:
                    warn(f"LLM extraction failed, OCR skipped: {self.name}")
                    return None  # Haberi skip et (hızlı!)

            if not article.get("image_url") and og_image:
                article["image_url"] = og_image

            # HACKATHON: Screenshot capture
            # Her haber için benzersiz ID oluştur
            article_id = str(uuid.uuid4())[:8]
            article["id"] = article_id

            # JPEG full page screenshot al ve kaydet
            screenshot_path = await self._capture_screenshot(article_id)
            if screenshot_path:
                article["screenshot_path"] = screenshot_path
            else:
                article["screenshot_path"] = None
                warn(f"Screenshot alınamadı: {url[:50]}...")

            return article
        except Exception as e:
            error(f"Article detail error: {e}")
            return None
    
    async def _get_opengraph_image(self) -> Optional[str]:
        try:
            og = await self._get_attribute('meta[property="og:image"]', 'content')
            if og:
                return og
            return await self._get_attribute('meta[name="twitter:image"]', 'content')
        except Exception:
            return None
    
    async def _ocr_fallback(self, url: str) -> Optional[Dict]:
        try:
            ocr = get_ocr()
            ocr_text = await ocr.extract_from_page(self.page, max_chars=30000)  # HACKATHON: Kalite > Hız, tam metin!

            if not ocr_text or len(ocr_text) < 100:
                return None

            extractor = get_extractor()
            article = await extractor.extract_article(
                url=url,
                html_content=f"<body>{ocr_text}</body>",
                text_content=ocr_text,
                source_name=f"{self.name} (OCR)"
            )

            if article:
                article['extracted_via_ocr'] = True
                success("OCR fallback successful!")
            return article
        except Exception as e:
            error(f"OCR fallback error: {e}")
            return None

    async def _capture_screenshot(self, article_id: str) -> Optional[str]:
        """
        Haber sayfasının JPEG screenshot'ını al ve kaydet.

        HACKATHON GEREKSİNİMİ: Her haber için JPEG görüntüsü gerekli.
        Full page screenshot alınır (kullanıcı tercihi).

        Args:
            article_id: Benzersiz haber ID'si (dosya adı için)

        Returns:
            Screenshot dosya yolu veya None (hata durumunda)
        """
        try:
            # Screenshot klasörünü oluştur
            screenshot_dir = Path("data/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            # JPEG full page screenshot al
            screenshot_bytes = await self.page.screenshot(
                type="jpeg",
                quality=85,
                full_page=True
            )

            # Dosyaya kaydet
            filename = f"{article_id}.jpg"
            filepath = screenshot_dir / filename

            with open(filepath, "wb") as f:
                f.write(screenshot_bytes)

            debug(f"Screenshot kaydedildi: {filepath}")
            return str(filepath)

        except Exception as e:
            warn(f"Screenshot capture hatası: {e}")
            return None
    
    async def search_and_fetch(self, company_name: str, max_articles: int = 3, skip_details: bool = False) -> List[Dict]:
        """
        Haber ara ve detaylarını getir.

        Args:
            company_name: Firma adı
            max_articles: Maksimum haber sayısı
            skip_details: True ise LLM extraction atlanır (DEMO MODE için hızlı)
        """
        try:
            results = await self.search(company_name, max_results=max_articles)
            if not results:
                return []

            # DEMO MODE: LLM extraction atla, sadece search sonuçlarını döndür
            if skip_details:
                articles = []
                for result in results[:max_articles]:
                    articles.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "date": result.get("date", "unknown"),
                        "text": result.get("snippet", ""),
                        "source": self.name,
                        "id": str(uuid.uuid4())[:8],
                        "screenshot_path": None  # Screenshot yok (hızlı mod)
                    })
                log(f"[{self.name}] {len(articles)} haber bulundu (skip_details=True)")
                return articles

            # FULL MODE: Her haber için detay çek (LLM extraction)
            articles = []
            for result in results[:max_articles]:
                detail = await self.get_article_detail(result['url'])
                if detail:
                    detail['source'] = self.name
                    detail['search_snippet'] = result.get('snippet', '')
                    articles.append(detail)

            return articles
        except Exception as e:
            error(f"search_and_fetch error: {e}")
            return []
