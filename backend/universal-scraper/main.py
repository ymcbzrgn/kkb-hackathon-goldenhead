"""
Universal News Scraper Service - Kubernetes Microservice
Tek image, 10 farklı deployment (SCRAPER_TYPE env variable ile)

SCRAPER_TYPE options:
- aa, trt, hurriyet, milliyet, cnnturk
- dunya, ekonomim, bigpara, ntv, sozcu
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import os
import time
import logging
import io
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import httpx
import pytesseract
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global HTTP client for LLM Gateway
http_client: Optional[httpx.AsyncClient] = None

# Scraper type from environment
SCRAPER_TYPE = os.getenv("SCRAPER_TYPE", "aa").lower()
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm-gateway:8080")

# Scraper configuration
SCRAPER_CONFIG = {
    "aa": {
        "name": "Anadolu Ajansi",
        "base_url": "https://www.aa.com.tr",
        "search_url": "https://www.aa.com.tr/tr/search?s=",
    },
    "trt": {
        "name": "TRT Haber",
        "base_url": "https://www.trthaber.com",
        "search_url": "https://www.trthaber.com/arama.html?q=",
    },
    "hurriyet": {
        "name": "Hurriyet",
        "base_url": "https://www.hurriyet.com.tr",
        "search_url": "https://www.hurriyet.com.tr/arama?q=",
    },
    "milliyet": {
        "name": "Milliyet",
        "base_url": "https://www.milliyet.com.tr",
        "search_url": "https://www.milliyet.com.tr/arama?query=",
    },
    "cnnturk": {
        "name": "CNN Turk",
        "base_url": "https://www.cnnturk.com",
        "search_url": "https://www.cnnturk.com/arama?query=",
    },
    "dunya": {
        "name": "Dunya Gazetesi",
        "base_url": "https://www.dunya.com",
        "search_url": "https://www.dunya.com/ara?key=",
    },
    "ekonomim": {
        "name": "Ekonomim",
        "base_url": "https://www.ekonomim.com",
        "search_url": "https://www.ekonomim.com/arama?q=",
    },
    "bigpara": {
        "name": "Bigpara",
        "base_url": "https://bigpara.hurriyet.com.tr",
        "search_url": "https://bigpara.hurriyet.com.tr/haberler/ara/?q=",
    },
    "ntv": {
        "name": "NTV",
        "base_url": "https://www.ntv.com.tr",
        "search_url": "https://www.ntv.com.tr/arama?q=",
    },
    "sozcu": {
        "name": "Sozcu",
        "base_url": "https://www.sozcu.com.tr",
        "search_url": "https://www.sozcu.com.tr/arama/?q=",
    },
}

# Playwright browser instance
playwright_instance = None
browser_instance = None
browser_lock = asyncio.Lock()


async def ensure_browser():
    """Browser'ın çalıştığından emin ol, gerekirse yeniden başlat."""
    global playwright_instance, browser_instance

    async with browser_lock:
        # Browser bağlı değilse yeniden başlat
        if browser_instance is None or not browser_instance.is_connected():
            logger.warning(f"[{SCRAPER_TYPE}] Browser not connected, restarting...")

            # Eski browser'ı temizle
            if browser_instance:
                try:
                    await browser_instance.close()
                except Exception as e:
                    logger.debug(f"Browser close error (ignored): {e}")

            # Playwright instance yoksa başlat
            if playwright_instance is None:
                from playwright.async_api import async_playwright
                playwright_instance = await async_playwright().start()

            # Yeni browser başlat
            browser_instance = await playwright_instance.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process'
                ]
            )
            logger.info(f"[{SCRAPER_TYPE}] Browser restarted successfully")

        return browser_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - initialize Playwright browser and HTTP client."""
    global playwright_instance, browser_instance, http_client

    from playwright.async_api import async_playwright

    # HTTP client for LLM Gateway
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        limits=httpx.Limits(max_connections=10)
    )

    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--single-process'
        ]
    )

    config = SCRAPER_CONFIG.get(SCRAPER_TYPE, SCRAPER_CONFIG["aa"])
    logger.info(f"Universal Scraper initialized: {config['name']} ({SCRAPER_TYPE})")

    yield

    if browser_instance:
        await browser_instance.close()
    if playwright_instance:
        await playwright_instance.stop()
    if http_client:
        await http_client.aclose()
    logger.info("Universal Scraper shutdown")


app = FastAPI(
    title=f"News Scraper - {SCRAPER_TYPE.upper()}",
    description=f"Kubernetes microservice for {SCRAPER_TYPE} news scraping",
    version="1.0.0",
    lifespan=lifespan
)


class ScrapeRequest(BaseModel):
    company_name: str
    max_articles: int = 5  # Quick Mode: 5 haber/kaynak
    request_id: str


class Article(BaseModel):
    title: str
    url: str
    date: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None
    source: str


class ScrapeResponse(BaseModel):
    source: str
    articles: List[Dict[str, Any]]
    duration_ms: int
    request_id: str


async def scrape_news(company_name: str, max_articles: int = 3) -> List[Dict[str, Any]]:
    """
    Generic scraping function - her kaynak icin CSS selector'lar farkli.
    Basit implementasyon: search URL + link collection.
    """
    import urllib.parse

    config = SCRAPER_CONFIG.get(SCRAPER_TYPE, SCRAPER_CONFIG["aa"])

    try:
        # Browser'ın çalıştığından emin ol (auto-recovery)
        browser = await ensure_browser()

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale='tr-TR'
        )
        page = await context.new_page()
        page.set_default_timeout(90000)  # 90s for OCR fallback

        # Search URL
        encoded_query = urllib.parse.quote(company_name)
        search_url = f"{config['search_url']}{encoded_query}"

        logger.info(f"[{config['name']}] Searching: {search_url}")

        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)  # JS rendering wait

        # OCR fallback icin screenshot'i SIMDI al (CSS selector'lar page'i navigate edecek)
        ocr_screenshot = None
        try:
            # Scroll to load lazy content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            ocr_screenshot = await page.screenshot(type="png", full_page=True)
            logger.info(f"[{config['name']}] OCR screenshot captured ({len(ocr_screenshot)} bytes)")
        except Exception as e:
            logger.warning(f"[{config['name']}] OCR screenshot failed: {e}")

        # OCR-Only Mode: CSS selector'ları bypass et, direkt OCR+LLM kullan
        # Neden: CSS selectors 9/10 kaynak için güncel değil, OCR daha güvenilir
        articles = []

        if ocr_screenshot:
            logger.info(f"[{config['name']}] Using OCR-only mode (CSS selectors bypassed)")
            articles = await ocr_llm_fallback(ocr_screenshot, company_name, config, context, max_articles)
        else:
            logger.warning(f"[{config['name']}] No screenshot available for OCR")

        await context.close()

        logger.info(f"[{config['name']}] Scraped {len(articles)} articles")
        return articles

    except Exception as e:
        logger.error(f"[{config['name']}] Scraping error: {e}")
        return []


def get_link_selectors(scraper_type: str) -> List[str]:
    """Site-specific CSS selectors for news links."""

    selectors = {
        "aa": [
            "#haber a[href^='/tr/']",
            "article a[href^='/tr/']",
            "div.card a[href^='/tr/']",
        ],
        "trt": [
            "div.news-item a",
            "article a",
            "a.card-link",
        ],
        "hurriyet": [
            "div.search-results a",
            "article a",
            "a.card-link",
        ],
        "milliyet": [
            "div.search-result a",
            "article a",
            "a[href*='/haber/']",
        ],
        "cnnturk": [
            "div.search-results a",
            "article a",
            "a[href*='/haber/']",
        ],
        "dunya": [
            "div.search-results a",
            "article a",
            "a[href*='/haber/']",
        ],
        "ekonomim": [
            "div.search-results a",
            "article a",
            "a[href*='/haber/']",
        ],
        "bigpara": [
            "div.news-list a",
            "article a",
            "a[href*='/haberler/']",
        ],
        "ntv": [
            "div.search-results a",
            "article a",
            "a[href*='/haber/']",
        ],
        "sozcu": [
            "div.search-results a",
            "article a",
            "a[href*='/haber/']",
        ],
    }

    return selectors.get(scraper_type, ["article a", "a[href*='/haber/']"])


async def get_article_detail(page, url: str, source_name: str) -> Optional[Dict[str, Any]]:
    """Get article details from URL."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Generic extraction
        title = ""
        text = ""
        date = ""
        image_url = ""

        # Try to get title
        for title_selector in ["h1", "h1.article-title", "h1.post-title", "article h1"]:
            try:
                title_elem = await page.query_selector(title_selector)
                if title_elem:
                    title = (await title_elem.inner_text()).strip()
                    if title:
                        break
            except:
                continue

        # Try to get article text
        for text_selector in ["article p", "div.article-body p", "div.post-content p", "div.news-content p"]:
            try:
                paragraphs = await page.query_selector_all(text_selector)
                if paragraphs:
                    texts = []
                    for p in paragraphs[:10]:
                        t = await p.inner_text()
                        if t and len(t.strip()) > 20:
                            texts.append(t.strip())
                    text = "\n".join(texts)
                    if text:
                        break
            except:
                continue

        # Try to get date
        for date_selector in ["time", "span.date", "div.date", "meta[property='article:published_time']"]:
            try:
                date_elem = await page.query_selector(date_selector)
                if date_elem:
                    if date_selector.startswith("meta"):
                        date = await date_elem.get_attribute("content")
                    else:
                        date = await date_elem.inner_text()
                    if date:
                        date = date.strip()[:50]
                        break
            except:
                continue

        # Try to get image
        try:
            og_image = await page.query_selector('meta[property="og:image"]')
            if og_image:
                image_url = await og_image.get_attribute("content")
        except:
            pass

        if not title:
            return None

        return {
            "title": title,
            "url": url,
            "date": date or "unknown",
            "text": text[:3000] if text else "",
            "image_url": image_url,
            "source": source_name
        }

    except Exception as e:
        logger.error(f"Article detail error: {e}")
        return None


async def get_article_detail_safe(context, url: str, config: dict) -> Optional[Dict[str, Any]]:
    """Safe wrapper for article detail extraction with its own page."""
    try:
        page = await context.new_page()
        page.set_default_timeout(90000)  # 90s for OCR fallback

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Generic extraction
        title = ""
        text = ""
        date = ""
        image_url = ""

        # Try to get title
        for title_selector in ["h1", "h1.article-title", "h1.post-title", "article h1"]:
            try:
                title_elem = await page.query_selector(title_selector)
                if title_elem:
                    title = (await title_elem.inner_text()).strip()
                    if title:
                        break
            except:
                continue

        # Try to get article text
        for text_selector in ["article p", "div.article-body p", "div.post-content p", "div.news-content p"]:
            try:
                paragraphs = await page.query_selector_all(text_selector)
                if paragraphs:
                    texts = []
                    for p in paragraphs[:10]:
                        t = await p.inner_text()
                        if t and len(t.strip()) > 20:
                            texts.append(t.strip())
                    text = "\n".join(texts)
                    if text:
                        break
            except:
                continue

        # Try to get date
        for date_selector in ["time", "span.date", "div.date", "meta[property='article:published_time']"]:
            try:
                date_elem = await page.query_selector(date_selector)
                if date_elem:
                    if date_selector.startswith("meta"):
                        date = await date_elem.get_attribute("content")
                    else:
                        date = await date_elem.inner_text()
                    if date:
                        date = date.strip()[:50]
                        break
            except:
                continue

        # Try to get image
        try:
            og_image = await page.query_selector('meta[property="og:image"]')
            if og_image:
                image_url = await og_image.get_attribute("content")
        except:
            pass

        await page.close()

        if not title:
            return None

        return {
            "title": title,
            "url": url,
            "date": date or "unknown",
            "text": text[:3000] if text else "",
            "image_url": image_url,
            "source": config['name']
        }

    except Exception as e:
        logger.debug(f"Safe article detail error: {e}")
        return None


async def ocr_llm_fallback(screenshot_bytes: bytes, company_name: str, config: dict, context, max_articles: int = 3) -> List[Dict[str, Any]]:
    """Screenshot + OCR + LLM ile haber cikarma (CSS selector basarisiz oldugunda).

    screenshot_bytes: CSS loop'tan ONCE alinmis screenshot (page artik farkli sayfada olabilir)
    """
    try:
        logger.info(f"[{config['name']}] Starting OCR+LLM fallback with pre-captured screenshot...")

        # 1. OCR ile metin cikar (screenshot zaten alinmis)
        image = Image.open(io.BytesIO(screenshot_bytes))
        ocr_text = pytesseract.image_to_string(image, lang='tur')

        if len(ocr_text.strip()) < 100:
            logger.warning(f"[{config['name']}] OCR text too short: {len(ocr_text)} chars")
            return []

        logger.info(f"[{config['name']}] OCR extracted {len(ocr_text)} chars")

        # 3. LLM Gateway'e gonder
        response = await http_client.post(
            f"{LLM_GATEWAY_URL}/ocr/extract-news",
            json={
                "ocr_text": ocr_text,
                "source_name": config['name'],
                "company_name": company_name
            },
            timeout=45
        )

        if response.status_code != 200:
            logger.error(f"[{config['name']}] LLM extraction failed: {response.status_code}")
            return []

        data = response.json()
        articles = []

        for item in data.get("articles", []):
            url = item.get("url")
            title = item.get("title")

            if url:
                # URL varsa detay sayfasina git
                # URL tam degilse base_url ekle
                if url.startswith("/"):
                    url = config['base_url'] + url

                article = await get_article_detail_safe(context, url, config)
                if article:
                    articles.append(article)
                    if len(articles) >= max_articles:
                        break
            elif title:
                # URL yoksa sadece baslik ile article olustur
                articles.append({
                    "title": title,
                    "url": config['base_url'],
                    "date": "unknown",
                    "text": "",
                    "image_url": "",
                    "source": config['name']
                })
                if len(articles) >= max_articles:
                    break

        logger.info(f"[{config['name']}] OCR+LLM fallback: {len(articles)} articles extracted")
        return articles

    except Exception as e:
        logger.error(f"[{config['name']}] OCR+LLM fallback error: {e}")
        return []


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    """Scrape news from this source."""
    start = time.time()
    config = SCRAPER_CONFIG.get(SCRAPER_TYPE, SCRAPER_CONFIG["aa"])

    try:
        articles = await scrape_news(
            request.company_name,
            max_articles=request.max_articles
        )

        duration_ms = int((time.time() - start) * 1000)

        return ScrapeResponse(
            source=config['name'],
            articles=articles,
            duration_ms=duration_ms,
            request_id=request.request_id
        )

    except Exception as e:
        logger.error(f"Scrape endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check - browser durumu dahil."""
    config = SCRAPER_CONFIG.get(SCRAPER_TYPE, SCRAPER_CONFIG["aa"])

    # Browser bağlantısını kontrol et
    browser_connected = browser_instance is not None and browser_instance.is_connected()

    if not browser_connected:
        # Browser bağlı değilse unhealthy döndür
        # Kubernetes liveness probe bunu yakalar ve pod'u restart eder
        raise HTTPException(
            status_code=503,
            detail=f"Browser not connected for {config['name']}"
        )

    return {
        "status": "healthy",
        "scraper_type": SCRAPER_TYPE,
        "source_name": config['name'],
        "browser_ready": True
    }


@app.get("/")
async def root():
    """Root endpoint."""
    config = SCRAPER_CONFIG.get(SCRAPER_TYPE, SCRAPER_CONFIG["aa"])
    return {
        "service": f"News Scraper - {config['name']}",
        "scraper_type": SCRAPER_TYPE,
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
