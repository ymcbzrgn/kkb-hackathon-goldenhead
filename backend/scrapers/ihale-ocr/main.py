"""
Ihale OCR Service - Tesseract OCR ile PDF Okuma Microservice.

K8s microservice olarak PDF'lerden Tesseract OCR ile yapisal veri cikarir.
Multi-pod paralel processing icin optimize edilmis.

Features:
- 4 rotasyon deneme (0, 90, 180, 270 derece)
- Concurrent rotation processing (ThreadPoolExecutor)
- 300 DPI yuksek kalite
- 9 alan cikartma (regex patterns)

Endpoints:
- POST /ocr - PDF'i OCR ile isle
- GET /health - Health check
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import os
import base64
import tempfile
import logging
import re
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DPI = int(os.getenv("OCR_DPI", "300"))
MIN_TEXT_THRESHOLD = int(os.getenv("MIN_TEXT_THRESHOLD", "200"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))  # Paralel rotasyon


class OCRRequest(BaseModel):
    pdf_base64: str
    pdf_id: Optional[str] = None
    gazete_sayi: Optional[str] = None
    gazete_tarih: Optional[str] = None
    request_id: Optional[str] = None


class YapiselVeri(BaseModel):
    yasak_kayit_no: Optional[str] = None
    ihale_kayit_no: Optional[str] = None
    yasaklayan_kurum: Optional[str] = None
    ihale_idaresi: Dict[str, Optional[str]] = {}
    yasakli_kisi: Dict[str, Optional[str]] = {}
    ortaklar: List[Dict[str, Optional[str]]] = []
    ortaklik_bilgileri: Optional[str] = None
    kanun_dayanagi: Optional[str] = None
    yasak_kapsami: Optional[str] = None
    yasak_suresi: Optional[str] = None


class OCRResponse(BaseModel):
    request_id: str
    pdf_id: str
    status: str  # "success" or "failed"
    ham_metin: Optional[str] = None
    yapisal_veri: Optional[YapiselVeri] = None
    okuma_yontemi: str = "Tesseract OCR + Rotasyon"
    rotation_used: int = 0
    duration_ms: int = 0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    tesseract: str
    workers: int


# Regex patterns (mevcut pdf_reader.py'den)
PATTERNS = {
    "yasak_kayit_no": [
        r"YASAKLI\s*KAYIT\s*NO[:\s]*(\d+)",
        r"YASAKLI\s*KAY[IT]T\s*N[O0][:\s]*(\d+)",
    ],
    "ihale_kayit_no": [
        r"(?:IKN|ISKN|[IT]HALE\s*KAYIT\s*N)[:\s/]*(\d{4}/\d+)",
        r"1\.?\s*[IT]HALE\s*KAYIT\s*NUMARASI[^0-9]*(\d{4}/\d+)",
        r"(\d{4}/\d{6,})",
    ],
    "yasaklayan_kurum": [
        r"2\.?\s*YASAKLAMA\s*KARARI\s*VEREN[^A-Z]*([A-Z][A-Za-z\s/]+(?:Bakanl[il]g[il]|BAKANLI[GĞ]I|M[UÜ]d[UÜ]rl[UÜ][gğ][UÜ]))",
        r"(SA[GĞ]LIK\s*BAKANLI[GĞ]I[^,\n]*)",
        r"([A-Z][A-Za-z\s]+BAKANLI[GĞ]I[^,\n]*)",
    ],
    "idare_adi": [
        r"3\.?\s*[IT]HALEY[IT]\s*YAPAN\s*[IT]DAREN[IT]N[^A-Z]*Ad[il][:\s]*([^\n]+)",
        r"Ad[il][:\s]+([A-Z][A-Z\s]+(?:HASTANES[IT]|BA[SŞ]HEK[IT]ML[IT][GĞ][IT]|M[UÜ]D[UÜ]RL[UÜ][GĞ][UÜ]))",
    ],
    "idare_adresi": [
        r"3\.?\s*[IT]HALEY[IT]\s*YAPAN.*?Adres[il][:\s]*([^\n]+)",
        r"Adres[il][:\s]+([A-Za-z0-9\s,./]+(?:Mahallesi|Caddesi|Sokak|No)[^\n]*)",
    ],
    "idare_posta_kodu": [r"Posta\s*Kodu[:\s]*(\d{5})"],
    "idare_il_ilce": [r"[IT]l/[IT]l[cç]e[:\s]*([A-Z]+/[A-Z]+)", r"[IT]l/[IT]l[cç]e[:\s]*([^\n]+)"],
    "idare_tel_kep": [r"Tel-?Kep\s*Adres[il]?[:\s]*([^\n]+)"],
    "idare_eposta": [r"E-?Posta[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"],
    "vergi_no": [
        r"Vergi\s*Kimlik[^0-9]*[:\s]*(\d{3,11})",
        r"M[UÜ]kellefiyet[^0-9]*[:\s]*(\d{3,11})",
        r"Vergi[^0-9]*(\d{10,11})",
        r"V\.?K\.?N\.?[:\s]*(\d{10,11})",
    ],
    "tc_kimlik": [r"T\.?C\.?\s*Kimlik\s*No[:\s]*(\d{11})", r"T\.?C\.?\s*Kimlik[^0-9]*(\d{11})"],
    "pasaport_no": [r"Pasaport\s*No[:\s]*([A-Z0-9]+)"],
    "yasakli_adresi": [r"4\.?\s*[IT]HALELERE\s*KATILMAKTAN.*?Adres[il][:\s]*([^\n]+)"],
    "yasak_suresi": [
        r"9\.?\s*YASAKLAMA\s*S[UÜ]RES[IT][:\s]*(\d+\s*/?\s*(?:YIL|AY|GUN|Y[IT]L))",
        r"YASAKLAMA\s*S[UÜ]RES[IT][:\s]*(\d+\s*/?\s*(?:YIL|AY|G[UÜ]N))",
        r"S[UÜ]RES[IT][:\s]*(\d+)\s*/?\s*(YIL|AY|GUN|Y[IT]L)",
    ],
    "kanun_dayanagi": [r"7\.?\s*YASAKLAMA\s*KANUN\s*DAYANA[GĞ]I[:\s]*([^\n]+)", r"(\d{4}\s*Say[il]+[^,\n]*Kanun[u]?)"],
    "yasak_kapsami": [r"8\.?\s*YASAKLAMA\s*KANUN\s*KAPSAMI[:\s]*([^\n]+)", r"(T[UÜ]m\s*[IT]halelerden)", r"(Belirli\s*[IT]halelerden)"],
    "ortak_adi": [r"5\.?\s*ORTAK\s*B[IT]LG[IT]LER[IT][^A]*Ad[il]/[UÜ]nvan[il][:\s]*([^\n]+)"],
    "ortak_tc": [r"5\.?\s*ORTAK.*?T\.?C\.?\s*Kimlik\s*No[:\s]*(\d{11})"],
    "ortak_vergi_no": [r"5\.?\s*ORTAK.*?Vergi\s*Kimlik[^0-9]*[:\s]*(\d{3,11})"],
    "ortak_adresi": [r"5\.?\s*ORTAK.*?Adres[il][:\s]*([^\n]+)"],
}

FIRMA_PATTERNS = [
    r"Ad[il][:\s]+([A-Z][A-Z\s]+(?:LIMITED|LTD|ANONIM)\s*[SŞ][IT]RKET[IT])",
    r"T[UÜ]ZEL\s*K[IT][SŞ][IT]N[IT]N[^A-Z]*([A-Z][A-Z\s]+(?:LIMITED|LTD|A\.?[SŞ]\.?))",
    r"([A-Z][A-Z\s]+(?:GIDA|KOZMET[IT]K|[IT]N[SŞ]AAT|T[IT]CARET|TEKST[IT]L|METAL|PLAST[IT]K)[A-Z\s]*(?:LIMITED|LTD|[SŞ][IT]RKET[IT]))",
]

# Thread pool for parallel rotation OCR
executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan."""
    logger.info(f"Ihale OCR Service starting (DPI={DPI}, workers={MAX_WORKERS})")
    yield
    executor.shutdown(wait=True)
    logger.info("Ihale OCR Service shutdown")


app = FastAPI(
    title="Ihale OCR Service",
    description="Tesseract OCR ile PDF'den yapisal veri cikartma",
    version="1.0.0",
    lifespan=lifespan
)


def ocr_with_rotation(image, rotation: int) -> tuple:
    """
    Tek bir rotasyon icin OCR yap.
    ThreadPoolExecutor icinde calisir.

    Returns:
        (rotation, text, text_length)
    """
    import pytesseract
    from PIL import Image

    try:
        if rotation > 0:
            rotated = image.rotate(rotation, expand=True)
        else:
            rotated = image

        # Turkce yoksa Ingilizce dene
        text = None
        for lang in ['tur', 'eng']:
            try:
                text = pytesseract.image_to_string(rotated, lang=lang)
                if text and len(text.strip()) > 50:
                    break
            except Exception:
                continue

        return (rotation, text or "", len(text.strip()) if text else 0)

    except Exception as e:
        logger.warning(f"OCR rotation {rotation} error: {e}")
        return (rotation, "", 0)


async def extract_text_with_parallel_rotation(pdf_path: str) -> tuple:
    """
    PDF'den paralel rotasyon ile text cikar.

    4 rotasyon ayni anda calisir (ThreadPoolExecutor).
    En uzun text ureten rotasyon secilir.

    Returns:
        (text, best_rotation)
    """
    from pdf2image import convert_from_path

    logger.info(f"Converting PDF to images (DPI={DPI})...")
    images = convert_from_path(pdf_path, dpi=DPI)

    all_text_parts = []
    overall_best_rotation = 0

    for i, image in enumerate(images):
        logger.info(f"OCR page {i+1}/{len(images)} (parallel rotation)")

        # 4 rotasyonu paralel calistir
        loop = asyncio.get_event_loop()
        rotation_tasks = [
            loop.run_in_executor(executor, ocr_with_rotation, image, rot)
            for rot in [0, 90, 180, 270]
        ]

        results = await asyncio.gather(*rotation_tasks)

        # En iyi sonucu sec
        best_rotation, best_text, best_len = max(results, key=lambda x: x[2])

        if best_text:
            if best_rotation > 0:
                logger.info(f"Page {i+1}: Using {best_rotation}° rotation ({best_len} chars)")
            all_text_parts.append(f"--- Sayfa {i+1} ---\n{best_text}")
            overall_best_rotation = best_rotation

    final_text = "\n\n".join(all_text_parts) if all_text_parts else None
    return (final_text, overall_best_rotation)


def extract_structured_data(text: str) -> Dict[str, Any]:
    """Ham metinden yapisal veri cikar."""
    data = {
        "yasak_kayit_no": None,
        "ihale_kayit_no": None,
        "yasaklayan_kurum": None,
        "ihale_idaresi": {
            "adi": None, "adresi": None, "posta_kodu": None,
            "il_ilce": None, "tel_kep": None, "eposta": None
        },
        "yasakli_kisi": {
            "adi": None, "tc_kimlik": None, "vergi_no": None,
            "pasaport_no": None, "adresi": None
        },
        "ortaklar": [],
        "ortaklik_bilgileri": None,
        "kanun_dayanagi": None,
        "yasak_kapsami": None,
        "yasak_suresi": None
    }

    if not text:
        return data

    text_with_newlines = text
    text_single_line = text.replace('\n', ' ').replace('\r', ' ')

    # Extract all fields using patterns
    def extract_field(patterns, search_text, flags=re.IGNORECASE):
        for pattern in patterns:
            match = re.search(pattern, search_text, flags)
            if match:
                return match.group(1).strip() if match.groups() else match.group(0).strip()
        return None

    # Meta
    data["yasak_kayit_no"] = extract_field(PATTERNS["yasak_kayit_no"], text)
    data["ihale_kayit_no"] = extract_field(PATTERNS["ihale_kayit_no"], text)
    data["yasaklayan_kurum"] = extract_field(PATTERNS["yasaklayan_kurum"], text)

    # Ihale Idaresi
    data["ihale_idaresi"]["adi"] = extract_field(PATTERNS["idare_adi"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    data["ihale_idaresi"]["adresi"] = extract_field(PATTERNS["idare_adresi"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    data["ihale_idaresi"]["posta_kodu"] = extract_field(PATTERNS["idare_posta_kodu"], text)
    data["ihale_idaresi"]["il_ilce"] = extract_field(PATTERNS["idare_il_ilce"], text)
    data["ihale_idaresi"]["tel_kep"] = extract_field(PATTERNS["idare_tel_kep"], text_with_newlines)
    data["ihale_idaresi"]["eposta"] = extract_field(PATTERNS["idare_eposta"], text)

    # Yasakli Kisi
    data["yasakli_kisi"]["vergi_no"] = extract_field(PATTERNS["vergi_no"], text)
    data["yasakli_kisi"]["tc_kimlik"] = extract_field(PATTERNS["tc_kimlik"], text)
    pasaport = extract_field(PATTERNS["pasaport_no"], text)
    if pasaport and pasaport.upper() not in ['NO', 'YOK', '-']:
        data["yasakli_kisi"]["pasaport_no"] = pasaport
    data["yasakli_kisi"]["adresi"] = extract_field(PATTERNS["yasakli_adresi"], text_with_newlines, re.IGNORECASE | re.DOTALL)

    # Firma Adi
    for pattern in FIRMA_PATTERNS:
        match = re.search(pattern, text)
        if match:
            firma_adi = match.group(1).strip()
            if len(firma_adi) > 10:
                data["yasakli_kisi"]["adi"] = firma_adi
                break

    # Ortaklar
    ortak = {}
    ortak["adi"] = extract_field(PATTERNS["ortak_adi"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    ortak["tc_kimlik"] = extract_field(PATTERNS["ortak_tc"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    ortak["vergi_no"] = extract_field(PATTERNS["ortak_vergi_no"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    ortak["adresi"] = extract_field(PATTERNS["ortak_adresi"], text_with_newlines, re.IGNORECASE | re.DOTALL)
    if ortak.get("adi"):
        data["ortaklar"].append(ortak)

    # Diger alanlar
    data["kanun_dayanagi"] = extract_field(PATTERNS["kanun_dayanagi"], text)
    data["yasak_kapsami"] = extract_field(PATTERNS["yasak_kapsami"], text)

    # Yasak Suresi
    for pattern in PATTERNS["yasak_suresi"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                data["yasak_suresi"] = f"{match.group(1)} / {match.group(2).upper()}"
            else:
                data["yasak_suresi"] = match.group(1).strip()
            break

    return data


@app.post("/ocr", response_model=OCRResponse)
async def process_pdf(request: OCRRequest):
    """
    PDF'i OCR ile isle ve yapisal veri cikar.

    Input: PDF base64 encoded
    Output: Yapisal veri (9 alan)
    """
    import time
    import uuid

    start = time.time()
    request_id = request.request_id or str(uuid.uuid4())
    pdf_id = request.pdf_id or str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] Processing PDF {pdf_id}")

    try:
        # Base64 decode
        pdf_bytes = base64.b64decode(request.pdf_base64)

        # Temp file olustur
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            # Paralel rotasyon ile OCR
            text, best_rotation = await extract_text_with_parallel_rotation(tmp_path)

            if not text or len(text.strip()) < MIN_TEXT_THRESHOLD:
                return OCRResponse(
                    request_id=request_id,
                    pdf_id=pdf_id,
                    status="failed",
                    error=f"OCR text too short ({len(text) if text else 0} chars)",
                    duration_ms=int((time.time() - start) * 1000)
                )

            # Yapisal veri cikar
            yapisal = extract_structured_data(text)

            duration_ms = int((time.time() - start) * 1000)
            logger.info(f"[{request_id}] OCR complete: {len(text)} chars, rotation={best_rotation}°, {duration_ms}ms")

            return OCRResponse(
                request_id=request_id,
                pdf_id=pdf_id,
                status="success",
                ham_metin=text,
                yapisal_veri=YapiselVeri(**yapisal),
                rotation_used=best_rotation,
                duration_ms=duration_ms
            )

        finally:
            # Cleanup
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"[{request_id}] OCR error: {e}")
        return OCRResponse(
            request_id=request_id,
            pdf_id=pdf_id,
            status="failed",
            error=str(e),
            duration_ms=int((time.time() - start) * 1000)
        )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    # Tesseract check
    tesseract_status = "unknown"
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        tesseract_status = "ready"
    except Exception:
        tesseract_status = "not_found"

    return HealthResponse(
        status="healthy" if tesseract_status == "ready" else "degraded",
        tesseract=tesseract_status,
        workers=MAX_WORKERS
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Ihale OCR Service",
        "version": "1.0.0",
        "dpi": DPI,
        "workers": MAX_WORKERS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
