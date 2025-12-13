"""
TSG Scraper K8s Microservice
Ticaret Sicili Gazetesi - FastAPI + Playwright + Tesseract OCR

Mevcut TSG Agent kodunu K8s microservice olarak sarmalayan FastAPI uygulamasi.
"""
import asyncio
import base64
import io
import json
import os
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import Counter

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from playwright.async_api import async_playwright, Page, Browser

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tsg-scraper")

# FastAPI app
app = FastAPI(title="TSG Scraper K8s", version="1.0.0")

# Environment variables
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "30000"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TSG_EMAIL = os.getenv("TSG_EMAIL", "yamacbezirgan@gmail.com")
TSG_PASSWORD = os.getenv("TSG_PASSWORD", "wisvar-wovwoj-7tagNe")
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8082")
DEBUG_DIR = Path("/tmp/tsg_debug")
DEBUG_DIR.mkdir(exist_ok=True)

# TSG System Prompt for LLM
TSG_SYSTEM_PROMPT = """Sen bir Ticaret Sicili Gazetesi (TSG) analiz uzmanisin.

GOREV:
Verilen TSG ilanindan sirket bilgilerini cikar ve JSON formatinda dondur.

ZORUNLU ALANLAR (8 Baslik):
1. Firma Unvani: Sirketin tam resmi adi
2. Tescil Konusu: Islem turu (kurulus, sermaye artirimi, yonetici degisikligi vb.)
3. Mersis Numarasi: 16 haneli numara (varsa)
4. Yoneticiler: Yonetim kurulu uyeleri / mudur isimleri (liste)
5. Imza Yetkilisi: Sirketi temsile yetkili kisi(ler)
6. Sermaye: Sirket sermayesi (ornegin: "10.000.000 TL")
7. Kurulus_Tarihi: Sirketin kurulus tarihi (ornegin: "15.03.2018")
8. Faaliyet_Konusu: Sirketin faaliyet alani (kisa ozet)

KURALLAR:
- SADECE metinde ACIKCA yazan bilgileri cikar
- Tahmin yapma, varsayimda bulunma!
- Bulunamayan alanlar icin null dondur
- Turkce karakterleri dogru kullan

CIKTI FORMATI:
Sadece JSON dondur, aciklama yapma!

{
    "Firma Unvani": "string veya null",
    "Tescil Konusu": "string veya null",
    "Mersis Numarasi": "string veya null",
    "Yoneticiler": ["isim1", "isim2"] veya null,
    "Imza Yetkilisi": "string veya null",
    "Sermaye": "string veya null",
    "Kurulus_Tarihi": "string veya null",
    "Faaliyet_Konusu": "string veya null"
}"""


# ============== REQUEST/RESPONSE MODELS ==============

class TSGRequest(BaseModel):
    company_name: str
    request_id: Optional[str] = None


class GazetteBilgisi(BaseModel):
    gazete_no: Optional[str] = None
    tarih: Optional[str] = None
    ilan_tipi: Optional[str] = None
    screenshot_base64: Optional[str] = None
    pdf_base64: Optional[str] = None
    detay_url: Optional[str] = None


class YapilandirilmisVeri(BaseModel):
    firma_unvani: Optional[str] = None
    tescil_konusu: Optional[str] = None
    mersis_numarasi: Optional[str] = None
    yoneticiler: Optional[List[str]] = None
    imza_yetkilisi: Optional[str] = None
    sermaye: Optional[str] = None
    kurulus_tarihi: Optional[str] = None
    faaliyet_konusu: Optional[str] = None


class TSGSonuc(BaseModel):
    toplam_ilan: int = 0
    secilen_ilan_index: int = 0
    gazete_bilgisi: Optional[GazetteBilgisi] = None
    yapilandirilmis_veri: Optional[YapilandirilmisVeri] = None
    sicil_bilgisi: Optional[Dict[str, str]] = None


class TSGResponse(BaseModel):
    request_id: Optional[str] = None
    status: str  # "completed" | "failed" | "not_found"
    firma_adi: str
    tsg_sonuc: Optional[TSGSonuc] = None
    summary: Optional[str] = None
    key_findings: List[str] = []
    warning_flags: List[str] = []
    duration_seconds: float = 0.0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    browser_ready: bool
    timestamp: str


# ============== CAPTCHA OCR ==============

class CaptchaOCR:
    """TSG CAPTCHA icin optimize edilmis OCR."""

    SCALE_FACTOR = 3
    BLUR_RADIUS = 0.5
    MIN_CAPTCHA_LEN = 3
    MAX_CAPTCHA_LEN = 6

    @classmethod
    def _otsu_threshold(cls, arr: np.ndarray) -> int:
        """Otsu threshold hesapla"""
        hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 256))
        total = arr.size
        sum_total = np.dot(np.arange(256), hist)

        sum_bg, weight_bg = 0.0, 0
        max_var, threshold = 0.0, 0

        for t in range(256):
            weight_bg += hist[t]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break
            sum_bg += t * hist[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg
            var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if var_between > max_var:
                max_var = var_between
                threshold = t
        return threshold

    @classmethod
    def _preprocess_otsu(cls, image_bytes: bytes) -> Image.Image:
        """Otsu threshold ile preprocessing"""
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)
        gray = ImageOps.grayscale(img)
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=cls.BLUR_RADIUS))
        arr = np.array(blurred)
        threshold = cls._otsu_threshold(arr)
        binary = ((arr > threshold) * 255).astype(np.uint8)
        return Image.fromarray(binary)

    @classmethod
    def _preprocess_fixed(cls, image_bytes: bytes, threshold: int) -> Image.Image:
        """Sabit threshold ile preprocessing"""
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)
        gray = ImageOps.grayscale(img)
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=cls.BLUR_RADIUS))
        arr = np.array(blurred)
        binary = ((arr > threshold) * 255).astype(np.uint8)
        return Image.fromarray(binary)

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """OCR sonucunu temizle"""
        text = re.sub(r'[^A-Za-z0-9]', '', text)
        return text.upper()

    @classmethod
    def _is_valid_captcha(cls, text: str) -> bool:
        """CAPTCHA gecerli mi kontrol et"""
        return cls.MIN_CAPTCHA_LEN <= len(text) <= cls.MAX_CAPTCHA_LEN

    @classmethod
    def read_captcha(cls, image_bytes: bytes) -> Optional[str]:
        """CAPTCHA oku - coklu yontem dene"""
        results = []
        psm_modes = [7, 8, 13, 6]
        thresholds = [100, 120, 140, 160]

        # Otsu ile dene
        for psm in psm_modes:
            try:
                img = cls._preprocess_otsu(image_bytes)
                config = f"--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                text = pytesseract.image_to_string(img, config=config)
                cleaned = cls._clean_text(text)
                if cls._is_valid_captcha(cleaned):
                    results.append(cleaned)
            except Exception as e:
                logger.warning(f"Otsu PSM {psm} hatasi: {e}")

        # Sabit threshold ile dene
        for threshold in thresholds:
            for psm in psm_modes[:2]:
                try:
                    img = cls._preprocess_fixed(image_bytes, threshold)
                    config = f"--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    text = pytesseract.image_to_string(img, config=config)
                    cleaned = cls._clean_text(text)
                    if cls._is_valid_captcha(cleaned):
                        results.append(cleaned)
                except Exception as e:
                    pass

        if not results:
            logger.warning("CAPTCHA okunamadi")
            return None

        # En cok tekrar eden sonucu sec
        counter = Counter(results)
        best, count = counter.most_common(1)[0]
        logger.info(f"CAPTCHA sonucu: {best} (guven: {count}/{len(results)})")
        return best


# ============== BROWSER POOL ==============

class BrowserPool:
    """Singleton browser pool for K8s"""

    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None

    @classmethod
    async def get_instance(cls) -> "BrowserPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_context(self):
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                logger.info("Browser not connected, initializing...")
                await self._cleanup_browser()
                await self._init_browser()

            context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="tr-TR",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )
            return context

    async def _init_browser(self):
        """Initialize Playwright browser"""
        logger.info("Starting Playwright browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--single-process",
            ]
        )
        logger.info("Browser started successfully")

    async def _cleanup_browser(self):
        """Cleanup browser resources"""
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self._browser = None

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error stopping playwright: {e}")
        finally:
            self._playwright = None

    def is_ready(self) -> bool:
        return self._browser is not None and self._browser.is_connected()


# ============== TSG SCRAPER ==============

class TSGScraper:
    """TSG Web Scraper - Playwright based"""

    BASE_URL = "https://www.ticaretsicil.gov.tr"

    def __init__(self, page: Page):
        self.page = page
        self.logged_in = False

    async def _save_debug_screenshot(self, name: str):
        """Debug icin screenshot kaydet"""
        try:
            path = DEBUG_DIR / f"{name}_{int(time.time())}.png"
            await self.page.screenshot(path=str(path))
            logger.debug(f"Screenshot: {path}")
        except Exception as e:
            logger.warning(f"Screenshot hatasi: {e}")

    async def login(self, max_retries: int = MAX_RETRIES) -> bool:
        """TSG'ye login yap"""
        logger.info("TSG Login basliyor...")

        for attempt in range(max_retries):
            try:
                logger.info(f"Login denemesi {attempt + 1}/{max_retries}")

                # Ana sayfaya git
                await self.page.goto(self.BASE_URL, wait_until="networkidle")
                await asyncio.sleep(2)
                await self._save_debug_screenshot(f"home_{attempt}")

                # Login butonuna tikla
                login_btn = await self.page.query_selector("a:has-text('GİRİŞ'), a[href*='giris'], .login-btn")
                if login_btn:
                    await login_btn.click()
                    await asyncio.sleep(2)
                    logger.info("Login butonu tiklandi")

                await self._save_debug_screenshot(f"login_modal_{attempt}")

                # Form doldur
                filled = await self._fill_login_form()
                if not filled:
                    logger.warning("Form doldurulamadi")
                    continue

                # Login butonuna tikla
                await self._click_login_button()
                await asyncio.sleep(3)

                await self._save_debug_screenshot(f"after_login_{attempt}")

                # Login basarili mi kontrol et
                if await self._check_login_success():
                    logger.info("LOGIN BASARILI!")
                    self.logged_in = True
                    return True
                else:
                    logger.warning("Login basarisiz, tekrar deneniyor...")
                    await self.page.reload()
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Login hatasi: {e}")
                await asyncio.sleep(2)

        logger.error("TUM LOGIN DENEMELERI BASARISIZ")
        return False

    async def _fill_login_form(self) -> bool:
        """Login formunu doldur"""
        try:
            # Email
            email_selectors = [
                "input[placeholder*='Posta']",
                "input[placeholder*='posta']",
                "input[placeholder*='mail']",
                "input[type='email']",
                "input[name*='mail']",
            ]

            email_filled = False
            for selector in email_selectors:
                try:
                    fields = await self.page.query_selector_all(selector)
                    for field in fields:
                        if await field.is_visible():
                            await field.fill("")
                            await field.type(TSG_EMAIL, delay=50)
                            email_filled = True
                            logger.info(f"Email dolduruldu: {selector}")
                            break
                    if email_filled:
                        break
                except:
                    continue

            # Password
            password_selectors = [
                "input[type='password']",
                "input[placeholder*='ifre']",
                "input[name*='password']",
            ]

            password_filled = False
            for selector in password_selectors:
                try:
                    fields = await self.page.query_selector_all(selector)
                    for field in fields:
                        if await field.is_visible():
                            await field.fill("")
                            await field.type(TSG_PASSWORD, delay=50)
                            password_filled = True
                            logger.info(f"Password dolduruldu: {selector}")
                            break
                    if password_filled:
                        break
                except:
                    continue

            # CAPTCHA varsa coz
            await self._solve_captcha_if_present()

            return email_filled and password_filled

        except Exception as e:
            logger.error(f"Form doldurma hatasi: {e}")
            return False

    async def _solve_captcha_if_present(self):
        """CAPTCHA varsa coz"""
        try:
            captcha_img = await self.page.query_selector("img[src*='captcha'], img[id*='captcha'], .captcha-image")
            if captcha_img:
                logger.info("CAPTCHA bulundu, cozuluyor...")

                # Screenshot al
                img_bytes = await captcha_img.screenshot()

                # OCR ile coz
                captcha_text = CaptchaOCR.read_captcha(img_bytes)

                if captcha_text:
                    # CAPTCHA input'una yaz
                    captcha_input = await self.page.query_selector(
                        "input[name*='captcha'], input[id*='captcha'], input[placeholder*='Güvenlik']"
                    )
                    if captcha_input:
                        await captcha_input.fill(captcha_text)
                        logger.info(f"CAPTCHA girildi: {captcha_text}")
        except Exception as e:
            logger.warning(f"CAPTCHA cozme hatasi: {e}")

    async def _click_login_button(self):
        """Login butonuna tikla"""
        try:
            login_buttons = [
                "button:has-text('GİRİŞ')",
                "button:has-text('Giriş')",
                "input[type='submit']",
                "button[type='submit']",
                ".login-submit",
            ]

            for selector in login_buttons:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        logger.info(f"Login butonuna tiklandi: {selector}")
                        return
                except:
                    continue
        except Exception as e:
            logger.error(f"Login butonu tiklanamadi: {e}")

    async def _check_login_success(self) -> bool:
        """Login basarili mi kontrol et"""
        try:
            # Basarili login sonrasi olabilecek elementler
            success_indicators = [
                "a:has-text('ÇIKIŞ')",
                "a:has-text('Çıkış')",
                ".user-menu",
                ".logout-btn",
                "a[href*='cikis']",
            ]

            for selector in success_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        return True
                except:
                    continue

            # URL kontrol
            current_url = self.page.url
            if "dashboard" in current_url or "panel" in current_url:
                return True

            return False
        except Exception as e:
            logger.error(f"Login kontrol hatasi: {e}")
            return False

    async def search_company(self, company_name: str, city: str = "ISTANBUL") -> List[Dict]:
        """Firma ara ve ilanlari getir"""
        logger.info(f"Firma aranıyor: {company_name} - Sehir: {city}")

        try:
            # Ilan arama sayfasina git
            search_url = f"{self.BASE_URL}/view/hizlierisim/ilangoruntuleme.php"
            await self.page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(2)

            await self._save_debug_screenshot("search_page")

            # Sehir sec
            await self._select_city(city)

            # Firma adi gir
            search_input = await self.page.query_selector(
                "input[name*='unvan'], input[placeholder*='Firma'], input[id*='unvan']"
            )
            if search_input:
                await search_input.fill(company_name)
                logger.info(f"Firma adi girildi: {company_name}")

            # Ara butonuna tikla
            search_btn = await self.page.query_selector(
                "button:has-text('Ara'), input[value*='Ara'], button[type='submit']"
            )
            if search_btn:
                await search_btn.click()
                await asyncio.sleep(3)

            await self._save_debug_screenshot("search_results")

            # Sonuclari parse et
            ilanlar = await self._parse_search_results()
            logger.info(f"Bulunan ilan sayisi: {len(ilanlar)}")

            return ilanlar

        except Exception as e:
            logger.error(f"Arama hatasi: {e}")
            return []

    async def _select_city(self, city: str):
        """Sehir sec"""
        try:
            city_select = await self.page.query_selector(
                "select[name*='sehir'], select[id*='sehir'], select[name*='il']"
            )
            if city_select:
                await city_select.select_option(label=city)
                logger.info(f"Sehir secildi: {city}")
                await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Sehir secme hatasi: {e}")

    async def _parse_search_results(self) -> List[Dict]:
        """Arama sonuclarini parse et"""
        ilanlar = []

        try:
            # Tablo satirlarini bul
            rows = await self.page.query_selector_all("table tbody tr, .ilan-row, .result-row")

            for i, row in enumerate(rows):
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 4:
                        ilan = {
                            "index": i,
                            "gazete_no": await self._get_cell_text(cells[0]) if len(cells) > 0 else "",
                            "tarih": await self._get_cell_text(cells[1]) if len(cells) > 1 else "",
                            "unvan": await self._get_cell_text(cells[2]) if len(cells) > 2 else "",
                            "ilan_tipi": await self._get_cell_text(cells[3]) if len(cells) > 3 else "",
                            "sicil_no": await self._get_cell_text(cells[4]) if len(cells) > 4 else "",
                            "sicil_mudurlugu": await self._get_cell_text(cells[5]) if len(cells) > 5 else "",
                        }

                        # Detay linki
                        link = await row.query_selector("a[href*='detay'], a[href*='goruntule']")
                        if link:
                            ilan["detay_url"] = await link.get_attribute("href")

                        ilanlar.append(ilan)
                except Exception as e:
                    logger.warning(f"Satir parse hatasi: {e}")
                    continue

        except Exception as e:
            logger.error(f"Sonuc parse hatasi: {e}")

        return ilanlar

    async def _get_cell_text(self, cell) -> str:
        """Hucre metnini al"""
        try:
            text = await cell.inner_text()
            return text.strip() if text else ""
        except:
            return ""

    async def download_ilan_pdf(self, ilan: Dict) -> Optional[bytes]:
        """Ilan PDF'ini indir"""
        try:
            detay_url = ilan.get("detay_url")
            if not detay_url:
                logger.warning("Detay URL bulunamadi")
                return None

            if not detay_url.startswith("http"):
                detay_url = f"{self.BASE_URL}{detay_url}"

            logger.info(f"Detay sayfasina gidiliyor: {detay_url}")
            await self.page.goto(detay_url, wait_until="networkidle")
            await asyncio.sleep(2)

            await self._save_debug_screenshot("ilan_detay")

            # PDF linkini bul ve indir
            pdf_link = await self.page.query_selector("a[href*='.pdf'], a:has-text('PDF'), .pdf-download")
            if pdf_link:
                pdf_url = await pdf_link.get_attribute("href")
                if pdf_url:
                    if not pdf_url.startswith("http"):
                        pdf_url = f"{self.BASE_URL}{pdf_url}"

                    # PDF indir
                    async with httpx.AsyncClient() as client:
                        response = await client.get(pdf_url, timeout=30)
                        if response.status_code == 200:
                            logger.info("PDF indirildi")
                            return response.content

            # PDF yoksa screenshot al
            logger.info("PDF bulunamadi, screenshot aliniyor...")
            screenshot = await self.page.screenshot(full_page=True)
            return screenshot

        except Exception as e:
            logger.error(f"PDF indirme hatasi: {e}")
            return None

    async def get_page_screenshot(self) -> Optional[bytes]:
        """Mevcut sayfanin screenshot'ini al"""
        try:
            return await self.page.screenshot(full_page=True)
        except Exception as e:
            logger.error(f"Screenshot hatasi: {e}")
            return None


# ============== LLM CLIENT ==============

async def call_llm_for_extraction(text: str) -> Optional[Dict]:
    """LLM Gateway'i cagirarak TSG verisini cikar"""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{LLM_GATEWAY_URL}/api/llm/chat",
                json={
                    "messages": [
                        {"role": "system", "content": TSG_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Bu TSG ilanini analiz et:\n\n{text}"}
                    ],
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "")

                # JSON parse et
                try:
                    # JSON blogu bul
                    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse hatasi: {e}")

    except Exception as e:
        logger.error(f"LLM cagri hatasi: {e}")

    return None


# ============== MAIN SEARCH FUNCTION ==============

async def search_tsg(company_name: str, request_id: Optional[str] = None) -> TSGResponse:
    """Ana TSG arama fonksiyonu"""
    start_time = time.time()

    try:
        # Browser context al
        pool = await BrowserPool.get_instance()
        context = await pool.get_context()
        page = await context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT)

        try:
            scraper = TSGScraper(page)

            # Login
            if not await scraper.login():
                return TSGResponse(
                    request_id=request_id,
                    status="failed",
                    firma_adi=company_name,
                    error="TSG login basarisiz",
                    duration_seconds=time.time() - start_time
                )

            # Firma ara
            ilanlar = await scraper.search_company(company_name)

            if not ilanlar:
                return TSGResponse(
                    request_id=request_id,
                    status="not_found",
                    firma_adi=company_name,
                    summary=f"{company_name} icin TSG'de ilan bulunamadi",
                    duration_seconds=time.time() - start_time
                )

            # Ilk ilani sec (veya en uygun olani)
            selected_ilan = ilanlar[0]

            # Kurulus/Tescil ilanlarini onceliklendir
            for ilan in ilanlar:
                ilan_tipi = ilan.get("ilan_tipi", "").lower()
                if "kurulus" in ilan_tipi or "tescil" in ilan_tipi:
                    selected_ilan = ilan
                    break

            # PDF/Screenshot indir
            pdf_data = await scraper.download_ilan_pdf(selected_ilan)
            screenshot = await scraper.get_page_screenshot()

            # LLM ile veri cikar (eger PDF/screenshot varsa)
            yapilandirilmis_veri = None
            if pdf_data:
                # OCR ile text cikar (basit)
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                        text = ""
                        for page_obj in pdf.pages:
                            text += page_obj.extract_text() or ""

                        if text:
                            extracted = await call_llm_for_extraction(text)
                            if extracted:
                                yapilandirilmis_veri = YapilandirilmisVeri(
                                    firma_unvani=extracted.get("Firma Unvani"),
                                    tescil_konusu=extracted.get("Tescil Konusu"),
                                    mersis_numarasi=extracted.get("Mersis Numarasi"),
                                    yoneticiler=extracted.get("Yoneticiler"),
                                    imza_yetkilisi=extracted.get("Imza Yetkilisi"),
                                    sermaye=extracted.get("Sermaye"),
                                    kurulus_tarihi=extracted.get("Kurulus_Tarihi"),
                                    faaliyet_konusu=extracted.get("Faaliyet_Konusu"),
                                )
                except Exception as e:
                    logger.warning(f"PDF OCR hatasi: {e}")

            # Response olustur
            tsg_sonuc = TSGSonuc(
                toplam_ilan=len(ilanlar),
                secilen_ilan_index=selected_ilan.get("index", 0),
                gazete_bilgisi=GazetteBilgisi(
                    gazete_no=selected_ilan.get("gazete_no"),
                    tarih=selected_ilan.get("tarih"),
                    ilan_tipi=selected_ilan.get("ilan_tipi"),
                    screenshot_base64=base64.b64encode(screenshot).decode() if screenshot else None,
                    pdf_base64=base64.b64encode(pdf_data).decode() if pdf_data else None,
                    detay_url=selected_ilan.get("detay_url"),
                ),
                yapilandirilmis_veri=yapilandirilmis_veri,
                sicil_bilgisi={
                    "sicil_no": selected_ilan.get("sicil_no", ""),
                    "sicil_mudurlugu": selected_ilan.get("sicil_mudurlugu", ""),
                }
            )

            # Key findings
            key_findings = []
            if yapilandirilmis_veri:
                if yapilandirilmis_veri.firma_unvani:
                    key_findings.append(f"Firma: {yapilandirilmis_veri.firma_unvani}")
                if yapilandirilmis_veri.tescil_konusu:
                    key_findings.append(f"Tescil: {yapilandirilmis_veri.tescil_konusu}")
                if yapilandirilmis_veri.sermaye:
                    key_findings.append(f"Sermaye: {yapilandirilmis_veri.sermaye}")

            return TSGResponse(
                request_id=request_id,
                status="completed",
                firma_adi=company_name,
                tsg_sonuc=tsg_sonuc,
                summary=f"{company_name} icin {len(ilanlar)} ilan bulundu. Gazete No: {selected_ilan.get('gazete_no', 'N/A')}",
                key_findings=key_findings,
                warning_flags=[],
                duration_seconds=time.time() - start_time
            )

        finally:
            await context.close()

    except Exception as e:
        logger.error(f"TSG arama hatasi: {e}")
        return TSGResponse(
            request_id=request_id,
            status="failed",
            firma_adi=company_name,
            error=str(e),
            duration_seconds=time.time() - start_time
        )


# ============== API ENDPOINTS ==============

@app.get("/", response_model=dict)
async def root():
    return {
        "service": "TSG Scraper K8s",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    pool = await BrowserPool.get_instance()
    return HealthResponse(
        status="healthy",
        browser_ready=pool.is_ready(),
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/tsg/search", response_model=TSGResponse)
async def search_endpoint(request: TSGRequest):
    """TSG arama endpoint'i"""
    logger.info(f"TSG arama istegi: {request.company_name}")

    result = await search_tsg(
        company_name=request.company_name,
        request_id=request.request_id
    )

    return result


# ============== MAIN ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
