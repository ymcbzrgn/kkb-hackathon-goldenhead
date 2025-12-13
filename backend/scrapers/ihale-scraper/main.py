"""
Ihale Scraper Service - Resmi Gazete Yasaklama Kararlari Microservice.

K8s microservice olarak Resmi Gazete'yi tarar ve PDF'leri indirir.
Stateless design, browser pooling ile optimize edilmis.

Endpoints:
- POST /scrape - Yasaklama kararlarini tara
- GET /health - Health check
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import os
import tempfile
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MAX_DAYS = int(os.getenv("MAX_DAYS", "90"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.5"))
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "30000"))

# Browser pool (singleton)
browser_pool = None


class ScrapeRequest(BaseModel):
    company_name: str
    days: int = 90
    request_id: Optional[str] = None


class PDFInfo(BaseModel):
    date: str
    kurum: str
    href: str
    pdf_base64: Optional[str] = None
    has_yasaklama: bool = False
    gazete_sayi: Optional[str] = None
    gazete_tarih: Optional[str] = None


class ScrapeResponse(BaseModel):
    request_id: str
    company_name: str
    total_pdfs: int
    yasaklama_pdfs: int
    pdfs: List[PDFInfo]
    taranan_gun: int
    hatalar: List[str]
    duration_seconds: float


class HealthResponse(BaseModel):
    status: str
    browser: str


class BrowserPool:
    """
    Browser Pool - Connection reuse icin singleton browser.

    Her request'te browser acip kapatmak yerine tek browser kullanir.
    K8s pod restart ile browser da restart olur.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()

    async def get_context(self):
        """Thread-safe browser context olustur."""
        async with self._lock:
            # Browser None veya kapanmış mı kontrol et
            if self._browser is None or not self._browser.is_connected():
                logger.info("Browser not connected, reinitializing...")
                await self._cleanup_browser()
                await self._init_browser()

            # Her request icin yeni context (izolasyon)
            context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                locale='tr-TR',
                accept_downloads=True,
            )
            return context

    async def _init_browser(self):
        """Playwright browser baslat."""
        from playwright.async_api import async_playwright

        logger.info("Initializing browser pool...")
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process',  # K8s icin
            ]
        )
        logger.info("Browser pool initialized")

    async def _cleanup_browser(self):
        """Eski browser kaynaklarini temizle."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None
        logger.info("Browser resources cleaned up")

    async def close(self):
        """Browser'i kapat."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser pool closed")

    @property
    def is_ready(self) -> bool:
        return self._browser is not None


# Yasaklama keywords
YASAKLAMA_KEYWORDS = [
    "yasaklama",
    "ihalelere katilmaktan yasaklama",
    "ihale yasak",
    "yasaklanmis",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - browser pool baslat."""
    global browser_pool

    browser_pool = BrowserPool()
    logger.info("Ihale Scraper Service starting...")

    yield

    await browser_pool.close()
    logger.info("Ihale Scraper Service shutdown")


app = FastAPI(
    title="Ihale Scraper Service",
    description="Resmi Gazete Yasaklama Kararlari Scraper",
    version="1.0.0",
    lifespan=lifespan
)


def generate_date_list(days: int) -> List[datetime]:
    """Son N gun icin tarih listesi (hafta ici)."""
    today = datetime.now()
    dates = []

    for i in range(days):
        date = today - timedelta(days=i)
        if date.weekday() < 5:  # Pazartesi-Cuma
            dates.append(date)

    return dates


def build_cesitli_ilanlar_url(date: datetime) -> str:
    """Cesitli Ilanlar URL'i olustur."""
    return (
        f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/"
        f"{date.year}/{date.month:02d}/{date.year}{date.month:02d}{date.day:02d}-4.htm"
    )


async def scrape_date(page, date: datetime, temp_dir: str) -> List[Dict[str, Any]]:
    """
    Belirli tarihi tara ve PDF'leri indir.

    Returns:
        List of PDF info dicts
    """
    url = build_cesitli_ilanlar_url(date)
    pdfs = []

    try:
        logger.info(f"[{date.strftime('%d.%m.%Y')}] Fetching URL: {url}")
        response = await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)

        if response and response.status == 404:
            logger.info(f"[{date.strftime('%d.%m.%Y')}] 404 - No gazette for this date")
            return []

        logger.info(f"[{date.strftime('%d.%m.%Y')}] Page loaded, status: {response.status if response else 'unknown'}")
        await asyncio.sleep(1)

        # Gazete metadata
        page_content = await page.content()
        import re
        sayi_match = re.search(r'Say[iı]\s*:\s*(\d{5})', page_content)
        gazete_sayi = sayi_match.group(1) if sayi_match else None

        # PDF linklerini bul
        links = await page.query_selector_all("a")
        pdf_link_count = sum(1 for link in links if True)  # total links
        logger.info(f"[{date.strftime('%d.%m.%Y')}] Found {len(links)} links on page")

        for link in links:
            try:
                href = await link.get_attribute("href")
                if not href or not href.endswith(".pdf"):
                    continue

                text = await link.inner_text()
                text_clean = text.strip() if text else ""

                # PDF'i click ile indir
                pdf_info = {
                    "date": date.strftime("%d.%m.%Y"),
                    "kurum": text_clean,
                    "href": href,
                    "pdf_base64": None,
                    "has_yasaklama": False,
                    "gazete_sayi": gazete_sayi,
                    "gazete_tarih": date.strftime("%d %B %Y")
                }

                try:
                    async with page.expect_download(timeout=30000) as download_info:
                        await link.click()

                    download = await download_info.value
                    filename = f"yasaklama_{date.strftime('%Y%m%d')}_{download.suggested_filename}"
                    filepath = os.path.join(temp_dir, filename)
                    await download.save_as(filepath)

                    # Quick text extraction (yasaklama check)
                    content = quick_pdf_read(filepath)
                    has_yasaklama = any(kw in content.lower() for kw in YASAKLAMA_KEYWORDS)

                    if has_yasaklama:
                        # PDF'i base64 encode (OCR service'e gondermek icin)
                        with open(filepath, "rb") as f:
                            pdf_base64 = base64.b64encode(f.read()).decode()

                        pdf_info["pdf_base64"] = pdf_base64
                        pdf_info["has_yasaklama"] = True
                        pdfs.append(pdf_info)
                        logger.info(f"[{date.strftime('%d.%m.%Y')}] Yasaklama bulundu: {text_clean[:50]}")

                    # Cleanup
                    os.remove(filepath)

                except Exception as e:
                    logger.warning(f"PDF download error: {e}")
                    continue

            except Exception as e:
                logger.warning(f"Link processing error: {e}")
                continue

    except Exception as e:
        logger.error(f"Date scrape error ({date}): {e}")

    return pdfs


def quick_pdf_read(pdf_path: str) -> str:
    """PyMuPDF ile hizli text extraction."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        logger.warning(f"PDF read error: {e}")
        return ""


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_resmi_gazete(request: ScrapeRequest):
    """
    Resmi Gazete'den yasaklama kararlarini tara.

    Returns: PDF listesi (base64 encoded)
    """
    import time
    import uuid

    start = time.time()
    request_id = request.request_id or str(uuid.uuid4())

    logger.info(f"[{request_id}] Starting scrape for '{request.company_name}' (last {request.days} days)")

    # Browser context al
    context = await browser_pool.get_context()
    page = await context.new_page()
    page.set_default_timeout(PAGE_TIMEOUT)

    temp_dir = tempfile.mkdtemp(prefix="ihale_scraper_")

    all_pdfs = []
    hatalar = []
    taranan_gun = 0

    try:
        dates = generate_date_list(min(request.days, MAX_DAYS))
        logger.info(f"[{request_id}] Scanning {len(dates)} business days")

        for i, date in enumerate(dates):
            try:
                date_str = date.strftime("%d.%m.%Y")

                pdfs = await scrape_date(page, date, temp_dir)
                all_pdfs.extend(pdfs)
                taranan_gun += 1

                if pdfs:
                    logger.info(f"[{request_id}] [{i+1}/{len(dates)}] {date_str}: {len(pdfs)} yasaklama")

                # Rate limiting
                await asyncio.sleep(REQUEST_DELAY)

            except Exception as e:
                logger.error(f"[{request_id}] Error on {date_str}: {e}")
                hatalar.append(f"{date_str}: {str(e)}")

    finally:
        await page.close()
        await context.close()

        # Cleanup temp dir
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    duration = time.time() - start

    logger.info(
        f"[{request_id}] Complete: {len(all_pdfs)} yasaklama PDFs in {duration:.1f}s"
    )

    return ScrapeResponse(
        request_id=request_id,
        company_name=request.company_name,
        total_pdfs=len(all_pdfs),
        yasaklama_pdfs=sum(1 for p in all_pdfs if p["has_yasaklama"]),
        pdfs=[PDFInfo(**p) for p in all_pdfs],
        taranan_gun=taranan_gun,
        hatalar=hatalar,
        duration_seconds=round(duration, 2)
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(
        status="healthy" if browser_pool and browser_pool.is_ready else "starting",
        browser="ready" if browser_pool and browser_pool.is_ready else "initializing"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Ihale Scraper Service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
