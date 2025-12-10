"""
Ihale Orchestrator Service - Fan-out/Fan-in koordinasyon.

K8s microservice olarak Scraper ve OCR podlarini koordine eder.
10 dakika global timeout ile partial results destegi.

Flow:
1. Scraper'i cagir -> PDF listesi al
2. Her PDF icin OCR'i paralel cagir (asyncio.as_completed)
3. Matcher ile firma eslestir (LLM)
4. Sonuclari birlestir

Endpoints:
- POST /api/ihale/check - Firma yasaklama kontrolu
- GET /health - Health check
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import httpx
import uuid
import os
import time
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - K8s Service Discovery
SCRAPER_URL = os.getenv("SCRAPER_URL", "http://ihale-scraper:8080")
OCR_URL = os.getenv("OCR_URL", "http://ihale-ocr:8080")
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm-gateway:8080")

# Timeouts
GLOBAL_TIMEOUT = int(os.getenv("GLOBAL_TIMEOUT", "600"))  # 10 dakika
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "300"))  # 5 dakika
OCR_TIMEOUT = int(os.getenv("OCR_TIMEOUT", "60"))  # 1 dakika per PDF

# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None


class IhaleRequest(BaseModel):
    company_name: str
    vergi_no: Optional[str] = None
    days: int = 90
    request_id: Optional[str] = None


class YasaklamaKarari(BaseModel):
    kaynak: str
    tarih: str
    yasakli_firma: Optional[str] = None
    vergi_no: Optional[str] = None
    tc_kimlik: Optional[str] = None
    yasaklayan_kurum: Optional[str] = None
    yasak_suresi: Optional[str] = None
    kanun_dayanagi: Optional[str] = None
    eslestirme_skoru: float = 0.0
    eslestirme_nedeni: Optional[str] = None
    resmi_gazete_sayi: Optional[str] = None
    resmi_gazete_tarih: Optional[str] = None


class IhaleResponse(BaseModel):
    request_id: str
    company_name: str
    vergi_no: Optional[str] = None
    yasakli_mi: bool
    toplam_karar: int
    eslesen_karar: int
    yasaklama_kararlari: List[YasaklamaKarari]
    taranan_gun: int
    scraper_duration_ms: int
    ocr_duration_ms: int
    total_duration_seconds: float
    partial_results: bool = False


class HealthResponse(BaseModel):
    status: str
    scraper: str
    ocr: str
    llm_gateway: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - HTTP client baslat."""
    global http_client

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(GLOBAL_TIMEOUT, connect=10.0),
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20)
    )

    logger.info(f"Ihale Orchestrator initialized (timeout={GLOBAL_TIMEOUT}s)")
    yield

    await http_client.aclose()
    logger.info("Ihale Orchestrator shutdown")


app = FastAPI(
    title="Ihale Orchestrator Service",
    description="Fan-out/Fan-in koordinasyon - Scraper + OCR",
    version="1.0.0",
    lifespan=lifespan
)


async def call_scraper(company_name: str, days: int, request_id: str) -> Dict[str, Any]:
    """Scraper service'i cagir."""
    logger.info(f"[{request_id}] Calling scraper...")

    try:
        response = await http_client.post(
            f"{SCRAPER_URL}/scrape",
            json={
                "company_name": company_name,
                "days": days,
                "request_id": request_id
            },
            timeout=SCRAPER_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[{request_id}] Scraper: {result.get('total_pdfs', 0)} PDFs found")
            return result
        else:
            logger.error(f"[{request_id}] Scraper HTTP {response.status_code}")
            return {"error": f"HTTP {response.status_code}", "pdfs": []}

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] Scraper timeout")
        return {"error": "Timeout", "pdfs": []}
    except Exception as e:
        logger.error(f"[{request_id}] Scraper error: {e}")
        return {"error": str(e), "pdfs": []}


async def call_ocr(pdf_info: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """OCR service'i cagir."""
    pdf_id = pdf_info.get("href", "unknown")[:20]

    try:
        response = await http_client.post(
            f"{OCR_URL}/ocr",
            json={
                "pdf_base64": pdf_info.get("pdf_base64"),
                "pdf_id": pdf_id,
                "gazete_sayi": pdf_info.get("gazete_sayi"),
                "gazete_tarih": pdf_info.get("gazete_tarih"),
                "request_id": request_id
            },
            timeout=OCR_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            result["source_date"] = pdf_info.get("date")
            result["source_kurum"] = pdf_info.get("kurum")
            return result
        else:
            return {"status": "failed", "error": f"HTTP {response.status_code}"}

    except httpx.TimeoutException:
        return {"status": "failed", "error": "Timeout"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def call_matcher(
    company_name: str,
    vergi_no: Optional[str],
    ocr_results: List[Dict[str, Any]],
    request_id: str
) -> List[Dict[str, Any]]:
    """
    LLM ile firma eslestirme.

    Her OCR sonucundaki firma bilgilerini aranan firma ile karsilastirir.
    """
    matched = []

    for ocr in ocr_results:
        if ocr.get("status") != "success":
            continue

        yapisal = ocr.get("yapisal_veri", {})
        yasakli_kisi = yapisal.get("yasakli_kisi", {}) if yapisal else {}

        # Quick match - Vergi No ile
        if vergi_no and yasakli_kisi.get("vergi_no"):
            if vergi_no == yasakli_kisi.get("vergi_no"):
                matched.append({
                    "ocr": ocr,
                    "eslestirme_skoru": 1.0,
                    "eslestirme_nedeni": "Vergi numarasi eslesti"
                })
                continue

        # Firma adi eslestirme (basit)
        yasakli_firma = yasakli_kisi.get("adi", "") or ""
        if yasakli_firma and company_name:
            company_upper = company_name.upper()
            firma_upper = yasakli_firma.upper()

            # Basit kelime eslestirme
            company_words = set(company_upper.split())
            firma_words = set(firma_upper.split())

            common = company_words & firma_words
            # En az 2 ortak kelime veya ilk kelime ayni
            if len(common) >= 2 or (company_words and firma_words and list(company_words)[0] == list(firma_words)[0]):
                matched.append({
                    "ocr": ocr,
                    "eslestirme_skoru": 0.7,
                    "eslestirme_nedeni": f"Firma adi benzer ({len(common)} ortak kelime)"
                })

    logger.info(f"[{request_id}] Matcher: {len(matched)}/{len(ocr_results)} matched")
    return matched


@app.post("/api/ihale/check", response_model=IhaleResponse)
async def check_company(request: IhaleRequest):
    """
    Firma yasaklama kontrolu.

    Fan-out/Fan-in pattern:
    1. Scraper'i cagir -> PDF listesi
    2. OCR'lari paralel cagir (asyncio.as_completed)
    3. Matcher ile firma eslestir
    4. Sonuclari birlestir

    10 dakika global timeout - partial results destegi.
    """
    start = time.time()
    request_id = request.request_id or str(uuid.uuid4())

    logger.info(f"[{request_id}] Starting ihale check for '{request.company_name}'")

    # ========================================
    # STEP 1: SCRAPER
    # ========================================
    scraper_start = time.time()
    scraper_result = await call_scraper(request.company_name, request.days, request_id)
    scraper_duration = int((time.time() - scraper_start) * 1000)

    pdfs = scraper_result.get("pdfs", [])
    taranan_gun = scraper_result.get("taranan_gun", 0)

    if not pdfs:
        logger.info(f"[{request_id}] No yasaklama PDFs found")
        return IhaleResponse(
            request_id=request_id,
            company_name=request.company_name,
            vergi_no=request.vergi_no,
            yasakli_mi=False,
            toplam_karar=0,
            eslesen_karar=0,
            yasaklama_kararlari=[],
            taranan_gun=taranan_gun,
            scraper_duration_ms=scraper_duration,
            ocr_duration_ms=0,
            total_duration_seconds=round(time.time() - start, 2)
        )

    # ========================================
    # STEP 2: PARALLEL OCR (asyncio.as_completed)
    # ========================================
    ocr_start = time.time()
    MAX_OCR_WAIT = GLOBAL_TIMEOUT - (time.time() - start) - 60  # 1dk buffer

    ocr_tasks = [call_ocr(pdf, request_id) for pdf in pdfs]
    ocr_results = []
    partial_results = False

    try:
        for coro in asyncio.as_completed(ocr_tasks, timeout=max(30, MAX_OCR_WAIT)):
            try:
                result = await coro
                ocr_results.append(result)
            except Exception as e:
                logger.warning(f"[{request_id}] OCR task error: {e}")

    except asyncio.TimeoutError:
        partial_results = True
        remaining = len(pdfs) - len(ocr_results)
        logger.warning(f"[{request_id}] OCR timeout - {remaining} PDFs incomplete")

    ocr_duration = int((time.time() - ocr_start) * 1000)
    logger.info(f"[{request_id}] OCR complete: {len(ocr_results)}/{len(pdfs)} processed")

    # ========================================
    # STEP 3: MATCHER
    # ========================================
    matched = await call_matcher(
        request.company_name,
        request.vergi_no,
        ocr_results,
        request_id
    )

    # ========================================
    # STEP 4: FORMAT RESULTS
    # ========================================
    yasaklama_kararlari = []

    for m in matched:
        ocr = m["ocr"]
        yapisal = ocr.get("yapisal_veri", {}) or {}
        yasakli_kisi = yapisal.get("yasakli_kisi", {}) or {}

        yasaklama_kararlari.append(YasaklamaKarari(
            kaynak=ocr.get("source_kurum", "Resmi Gazete"),
            tarih=ocr.get("source_date", ""),
            yasakli_firma=yasakli_kisi.get("adi"),
            vergi_no=yasakli_kisi.get("vergi_no"),
            tc_kimlik=yasakli_kisi.get("tc_kimlik"),
            yasaklayan_kurum=yapisal.get("yasaklayan_kurum"),
            yasak_suresi=yapisal.get("yasak_suresi"),
            kanun_dayanagi=yapisal.get("kanun_dayanagi"),
            eslestirme_skoru=m["eslestirme_skoru"],
            eslestirme_nedeni=m["eslestirme_nedeni"],
            resmi_gazete_sayi=yapisal.get("yasak_kayit_no"),
            resmi_gazete_tarih=ocr.get("source_date")
        ))

    total_duration = time.time() - start

    logger.info(
        f"[{request_id}] Complete: {len(matched)} matches, "
        f"partial={partial_results}, {total_duration:.1f}s"
    )

    return IhaleResponse(
        request_id=request_id,
        company_name=request.company_name,
        vergi_no=request.vergi_no,
        yasakli_mi=len(matched) > 0,
        toplam_karar=len(ocr_results),
        eslesen_karar=len(matched),
        yasaklama_kararlari=yasaklama_kararlari,
        taranan_gun=taranan_gun,
        scraper_duration_ms=scraper_duration,
        ocr_duration_ms=ocr_duration,
        total_duration_seconds=round(total_duration, 2),
        partial_results=partial_results
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check - verify connectivity."""
    scraper_status = "unknown"
    ocr_status = "unknown"
    llm_status = "unknown"

    # Check scraper
    try:
        response = await http_client.get(f"{SCRAPER_URL}/health", timeout=2.0)
        scraper_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        scraper_status = "unreachable"

    # Check OCR
    try:
        response = await http_client.get(f"{OCR_URL}/health", timeout=2.0)
        ocr_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        ocr_status = "unreachable"

    # Check LLM Gateway
    try:
        response = await http_client.get(f"{LLM_GATEWAY_URL}/health", timeout=2.0)
        llm_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        llm_status = "unreachable"

    overall = "healthy" if scraper_status == "healthy" and ocr_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall,
        scraper=scraper_status,
        ocr=ocr_status,
        llm_gateway=llm_status
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Ihale Orchestrator Service",
        "version": "1.0.0",
        "status": "running",
        "timeout": GLOBAL_TIMEOUT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
