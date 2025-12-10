"""
News Orchestrator Service - Fan-out/Fan-in pattern for parallel scraping.
Kubernetes microservice that coordinates all scraper pods.
"""
from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
import asyncio
import httpx
import uuid
from typing import List, Dict, Optional, Any
import os
import time
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Scraper endpoints (K8s Service Discovery)
SCRAPERS = {
    "aa": os.getenv("AA_SCRAPER_URL", "http://aa-scraper:8080/scrape"),
    "trt": os.getenv("TRT_SCRAPER_URL", "http://trt-scraper:8080/scrape"),
    "hurriyet": os.getenv("HURRIYET_SCRAPER_URL", "http://hurriyet-scraper:8080/scrape"),
    "milliyet": os.getenv("MILLIYET_SCRAPER_URL", "http://milliyet-scraper:8080/scrape"),
    "cnnturk": os.getenv("CNNTURK_SCRAPER_URL", "http://cnnturk-scraper:8080/scrape"),
    "dunya": os.getenv("DUNYA_SCRAPER_URL", "http://dunya-scraper:8080/scrape"),
    "ekonomim": os.getenv("EKONOMIM_SCRAPER_URL", "http://ekonomim-scraper:8080/scrape"),
    "bigpara": os.getenv("BIGPARA_SCRAPER_URL", "http://bigpara-scraper:8080/scrape"),
    "ntv": os.getenv("NTV_SCRAPER_URL", "http://ntv-scraper:8080/scrape"),
    "sozcu": os.getenv("SOZCU_SCRAPER_URL", "http://sozcu-scraper:8080/scrape"),
}

LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm-gateway:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - initialize HTTP client."""
    global http_client

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(600.0, connect=10.0),  # 10 dakika hard limit
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=50)
    )

    logger.info(f"News Orchestrator initialized - {len(SCRAPERS)} scrapers configured")
    yield

    await http_client.aclose()
    logger.info("News Orchestrator shutdown")


app = FastAPI(
    title="News Orchestrator Service",
    description="Fan-out/Fan-in orchestrator for parallel news scraping",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class NewsRequest(BaseModel):
    company_name: str
    max_articles_per_source: int = 5  # Quick Mode: 5 haber/kaynak
    timeout_seconds: int = 120  # 120s for OCR fallback
    report_id: Optional[str] = None


class SourceResult(BaseModel):
    source: str
    status: str  # "success" or "failed"
    articles: List[Dict[str, Any]] = []
    duration_ms: int = 0
    error: Optional[str] = None


class NewsResponse(BaseModel):
    request_id: str
    company_name: str
    total_articles: int
    sources_completed: int
    sources_failed: int
    articles: List[Dict[str, Any]]
    analysis: Dict[str, Any]
    source_results: List[SourceResult]
    duration_seconds: float


class HealthResponse(BaseModel):
    status: str
    scrapers: Dict[str, str]
    llm_gateway: str


async def call_scraper(
    source: str,
    url: str,
    company_name: str,
    max_articles: int,
    request_id: str,
    timeout: int
) -> Dict[str, Any]:
    """Call a single scraper service."""
    start = time.time()

    try:
        response = await http_client.post(
            url,
            json={
                "company_name": company_name,
                "max_articles": max_articles,
                "request_id": request_id
            },
            timeout=timeout
        )

        duration_ms = int((time.time() - start) * 1000)

        if response.status_code == 200:
            result = response.json()
            articles = result.get("articles", [])

            # Add source to each article
            for article in articles:
                article["source"] = source

            logger.info(f"[{source}] Success: {len(articles)} articles in {duration_ms}ms")

            return {
                "source": source,
                "status": "success",
                "articles": articles,
                "duration_ms": duration_ms
            }
        else:
            logger.error(f"[{source}] HTTP {response.status_code}: {response.text[:200]}")
            return {
                "source": source,
                "status": "failed",
                "error": f"HTTP {response.status_code}",
                "duration_ms": duration_ms
            }

    except httpx.TimeoutException:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(f"[{source}] Timeout after {duration_ms}ms")
        return {
            "source": source,
            "status": "failed",
            "error": "Timeout",
            "duration_ms": duration_ms
        }
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(f"[{source}] Error: {e}")
        return {
            "source": source,
            "status": "failed",
            "error": str(e),
            "duration_ms": duration_ms
        }


async def call_llm_analysis(
    company_name: str,
    articles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Call LLM Gateway for unified analysis."""
    if not articles:
        return {
            "enriched_articles": [],
            "summary": {"total": 0, "olumlu": 0, "olumsuz": 0},
            "sentiment_overview": {"trend": "notr", "key_findings": []}
        }

    try:
        response = await http_client.post(
            f"{LLM_GATEWAY_URL}/unified-analysis",
            json={
                "company_name": company_name,
                "articles": articles
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"LLM Gateway error: {response.status_code}")
            return {
                "enriched_articles": articles,
                "summary": {"total": len(articles), "olumlu": 0, "olumsuz": len(articles)},
                "sentiment_overview": {"trend": "negatif", "key_findings": []}
            }

    except Exception as e:
        logger.error(f"LLM Gateway error: {e}")
        return {
            "enriched_articles": articles,
            "summary": {"total": len(articles), "olumlu": 0, "olumsuz": len(articles)},
            "sentiment_overview": {"trend": "negatif", "key_findings": []}
        }


@app.post("/api/news/search", response_model=NewsResponse)
async def search_news(request: NewsRequest):
    """
    FAN-OUT / FAN-IN: 10 kaynaktan paralel haber toplama.

    1. Fan-out: Tüm scraper'lara paralel istek gönder
    2. Collect: Sonuçları topla
    3. Analyze: LLM Gateway ile analiz
    4. Fan-in: Sonuçları birleştir ve döndür
    """
    start = time.time()
    request_id = request.report_id or str(uuid.uuid4())

    logger.info(f"[{request_id}] Starting news search for '{request.company_name}'")

    # =============================================
    # FAN-OUT: TÜM SCRAPERLAR AYNI ANDA!
    # =============================================
    MAX_WAIT_TIME = 540  # 9 dakika (1 dk LLM analizi için buffer)

    tasks = [
        call_scraper(
            source=source,
            url=url,
            company_name=request.company_name,
            max_articles=request.max_articles_per_source,
            request_id=request_id,
            timeout=request.timeout_seconds
        )
        for source, url in SCRAPERS.items()
    ]

    # =============================================
    # COLLECT: asyncio.as_completed ile progressive toplama
    # Timeout olursa o ana kadar toplananlarla devam et
    # =============================================
    all_articles = []
    source_results = []
    sources_completed = 0
    sources_failed = 0
    processed_sources = set()

    try:
        for coro in asyncio.as_completed(tasks, timeout=MAX_WAIT_TIME):
            try:
                result = await coro

                if isinstance(result, Exception):
                    sources_failed += 1
                    source_results.append(SourceResult(
                        source="unknown",
                        status="failed",
                        error=str(result)
                    ))
                    continue

                processed_sources.add(result["source"])
                source_results.append(SourceResult(
                    source=result["source"],
                    status=result["status"],
                    articles=result.get("articles", []),
                    duration_ms=result.get("duration_ms", 0),
                    error=result.get("error")
                ))

                if result["status"] == "success":
                    sources_completed += 1
                    all_articles.extend(result.get("articles", []))
                else:
                    sources_failed += 1

            except Exception as e:
                sources_failed += 1
                source_results.append(SourceResult(
                    source="unknown",
                    status="failed",
                    error=str(e)
                ))

    except asyncio.TimeoutError:
        # 9 dakika doldu - kalan kaynakları timeout olarak işaretle
        remaining = len(SCRAPERS) - len(processed_sources)
        logger.warning(f"[{request_id}] Global timeout! {remaining} kaynak tamamlanamadı, partial results döndürülüyor")

        for source in SCRAPERS.keys():
            if source not in processed_sources:
                sources_failed += 1
                source_results.append(SourceResult(
                    source=source,
                    status="failed",
                    error="Global timeout (9 dakika)"
                ))

    logger.info(
        f"[{request_id}] Scraping complete: "
        f"{sources_completed} success, {sources_failed} failed, "
        f"{len(all_articles)} total articles"
    )

    # =============================================
    # ANALYZE: LLM Gateway ile analiz
    # =============================================
    analysis = await call_llm_analysis(request.company_name, all_articles)

    # Use enriched articles from analysis
    final_articles = analysis.get("enriched_articles", all_articles)

    # =============================================
    # FAN-IN: Sonuçları birleştir
    # =============================================
    duration = time.time() - start

    logger.info(
        f"[{request_id}] Complete in {duration:.2f}s: "
        f"{len(final_articles)} articles analyzed"
    )

    return NewsResponse(
        request_id=request_id,
        company_name=request.company_name,
        total_articles=len(final_articles),
        sources_completed=sources_completed,
        sources_failed=sources_failed,
        articles=final_articles,
        analysis=analysis,
        source_results=source_results,
        duration_seconds=round(duration, 2)
    )


@app.get("/api/news/sources")
async def list_sources():
    """List all configured scraper sources."""
    return {
        "sources": list(SCRAPERS.keys()),
        "total": len(SCRAPERS)
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check - verify connectivity to scrapers and LLM Gateway."""
    scraper_status = {}

    # Check each scraper (non-blocking, just DNS/TCP)
    for source, url in SCRAPERS.items():
        try:
            # Extract host from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname

            # Simple HTTP check with short timeout
            response = await http_client.get(
                url.replace("/scrape", "/health"),
                timeout=2.0
            )
            scraper_status[source] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            scraper_status[source] = "unreachable"

    # Check LLM Gateway
    try:
        response = await http_client.get(
            f"{LLM_GATEWAY_URL}/health",
            timeout=2.0
        )
        llm_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        llm_status = "unreachable"

    # Overall status
    healthy_scrapers = sum(1 for s in scraper_status.values() if s == "healthy")
    overall = "healthy" if healthy_scrapers >= 5 and llm_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall,
        scrapers=scraper_status,
        llm_gateway=llm_status
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "News Orchestrator Service",
        "version": "1.0.0",
        "status": "running",
        "scrapers": len(SCRAPERS)
    }


# WebSocket endpoint for real-time progress (optional)
@app.websocket("/ws/news/{request_id}")
async def news_progress(websocket: WebSocket, request_id: str):
    """Real-time progress updates via WebSocket."""
    await websocket.accept()

    try:
        # Simple progress simulation
        # In production, would use Redis PubSub
        for i, source in enumerate(SCRAPERS.keys()):
            await websocket.send_json({
                "type": "progress",
                "source": source,
                "progress": int((i + 1) / len(SCRAPERS) * 100),
                "status": "processing"
            })
            await asyncio.sleep(0.1)

        await websocket.send_json({
            "type": "complete",
            "progress": 100,
            "status": "done"
        })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
