"""
LLM Gateway Service - Centralized LLM API with connection pooling and batch processing.
Kubernetes microservice that provides unified sentiment analysis.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import httpx
from typing import List, Dict, Optional, Any
import os
import json
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KKB_API_URL = os.getenv("KKB_API_URL", "https://mia.csp.kloudeks.com/v1")
KKB_API_KEY = os.getenv("KKB_API_KEY", "")
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))

# Global HTTP client with connection pooling
http_client: Optional[httpx.AsyncClient] = None

# Rate limiting semaphore
llm_semaphore: Optional[asyncio.Semaphore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - initialize HTTP client on startup."""
    global http_client, llm_semaphore

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=50,
            max_keepalive_connections=20
        )
    )
    llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    logger.info(f"LLM Gateway initialized - Max concurrent: {MAX_CONCURRENT_REQUESTS}")
    yield

    await http_client.aclose()
    logger.info("LLM Gateway shutdown")


app = FastAPI(
    title="LLM Gateway Service",
    description="Centralized LLM API with batch processing for news analysis",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class Article(BaseModel):
    id: Optional[str] = None
    title: str
    text: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


class UnifiedAnalysisRequest(BaseModel):
    company_name: str
    articles: List[Dict[str, Any]]


class ArticleAnalysis(BaseModel):
    id: Optional[str] = None
    title: str
    is_relevant: bool
    relevance_score: float
    sentiment: str  # "olumlu" or "olumsuz"
    key_finding: Optional[str] = None


class UnifiedAnalysisResponse(BaseModel):
    enriched_articles: List[Dict[str, Any]]
    summary: Dict[str, int]
    sentiment_overview: Dict[str, Any]


class RelevanceRequest(BaseModel):
    company_name: str
    article_title: str
    article_text: Optional[str] = None


class RelevanceResponse(BaseModel):
    is_relevant: bool
    confidence: float


class SentimentRequest(BaseModel):
    titles: List[str]


class SentimentResponse(BaseModel):
    sentiments: List[str]


class OCRExtractRequest(BaseModel):
    ocr_text: str
    source_name: str
    company_name: str


class OCRExtractResponse(BaseModel):
    articles: List[Dict[str, Any]]


async def call_llm(
    prompt: str,
    model: str = "gpt-oss-120b",
    temperature: float = 0.1,
    max_tokens: int = 1000
) -> str:
    """Make LLM API call with rate limiting."""
    if not http_client:
        raise HTTPException(503, "HTTP client not initialized")

    async with llm_semaphore:
        try:
            response = await http_client.post(
                f"{KKB_API_URL}/chat/completions",
                headers={"Authorization": f"Bearer {KKB_API_KEY}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )

            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                raise HTTPException(response.status_code, f"LLM API error: {response.text}")

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                logger.warning(f"LLM returned empty content: {result}")
            return content

        except httpx.TimeoutException:
            logger.error("LLM API timeout")
            raise HTTPException(504, "LLM API timeout")
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise HTTPException(500, str(e))


@app.post("/unified-analysis", response_model=UnifiedAnalysisResponse)
async def unified_analysis(request: UnifiedAnalysisRequest):
    """
    Single LLM call for: Relevance + Sentiment + Key Findings.
    Processes articles in batches for efficiency.
    """
    if not request.articles:
        return UnifiedAnalysisResponse(
            enriched_articles=[],
            summary={"total": 0, "olumlu": 0, "olumsuz": 0},
            sentiment_overview={"trend": "notr", "key_findings": []}
        )

    batch_size = 5
    batches = [
        request.articles[i:i+batch_size]
        for i in range(0, len(request.articles), batch_size)
    ]

    async def process_batch(batch: List[Dict], batch_idx: int) -> List[Dict]:
        """Process a batch of articles with single LLM call."""

        # Prepare batch prompt
        articles_json = json.dumps([
            {
                "index": i,
                "title": a.get("title", "")[:200],
                "text": (a.get("text", "") or "")[:500]
            }
            for i, a in enumerate(batch)
        ], ensure_ascii=False, indent=2)

        prompt = f"""Aşağıdaki haberleri "{request.company_name}" firması için analiz et.

Her haber için JSON döndür:
{{
    "index": 0,
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "sentiment": "olumlu" veya "olumsuz",
    "key_finding": "tek cümle özet"
}}

Relevance kriterleri (ESNEK YORUMLA - OCR hataları olabilir):
- Firma adı veya kısaltması geçiyor mu? (örn: "Koç", "KOC", "Koc Holding" vb.)
- Firmanın ana şirketleri veya iştirakleri hakkında mı? (örn: Koç için Ford Otosan, Arçelik, Tüpraş)
- Sektördeki genel gelişmeler firma ile ilişkilendirilebilir mi?
- OCR/yazım hataları olabilir - kısmen benzer isimler de kabul et
- ŞÜPHE DURUMUNDA is_relevant: true VER

Sentiment kriterleri:
- olumlu: İyi haber, başarı, büyüme, anlaşma, ödül, yatırım
- olumsuz: Kötü haber, kriz, zarar, dava, ceza, soruşturma

Haberler:
{articles_json}

Sadece JSON array döndür, açıklama ekleme:"""

        try:
            response = await call_llm(prompt, max_tokens=1500)

            # Parse JSON response
            try:
                # Clean response - find JSON array
                response = response.strip()
                if response.startswith("```"):
                    response = response.split("```")[1]
                    if response.startswith("json"):
                        response = response[4:]
                    response = response.strip()

                analyses = json.loads(response)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for batch {batch_idx}")
                analyses = []

            # Enrich articles with analysis
            enriched = []
            for i, article in enumerate(batch):
                analysis = next(
                    (a for a in analyses if a.get("index") == i),
                    {"is_relevant": True, "relevance_score": 0.5, "sentiment": "olumsuz", "key_finding": ""}
                )

                enriched.append({
                    **article,
                    "is_relevant": analysis.get("is_relevant", True),
                    "relevance_score": analysis.get("relevance_score", 0.5),
                    "sentiment": analysis.get("sentiment", "olumsuz"),
                    "key_finding": analysis.get("key_finding", "")
                })

            return enriched

        except Exception as e:
            logger.error(f"Batch {batch_idx} processing error: {e}")
            # Return with default values
            return [
                {
                    **article,
                    "is_relevant": True,
                    "relevance_score": 0.5,
                    "sentiment": "olumsuz",
                    "key_finding": ""
                }
                for article in batch
            ]

    # Process all batches in parallel
    tasks = [process_batch(batch, i) for i, batch in enumerate(batches)]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine results
    enriched_articles = []
    for result in batch_results:
        if isinstance(result, list):
            enriched_articles.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Batch failed: {result}")

    # NOT: is_relevant filtresini KALDIRDIK - tüm makaleleri döndür
    # Eski kod: relevant = [a for a in enriched_articles if a.get("is_relevant", True)]
    # BUG FIX: LLM OCR metninden firma adını bulamayınca tüm haberleri siliyordu
    relevant = enriched_articles  # Filtresiz - tüm makaleleri al

    # Calculate summary
    total = len(relevant)
    olumlu = sum(1 for a in relevant if a.get("sentiment") == "olumlu")
    olumsuz = total - olumlu

    # Determine trend
    if olumlu > olumsuz:
        trend = "pozitif"
    elif olumsuz > olumlu:
        trend = "negatif"
    else:
        trend = "notr"

    # Collect key findings
    key_findings = [
        a.get("key_finding")
        for a in relevant[:5]
        if a.get("key_finding")
    ]

    return UnifiedAnalysisResponse(
        enriched_articles=relevant,
        summary={"total": total, "olumlu": olumlu, "olumsuz": olumsuz},
        sentiment_overview={
            "trend": trend,
            "key_findings": key_findings
        }
    )


@app.post("/relevance", response_model=RelevanceResponse)
async def check_relevance(request: RelevanceRequest):
    """Check if article is relevant to company."""
    text = request.article_text or request.article_title

    prompt = f"""Bu haber "{request.company_name}" firması hakkında mı?

Başlık: {request.article_title}
Metin: {text[:500]}

Cevap formatı: EVET veya HAYIR - Güven skoru (0.0-1.0)
Örnek: EVET - 0.95

Cevap:"""

    try:
        response = await call_llm(prompt, max_tokens=50)
        response = response.strip().upper()

        is_relevant = "EVET" in response
        confidence = 0.5

        try:
            if "-" in response:
                import re
                conf_match = re.search(r'(\d+\.?\d*)', response.split("-")[1])
                if conf_match:
                    confidence = float(conf_match.group(1))
                    if confidence > 1:
                        confidence = confidence / 100
        except Exception:
            pass

        return RelevanceResponse(is_relevant=is_relevant, confidence=confidence)

    except Exception as e:
        logger.error(f"Relevance check error: {e}")
        return RelevanceResponse(is_relevant=True, confidence=0.5)


@app.post("/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """Batch sentiment analysis for titles."""
    if not request.titles:
        return SentimentResponse(sentiments=[])

    titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(request.titles)])

    prompt = f"""Aşağıdaki haber başlıklarının sentiment'ini analiz et.

Haber Başlıkları:
{titles_text}

Her haber için tek kelime sentiment ver:
- olumlu: İyi haber, olumlu gelişme, başarı, büyüme
- olumsuz: Kötü haber, olumsuz gelişme, zarar, kriz

Cevap formatı (sadece sentiment'ler, satır satır):
1. olumlu
2. olumsuz
...

Cevap:"""

    try:
        response = await call_llm(prompt, max_tokens=200)

        sentiments = []
        valid_sentiments = {"olumlu", "olumsuz"}

        for line in response.strip().split('\n'):
            line = line.strip().lower()
            for sentiment in valid_sentiments:
                if sentiment in line:
                    sentiments.append(sentiment)
                    break

        # Fill missing with default
        while len(sentiments) < len(request.titles):
            sentiments.append("olumsuz")

        return SentimentResponse(sentiments=sentiments)

    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return SentimentResponse(sentiments=["olumsuz"] * len(request.titles))


@app.post("/ocr/extract-news", response_model=OCRExtractResponse)
async def extract_news_from_ocr(request: OCRExtractRequest):
    """OCR metninden haber linklerini ve basliklarini cikar."""

    # BUG FIX: ocr_text None kontrolü
    if not request.ocr_text or len(request.ocr_text.strip()) < 50:
        logger.warning(f"OCR text too short or empty")
        return OCRExtractResponse(articles=[])

    prompt = f"""Bu metin "{request.source_name}" haber sitesinin arama sonuç sayfasından OCR ile çıkarılmıştır.

Lütfen metindeki TÜM haber başlıklarını JSON formatında çıkar:
{{
    "articles": [
        {{"title": "Haber başlığı", "url": "https://..." veya null}},
        ...
    ]
}}

OCR Metni:
{request.ocr_text[:5000]}

Kurallar (ESNEK YORUMLA - OCR hataları olabilir):
- Haber başlığı gibi görünen tüm metinleri çıkar
- OCR hataları olabilir - kısmen okunamayan başlıkları da dahil et
- Başlık uzunsa kısalt ama dahil et
- URL bulunamazsa null yaz
- Maximum 10 haber (daha fazla bul!)
- Türkçe karakterleri düzelt
- "{request.company_name}" ile kısmi eşleşmeler de dahil

ÖNEMLİ: Şüpheli de olsa haber başlıklarını dahil et, filtreleme sonra yapılacak.

Sadece JSON döndür, açıklama ekleme:"""

    try:
        response = await call_llm(prompt, temperature=0.1, max_tokens=2000)

        # BUG FIX: LLM response None kontrolü
        if not response:
            logger.warning(f"[{request.source_name}] LLM returned empty/None response")
            return OCRExtractResponse(articles=[])

        # Parse JSON response
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()

            data = json.loads(response)
            articles = data.get("articles", [])

            # Validate articles (max 10)
            valid_articles = []
            for article in articles[:10]:
                if isinstance(article, dict) and article.get("title"):
                    valid_articles.append({
                        "title": str(article.get("title", ""))[:200],
                        "url": article.get("url")
                    })

            logger.info(f"[{request.source_name}] OCR extracted {len(valid_articles)} article titles")
            return OCRExtractResponse(articles=valid_articles)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OCR LLM response: {e}")
            return OCRExtractResponse(articles=[])

    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        return OCRExtractResponse(articles=[])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api_url": KKB_API_URL,
        "max_concurrent": MAX_CONCURRENT_REQUESTS
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "LLM Gateway Service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
