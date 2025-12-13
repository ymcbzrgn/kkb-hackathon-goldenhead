"""
TSG Scraper v3 - Vision AI ile CAPTCHA Cozme + Otomatik Login
Playwright ile web scraping

MOCK DATA YOK - Sadece gercek veri!
"""
from playwright.async_api import async_playwright, Page, Browser
import asyncio
import base64
from typing import List, Dict, Optional
import json
from pathlib import Path

# Vision LLM kaldirildi - Tesseract OCR kullaniliyor
from app.agents.tsg.captcha import CaptchaOCR
from app.agents.tsg.logger import log, step, success, error, warn, debug, Timer, with_timeout


class TSGScraper:
    """
    Ticaret Sicili Gazetesi Scraper v3 - Agentic AI.

    Strateji:
    1. Playwright ile headless Chrome
    2. Vision AI ile CAPTCHA coz
    3. Otomatik login
    4. Veri bulunamazsa BOS dondur (MOCK YOK!)
    """

    BASE_URL = "https://www.ticaretsicil.gov.tr"

    # TSG Hesap Bilgileri
    EMAIL = "yamacbezirgan@gmail.com"
    PASSWORD = "wisvar-wovwoj-7tagNe"

    # Debug icin screenshot kaydet
    DEBUG_DIR = Path("/tmp/tsg_debug")

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.logged_in = False

        # Debug klasoru olustur
        self.DEBUG_DIR.mkdir(exist_ok=True)

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, *args):
        await self._close_browser()

    async def _init_browser(self):
        """Playwright browser baslat"""
        log("Browser baslatiliyor...")
        try:
            self.playwright = await async_playwright().start()
            debug("Playwright engine basladi")

            # Chromium kullan
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]
            )

            # Context olustur
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="tr-TR",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )

            self.page = await context.new_page()
            self.page.set_default_timeout(30000)

            success("Browser baslatildi")

        except Exception as e:
            error(f"Playwright baslatilamadi: {e}")
            raise

    async def login(self, max_retries: int = 3) -> bool:
        """
        TSG'ye login yap (Modal form - CAPTCHA yok).

        Args:
            max_retries: Maksimum deneme sayisi

        Returns:
            bool: Login basarili mi?
        """
        step("LOGIN BASLIYOR")
        for attempt in range(max_retries):
            try:
                log(f"Login denemesi {attempt + 1}/{max_retries}")

                # Ana sayfaya git
                log(f"Ana sayfaya gidiliyor: {self.BASE_URL}")
                await self.page.goto(self.BASE_URL, wait_until="networkidle")
                await asyncio.sleep(2)

                # Debug screenshot
                await self._save_debug_screenshot(f"home_page_{attempt}")

                # Login butonuna tikla (sag ustteki GİRİŞ)
                login_btn = await self.page.query_selector("a:has-text('GİRİŞ'), a[href*='giris'], .login-btn")
                if login_btn:
                    await login_btn.click()
                    await asyncio.sleep(2)
                    log("Login butonuna tiklandi, modal aciliyor...")

                # Debug screenshot - modal acik
                await self._save_debug_screenshot(f"login_modal_{attempt}")

                # Modal formunu doldur (CAPTCHA olmadan)
                filled = await self._fill_modal_login_form()
                if not filled:
                    warn("Modal form doldurulamadi")
                    # Alternatif: Direkt URL ile dene
                    await self.page.goto(f"{self.BASE_URL}/view/hizlierisim/ilangoruntuleme.php")
                    await asyncio.sleep(2)
                    filled = await self._fill_modal_login_form()
                    if not filled:
                        continue

                # GİRİŞ butonuna tikla (modal icindeki)
                await self._click_modal_login_button()
                await asyncio.sleep(3)

                # Debug screenshot
                await self._save_debug_screenshot(f"after_login_{attempt}")

                # Login basarili mi kontrol et
                if await self._check_login_success():
                    success("LOGIN BASARILI!")
                    self.logged_in = True
                    step("LOGIN TAMAMLANDI")
                    return True
                else:
                    warn("Login basarisiz, tekrar deneniyor...")
                    await self.page.reload()
                    await asyncio.sleep(2)

            except Exception as e:
                error(f"Login hatasi: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(2)

        error("TUM LOGIN DENEMELERI BASARISIZ")
        return False

    async def _fill_modal_login_form(self) -> bool:
        """Modal login formunu doldur (CAPTCHA dahil - Vision AI ile)"""
        log("Modal form dolduruluyor...")
        try:
            # Modal/popup icerisindeki form alanlarini bul
            # E-Posta alani
            email_selectors = [
                "input[placeholder*='Posta']",
                "input[placeholder*='posta']",
                "input[placeholder*='mail']",
                "input[type='email']",
                "input[name*='mail']",
                "input[name*='Mail']",
                "input[id*='mail']",
                ".modal input[type='text']",
                ".popup input[type='text']",
                "form input[type='text']:first-of-type",
            ]

            email_filled = False
            for selector in email_selectors:
                try:
                    fields = await self.page.query_selector_all(selector)
                    for field in fields:
                        if await field.is_visible():
                            await field.fill("")
                            await field.type(self.EMAIL, delay=50)
                            email_filled = True
                            log(f"Email dolduruldu: {selector}")
                            break
                    if email_filled:
                        break
                except:
                    continue

            # Sifre alani
            password_selectors = [
                "input[type='password']",
                "input[placeholder*='ifre']",
                "input[placeholder*='Şifre']",
                "input[name*='ifre']",
                "input[name*='pass']",
            ]

            password_filled = False
            for selector in password_selectors:
                try:
                    field = await self.page.query_selector(selector)
                    if field and await field.is_visible():
                        await field.fill("")
                        await field.type(self.PASSWORD, delay=50)
                        password_filled = True
                        log(f"Sifre dolduruldu: {selector}")
                        break
                except:
                    continue

            # CAPTCHA - Vision AI ile coz
            captcha_filled = await self._solve_modal_captcha()

            form_success = email_filled and password_filled and captcha_filled
            log(f"Form durumu - Email: {email_filled}, Sifre: {password_filled}, CAPTCHA: {captcha_filled}")

            return form_success

        except Exception as e:
            error(f"Modal form doldurma hatasi: {e}")
            return False

    async def _solve_modal_captcha(self) -> bool:
        """Modal'daki CAPTCHA'yi Vision AI ile coz"""
        step("CAPTCHA COZULUYOR")
        try:
            # CAPTCHA gorselini bul (modal icinde)
            captcha_img_selectors = [
                "img[src*='captcha']",
                "img[src*='Captcha']",
                "img[alt*='captcha']",
                "img[alt*='Captcha']",
                ".captcha img",
                "#captchaImg",
            ]

            captcha_img = None
            for selector in captcha_img_selectors:
                try:
                    img = await self.page.query_selector(selector)
                    if img and await img.is_visible():
                        captcha_img = img
                        log(f"CAPTCHA gorseli bulundu: {selector}")
                        break
                except:
                    continue

            if not captcha_img:
                warn("Modal'da CAPTCHA gorseli bulunamadi - belki CAPTCHA yok")
                return True  # CAPTCHA yoksa devam et

            # CAPTCHA screenshot al
            captcha_bytes = await captcha_img.screenshot()
            captcha_base64 = base64.b64encode(captcha_bytes).decode()

            # Debug: CAPTCHA gorselini kaydet
            with open(self.DEBUG_DIR / "modal_captcha.png", "wb") as f:
                f.write(captcha_bytes)
            debug(f"CAPTCHA gorseli kaydedildi: /tmp/tsg_debug/modal_captcha.png ({len(captcha_bytes)} bytes)")

            # Tesseract OCR ile CAPTCHA oku
            log("OCR ile CAPTCHA okunuyor...")
            captcha_text = CaptchaOCR.read_captcha(captcha_base64)

            if captcha_text:
                success(f"CAPTCHA okundu: '{captcha_text}'")
            else:
                error("CAPTCHA okunamadi!")
                return False

            # CAPTCHA input alanini bul ve doldur
            captcha_input_selectors = [
                "input[name='Captcha']",
                "input[name*='captcha']",
                "input[name*='Captcha']",
                "input[placeholder*='Güvenlik']",
                "input[placeholder*='güvenlik']",
                "input[placeholder*='Kod']",
            ]

            for selector in captcha_input_selectors:
                try:
                    field = await self.page.query_selector(selector)
                    if field and await field.is_visible():
                        await field.fill("")
                        await field.type(captcha_text, delay=50)
                        log(f"CAPTCHA girildi: {selector}")
                        success("CAPTCHA COZULDU")
                        return True
                except:
                    continue

            warn("CAPTCHA input alani bulunamadi!")
            return False

        except Exception as e:
            error(f"CAPTCHA cozme hatasi: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _click_modal_login_button(self):
        """Modal icindeki GİRİŞ butonuna tikla"""
        log("Login butonuna tiklanıyor...")
        selectors = [
            ".modal button:has-text('GİRİŞ')",
            ".modal button:has-text('Giriş')",
            ".popup button:has-text('GİRİŞ')",
            "button:has-text('GİRİŞ')",
            "button:has-text('Giriş')",
            "input[type='submit'][value*='GİRİŞ']",
            "input[value*='GİRİŞ']",
            ".modal button[type='submit']",
            ".btn-login",
            "button.btn-primary",
        ]

        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    log(f"Modal login butonuna tiklandi: {selector}")
                    return
            except:
                continue

        # Son care: Enter
        warn("Modal login butonu bulunamadi, Enter'a basiliyor...")
        await self.page.keyboard.press("Enter")

    async def _find_captcha_image(self):
        """CAPTCHA gorselini bul"""
        selectors = [
            "img[src*='captcha']",
            "img[src*='Captcha']",
            "img[src*='guvenlik']",
            "img[id*='captcha']",
            "img[id*='Captcha']",
            "#imgCaptcha",
            ".captcha-image img",
        ]

        for selector in selectors:
            try:
                img = await self.page.query_selector(selector)
                if img:
                    is_visible = await img.is_visible()
                    if is_visible:
                        debug(f"CAPTCHA bulundu: {selector}")
                        return img
            except:
                continue

        return None

    async def _fill_login_form(self, captcha_text: str) -> bool:
        """Login formunu doldur"""
        try:
            # Email alani
            email_selectors = [
                "input[type='email']",
                "input[name*='mail']",
                "input[id*='mail']",
                "input[name*='Mail']",
                "input[placeholder*='mail']",
                "input[placeholder*='Mail']",
            ]

            email_filled = False
            for selector in email_selectors:
                try:
                    field = await self.page.query_selector(selector)
                    if field and await field.is_visible():
                        await field.fill(self.EMAIL)
                        email_filled = True
                        log(f"Email dolduruldu: {selector}")
                        break
                except:
                    continue

            # Sifre alani
            password_selectors = [
                "input[type='password']",
                "input[name*='ifre']",
                "input[name*='sifre']",
                "input[name*='pass']",
                "input[id*='ifre']",
            ]

            password_filled = False
            for selector in password_selectors:
                try:
                    field = await self.page.query_selector(selector)
                    if field and await field.is_visible():
                        await field.fill(self.PASSWORD)
                        password_filled = True
                        log(f"Sifre dolduruldu: {selector}")
                        break
                except:
                    continue

            # CAPTCHA alani
            captcha_selectors = [
                "input[name*='aptcha']",
                "input[name*='guvenlik']",
                "input[placeholder*='Güvenlik']",
                "input[placeholder*='guvenlik']",
                "input[placeholder*='aptcha']",
                "input[id*='aptcha']",
                "input[id*='guvenlik']",
            ]

            captcha_filled = False
            for selector in captcha_selectors:
                try:
                    field = await self.page.query_selector(selector)
                    if field and await field.is_visible():
                        await field.fill(captcha_text)
                        captcha_filled = True
                        log(f"CAPTCHA dolduruldu: {selector}")
                        break
                except:
                    continue

            form_success = email_filled and password_filled and captcha_filled
            log(f"Form durumu - Email: {email_filled}, Sifre: {password_filled}, CAPTCHA: {captcha_filled}")

            return form_success

        except Exception as e:
            error(f"Form doldurma hatasi: {e}")
            return False

    async def _click_login_button(self):
        """Login butonuna tikla"""
        selectors = [
            "button:has-text('GİRİŞ')",
            "button:has-text('Giriş')",
            "button:has-text('giris')",
            "input[type='submit'][value*='GİRİŞ']",
            "input[type='submit'][value*='Giriş']",
            "input[value*='GİRİŞ']",
            "button[type='submit']",
            ".login-button",
            "#btnGiris",
        ]

        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    log(f"Login butonuna tiklandi: {selector}")
                    return
            except:
                continue

        # Buton bulunamazsa Enter'a bas
        warn("Login butonu bulunamadi, Enter'a basiliyor...")
        await self.page.keyboard.press("Enter")

    async def _check_login_success(self) -> bool:
        """Login basarili mi kontrol et"""
        log("Login basari kontrolu yapiliyor...")
        try:
            # Hata mesaji var mi?
            error_selectors = [
                ".error",
                ".hata",
                ".alert-danger",
                ".error-message",
                "div:has-text('Hatalı')",
                "div:has-text('Yanlış')",
            ]

            for selector in error_selectors:
                try:
                    err = await self.page.query_selector(selector)
                    if err and await err.is_visible():
                        error_text = await err.inner_text()
                        warn(f"Hata mesaji bulundu: {error_text}")
                        return False
                except:
                    continue

            # Basari gostergeleri
            success_selectors = [
                "a[href*='logout']",
                "a[href*='cikis']",
                "button:has-text('Çıkış')",
                "a:has-text('Çıkış')",
                ".user-info",
                ".welcome-message",
            ]

            for selector in success_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        log(f"Login basari gostergesi: {selector}")
                        return True
                except:
                    continue

            # URL kontrolu
            current_url = self.page.url.lower()
            if "giris" not in current_url and "login" not in current_url:
                # Ana sayfa veya sorgulama sayfasina yonlendirilmis
                log(f"URL degisti (login'den cikti): {current_url}")
                return True

            return False

        except Exception as e:
            error(f"Login kontrol hatasi: {e}")
            return False

    async def search_company(self, company_name: str, city: str = None) -> List[Dict]:
        """
        Firma ara ve ilanlari getir.

        Args:
            company_name: Firma adi
            city: Firma merkezi sehri (ornek: "İSTANBUL", "ANKARA")
                  None ise Istanbul varsayilan.

        Returns:
            List[Dict]: Ilan listesi (bos olabilir, MOCK YOK!)
        """
        step(f"FIRMA ARANYOR: {company_name}")
        if city:
            log(f"Hedef sehir: {city}")

        # City parametresini instance'a kaydet (_select_sicil_mudurlugu icin)
        self._target_city = city

        # Oncelikle login yap
        if not self.logged_in:
            if not await self.login():
                error("Login yapilamadi, arama yapilamiyor")
                return []

        try:
            # Ilan Goruntuleme sayfasina git (direkt URL)
            search_url = f"{self.BASE_URL}/view/hizlierisim/ilangoruntuleme.php"
            log(f"Ilan Goruntuleme sayfasina gidiliyor: {search_url}")
            await self.page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Debug screenshot
            await self._save_debug_screenshot("search_page")

            # Sicil Mudurlugu dropdown'unu sec (zorunlu alan!)
            # city parametresi search_company'den geliyor
            await self._select_sicil_mudurlugu(city=getattr(self, '_target_city', None))
            await asyncio.sleep(1)

            # CAPTCHA kontrolu - sorgu sayfasinda olabilir
            captcha_img = await self._find_captcha_image()
            if captcha_img:
                log("Sorgu sayfasinda CAPTCHA var, cozuluyor...")
                captcha_solved = await self._solve_page_captcha(captcha_img)
                if not captcha_solved:
                    error("CAPTCHA cozulemedi")
                    return []

            # Arama alanini bul
            search_input = await self._find_search_input()
            if not search_input:
                warn("Arama alani bulunamadi, sayfa icerigini kontrol ediliyor...")
                await self._save_debug_screenshot("search_page_no_input")

                # Belki form farkli bir yerde - tum input'lari listele
                all_inputs = await self.page.query_selector_all("input[type='text']")
                debug(f"Sayfada {len(all_inputs)} text input var")

                for i, inp in enumerate(all_inputs):
                    try:
                        name = await inp.get_attribute("name") or ""
                        placeholder = await inp.get_attribute("placeholder") or ""
                        visible = await inp.is_visible()
                        debug(f"  Input {i}: name='{name}', placeholder='{placeholder}', visible={visible}")
                    except:
                        pass

                return []

            # Firma adini gir
            log(f"Firma adi giriliyor: {company_name}")
            await search_input.fill("")
            await search_input.type(company_name, delay=50)
            await asyncio.sleep(1)

            # Ara butonuna tikla
            await self._click_search_button()
            await asyncio.sleep(4)

            # Debug screenshot
            await self._save_debug_screenshot("search_results")

            # Sonuclari parse et
            results = await self._parse_results()
            success(f"TSG'den {len(results)} sonuc bulundu")
            step("ARAMA TAMAMLANDI")

            return results

        except Exception as e:
            error(f"Arama hatasi: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _solve_page_captcha(self, captcha_img) -> bool:
        """Sayfadaki CAPTCHA'yi coz"""
        try:
            # CAPTCHA screenshot al
            captcha_bytes = await captcha_img.screenshot()
            captcha_base64 = base64.b64encode(captcha_bytes).decode()

            # Debug: CAPTCHA gorselini kaydet
            with open(self.DEBUG_DIR / "page_captcha.png", "wb") as f:
                f.write(captcha_bytes)

            # Tesseract OCR ile CAPTCHA oku
            captcha_text = CaptchaOCR.read_captcha(captcha_base64)
            log(f"Sayfa CAPTCHA okundu: '{captcha_text}'")

            if not captcha_text:
                return False

            # CAPTCHA input alanini bul ve doldur
            captcha_input = await self.page.query_selector(
                "input[name*='aptcha'], input[placeholder*='Güvenlik'], input[placeholder*='guvenlik']"
            )
            if captcha_input:
                await captcha_input.fill(captcha_text)
                log("CAPTCHA girildi")
                return True

            return False

        except Exception as e:
            error(f"CAPTCHA cozme hatasi: {e}")
            return False

    async def _select_sicil_mudurlugu(self, city: str = None) -> bool:
        """
        Sicil Mudurlugu dropdown'unu sec.
        TSG'de arama yapmak icin zorunlu alan.

        Args:
            city: Hedef sehir (ornek: "İSTANBUL", "ANKARA").
                  None ise Istanbul varsayilan.

        Returns:
            bool: Secim basarili mi?
        """
        # Hedef sehir belirle
        target_city = (city or "İSTANBUL").upper()
        log(f"Sicil Mudurlugu seciliyor: {target_city}")

        try:
            # Dropdown selektorleri
            dropdown_selectors = [
                "select[name*='sicil']",
                "select[name*='Sicil']",
                "select[name*='mudurluk']",
                "select[name*='Mudurluk']",
                "select.form-control",
                "select",
            ]

            for selector in dropdown_selectors:
                try:
                    dropdown = await self.page.query_selector(selector)
                    if dropdown and await dropdown.is_visible():
                        # Dropdown'daki tum secenek sayisini al
                        options = await dropdown.query_selector_all("option")
                        option_count = len(options)
                        debug(f"Sicil Mudurlugu dropdown bulundu: {selector} ({option_count} secenek)")

                        if option_count > 1:
                            # 1. Hedef sehri bul
                            for opt in options:
                                opt_text = (await opt.text_content() or "").upper()
                                opt_value = await opt.get_attribute("value") or ""

                                # Hedef sehir eslesme kontrolu (Turkce karakter uyumu)
                                target_normalized = target_city.replace("İ", "I").replace("Ş", "S").replace("Ğ", "G")
                                opt_normalized = opt_text.replace("İ", "I").replace("Ş", "S").replace("Ğ", "G")

                                if target_city in opt_text or target_normalized in opt_normalized:
                                    await dropdown.select_option(value=opt_value)
                                    success(f"Sicil Mudurlugu secildi: {opt_text}")
                                    return True

                            # 2. Istanbul fallback (hedef sehir bulunamadiysa)
                            if target_city != "İSTANBUL":
                                warn(f"{target_city} bulunamadi, Istanbul deneniyor...")
                                for opt in options:
                                    opt_text = (await opt.text_content() or "").upper()
                                    opt_value = await opt.get_attribute("value") or ""

                                    if "STANBUL" in opt_text or "ISTANBUL" in opt_text:
                                        await dropdown.select_option(value=opt_value)
                                        success(f"Sicil Mudurlugu secildi (fallback): {opt_text}")
                                        return True

                            # 3. Son care: ilk gecerli secenek
                            for opt in options:
                                opt_value = await opt.get_attribute("value") or ""
                                if opt_value and opt_value != "0" and opt_value != "":
                                    await dropdown.select_option(value=opt_value)
                                    opt_text = await opt.text_content() or ""
                                    log(f"Sicil Mudurlugu secildi (son fallback): {opt_text}")
                                    return True

                except Exception as e:
                    continue

            warn("Sicil Mudurlugu dropdown bulunamadi - devam ediliyor")
            return False

        except Exception as e:
            error(f"Sicil Mudurlugu secme hatasi: {e}")
            return False

    async def _find_search_input(self):
        """Arama input alanini bul"""
        selectors = [
            "input[name*='nvan']",
            "input[name*='Unvan']",
            "input[placeholder*='nvan']",
            "input[placeholder*='Unvan']",
            "input[id*='nvan']",
            "#txtUnvan",
            "input[type='text']:not([name*='aptcha']):not([name*='Captcha'])",
        ]

        for selector in selectors:
            try:
                inputs = await self.page.query_selector_all(selector)
                for inp in inputs:
                    if await inp.is_visible():
                        name = await inp.get_attribute("name") or ""
                        placeholder = await inp.get_attribute("placeholder") or ""

                        # CAPTCHA degilse kullan
                        if "captcha" not in name.lower() and "captcha" not in placeholder.lower():
                            log(f"Arama alani bulundu: {selector}")
                            return inp
            except:
                continue

        return None

    async def _click_search_button(self):
        """Ara butonuna tikla"""
        log("Sorgula butonuna tiklanıyor...")
        selectors = [
            "button:has-text('SORGULA')",
            "button:has-text('Sorgula')",
            "button:has-text('ARA')",
            "button:has-text('Ara')",
            "input[type='submit'][value*='Sorgula']",
            "input[value*='SORGULA']",
            "#btnSorgula",
            "button[type='submit']",
        ]

        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    log(f"Ara butonuna tiklandi: {selector}")
                    return
            except:
                continue

        # Buton bulunamazsa Enter
        warn("Ara butonu bulunamadi, Enter'a basiliyor...")
        await self.page.keyboard.press("Enter")

    async def _parse_results(self) -> List[Dict]:
        """Sonuclari parse et"""
        log("Sonuclar parse ediliyor...")
        results = []

        # Tablo selektorleri
        table_selectors = [
            "table.GridView",
            "table#gvIlanlar",
            "#ContentPlaceHolder1_gvIlanlar",
            "table.results",
            ".ilan-listesi table",
            "table[id*='GridView']",
            "#gvSonuclar",
            "table.table",
            "table tbody",
        ]

        for selector in table_selectors:
            try:
                table = await self.page.query_selector(selector)
                if table:
                    rows = await table.query_selector_all("tr")
                    debug(f"Tablo bulundu: {selector} ({len(rows)} satir)")

                    for row in rows[1:16]:  # Header atla, max 15
                        try:
                            cells = await row.query_selector_all("td")
                            if len(cells) >= 4:
                                # TSG Tablo Kolonlari (dogru siralama):
                                # 0: Sicil Mudurlugu, 1: Sicil No, 2: Unvan, 3: Yayin Tarihi
                                # 4: Sayi (Gazete No), 5: Sayfa, 6: Ilan Turu, 7: Gazete PDF
                                result = {
                                    "sicil_mudurlugu": await self._get_cell_text(cells, 0),
                                    "sicil_no": await self._get_cell_text(cells, 1),
                                    "unvan": await self._get_cell_text(cells, 2),          # FIRMA ADI!
                                    "tarih": await self._get_cell_text(cells, 3),
                                    "gazete_no": await self._get_cell_text(cells, 4) if len(cells) > 4 else "",
                                    "sayfa": await self._get_cell_text(cells, 5) if len(cells) > 5 else "",
                                    "ilan_tipi": await self._get_cell_text(cells, 6) if len(cells) > 6 else "",
                                    "source": "TSG"
                                }

                                # PDF linki cells[7]'den al
                                if len(cells) > 7:
                                    pdf_cell = cells[7]
                                    pdf_link = await pdf_cell.query_selector("a[href]")
                                    if pdf_link:
                                        pdf_href = await pdf_link.get_attribute("href")
                                        if pdf_href:
                                            if not pdf_href.startswith("http"):
                                                pdf_href = f"{self.BASE_URL}/{pdf_href.lstrip('/')}"
                                            result["pdf_url"] = pdf_href
                                            result["detay_url"] = pdf_href

                                # Fallback: Herhangi bir linkten detay URL al
                                if "detay_url" not in result:
                                    link = await row.query_selector("a[href]")
                                    if link:
                                        href = await link.get_attribute("href")
                                        if href:
                                            if not href.startswith("http"):
                                                href = f"{self.BASE_URL}/{href.lstrip('/')}"
                                            result["detay_url"] = href

                                # En az unvan veya sicil_no doluysa ekle
                                if any([result["unvan"], result["sicil_no"], result["gazete_no"]]):
                                    results.append(result)

                        except Exception as e:
                            continue

                    if results:
                        break

            except:
                continue

        if not results:
            warn("Tablo parse edilemedi, sonuç bulunamadı")

        return results

    async def _get_cell_text(self, cells: list, index: int) -> str:
        """Hucre metnini al"""
        try:
            if index < len(cells):
                text = await cells[index].inner_text()
                return text.strip()
        except:
            pass
        return ""

    async def _save_debug_screenshot(self, name: str):
        """Debug screenshot kaydet"""
        try:
            path = self.DEBUG_DIR / f"{name}.png"
            await self.page.screenshot(path=str(path))
            debug(f"Screenshot kaydedildi: {path}")
        except Exception as e:
            warn(f"Screenshot hatasi: {e}")

    async def get_gazete_page(self, ilan: Dict, index: int = 0) -> Dict:
        """
        Ilan detayindan Gazete PDF sayfasina git ve screenshot al.

        Args:
            ilan: Ilan verisi (detay_url icermeli)
            index: Screenshot dosya indeksi

        Returns:
            Dict: gazete_no, sayfa_no, tarih, screenshot_path, ilan_metni
        """
        step(f"GAZETE SAYFASI CEKILIYOR (ilan {index})")

        detay_url = ilan.get("detay_url")
        if not detay_url:
            warn("Ilan'da detay_url yok")
            return {"error": "detay_url_yok"}

        try:
            # 1. Ilan detay sayfasina git
            log(f"Ilan detay sayfasina gidiliyor: {detay_url}")
            await self.page.goto(detay_url, wait_until="networkidle")
            await asyncio.sleep(2)

            # Debug screenshot
            await self._save_debug_screenshot(f"ilan_detay_{index}")

            # 2. Gazete PDF linkini bul ve tikla
            pdf_link_selectors = [
                "a[href*='.pdf']",
                "a:has-text('PDF')",
                "a:has-text('Gazete')",
                "a:has-text('Görüntüle')",
                "a[href*='gazete']",
                ".pdf-link",
                ".gazete-link",
            ]

            pdf_clicked = False
            for selector in pdf_link_selectors:
                try:
                    link = await self.page.query_selector(selector)
                    if link and await link.is_visible():
                        await link.click()
                        pdf_clicked = True
                        log(f"Gazete PDF linkine tiklandi: {selector}")
                        await asyncio.sleep(3)
                        break
                except:
                    continue

            if not pdf_clicked:
                warn("Gazete PDF linki bulunamadi, mevcut sayfanin screenshot'i alinacak")

            # 3. Full page screenshot al
            screenshot_path = self.DEBUG_DIR / f"gazete_sayfa_{index}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            success(f"Gazete sayfasi screenshot kaydedildi: {screenshot_path}")

            # 4. Sayfa bilgilerini topla
            gazete_info = {
                "gazete_no": ilan.get("gazete_no", ""),
                "tarih": ilan.get("tarih", ""),
                "ilan_tipi": ilan.get("ilan_tipi", ""),
                "screenshot_path": str(screenshot_path),
                "detay_url": detay_url,
            }

            # Sayfa no bulmaya calis (URL veya sayfadan)
            current_url = self.page.url
            if "sayfa" in current_url.lower():
                import re
                match = re.search(r'sayfa[=:]?(\d+)', current_url, re.IGNORECASE)
                if match:
                    gazete_info["sayfa_no"] = match.group(1)

            step("GAZETE SAYFASI TAMAMLANDI")
            return gazete_info

        except Exception as e:
            error(f"Gazete sayfasi hatasi: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "detay_url": detay_url}

    @staticmethod
    def select_best_ilan(ilan_list: List[Dict]) -> tuple:
        """
        Hackathon icin en uygun ilani sec.

        Oncelik sirasi:
        1. Kurulus/Tescil ilanlari (tum 5 baslik dolu)
        2. Yonetici degisikligi (yoneticiler + imza yetkilisi)
        3. Pay devri (ortaklar)
        4. Fallback: Ilk ilan

        Args:
            ilan_list: Ilan listesi

        Returns:
            tuple: (secilen_ilan, index)
        """
        step("EN UYGUN ILAN SECILIYOR")

        if not ilan_list:
            warn("Ilan listesi bos")
            return None, -1

        priority_keywords = [
            (["kuruluş", "kurulus", "tescil", "kurulu"], 5),
            (["yönetici", "yonetici", "müdür", "mudur", "temsil"], 4),
            (["pay devri", "ortaklık", "ortaklik", "hisse"], 3),
        ]

        best_ilan = None
        best_index = 0
        best_score = -1

        for i, ilan in enumerate(ilan_list):
            # v3.5: Yeni kolon isimleri kullaniliyor
            ilan_tipi = (ilan.get("ilan_tipi") or "").lower()
            unvan = (ilan.get("unvan") or "").lower()
            sicil_no = (ilan.get("sicil_no") or "")
            gazete_no = (ilan.get("gazete_no") or "").lower()
            text = f"{ilan_tipi} {unvan} {gazete_no}"

            score = 0
            matched_keyword = None

            for keywords, keyword_score in priority_keywords:
                for keyword in keywords:
                    if keyword in text:
                        score = keyword_score
                        matched_keyword = keyword
                        break
                if score > 0:
                    break

            # Bonus: Sicil No varsa +1
            if sicil_no and sicil_no != "N/A":
                score += 1

            if score > best_score:
                best_score = score
                best_ilan = ilan
                best_index = i
                if matched_keyword:
                    debug(f"Ilan {i}: '{matched_keyword}' bulundu (skor: {score})")

        # Fallback: ilk ilan
        if best_ilan is None:
            best_ilan = ilan_list[0]
            best_index = 0
            debug("Fallback: ilk ilan secildi")

        success(f"Secilen ilan: index={best_index}, tip={best_ilan.get('ilan_tipi', 'N/A')}, skor={best_score}")
        return best_ilan, best_index

    # =====================================================
    # v4.0 - Multi-Ilan Birlestirme Fonksiyonlari
    # =====================================================

    @staticmethod
    def group_ilanlar_by_type(ilan_list: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Ilanlari tiplerine gore grupla.

        Ilan Tipi Kategorileri:
        - KURULUS: kurulus, tescil, kurulu, ana sozlesme
        - YONETIM: yonetici, mudur, temsil, imza
        - SERMAYE: sermaye, pay devri, hisse, ortaklik
        - DIGER: diger tum ilanlar

        Returns:
            Dict[str, List[Dict]]: {"KURULUS": [...], "YONETIM": [...], ...}
        """
        step("ILAN GRUPLAMA (v4.0)")

        # v9.4: Genişletilmiş ilan tip kategorileri
        TYPE_KEYWORDS = {
            "KURULUS": ["kuruluş", "kurulus", "tescil", "kurulu", "ana sözleşme", "ana sozlesme", "birleşme", "birlesme", "devir"],
            "YONETIM": ["yönetim", "yonetim", "yönetici", "yonetici", "müdür", "mudur", "temsil", "imza", "yetki", "atama"],
            "SERMAYE": ["sermaye", "pay devri", "ortaklık", "ortaklik", "hisse", "artırım", "artirim", "azaltım", "azaltim"],
            "GENEL_KURUL": ["genel kurul", "olağan", "olagan", "olağanüstü", "olaganüstü", "toplantı", "toplanti"],
            "TESCIL": ["değişiklik", "degisiklik", "tadil", "düzeltme", "duzeltme", "güncelleme", "guncelleme"],
        }

        groups = {"KURULUS": [], "YONETIM": [], "SERMAYE": [], "GENEL_KURUL": [], "TESCIL": [], "DIGER": []}

        # Turkce karakterleri normalize et
        def normalize_tr(text: str) -> str:
            """Turkce karakterleri ASCII'ye cevir."""
            tr_map = {
                'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
                'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
                'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
            }
            for tr_char, ascii_char in tr_map.items():
                text = text.replace(tr_char, ascii_char)
            return text.lower()

        # Keyword'leri de normalize et
        normalized_keywords = {
            group: [normalize_tr(kw) for kw in keywords]
            for group, keywords in TYPE_KEYWORDS.items()
        }

        for ilan in ilan_list:
            ilan_tipi = normalize_tr(ilan.get("ilan_tipi") or "")
            matched = False

            for group_name, keywords in normalized_keywords.items():
                if any(kw in ilan_tipi for kw in keywords):
                    groups[group_name].append(ilan)
                    matched = True
                    break

            if not matched:
                groups["DIGER"].append(ilan)

        # Log gruplar
        log(f"Gruplama sonucu: KURULUS={len(groups['KURULUS'])}, "
            f"YONETIM={len(groups['YONETIM'])}, "
            f"SERMAYE={len(groups['SERMAYE'])}, "
            f"GENEL_KURUL={len(groups['GENEL_KURUL'])}, "
            f"TESCIL={len(groups['TESCIL'])}, "
            f"DIGER={len(groups['DIGER'])}")

        return groups

    @staticmethod
    def select_priority_ilanlar(grouped_ilanlar: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Her gruptan en guncel/en uygun ilani sec.

        Oncelik: En yeni tarih > Sicil no olan

        Returns:
            Dict[str, Dict]: {"KURULUS": best_ilan, "YONETIM": best_ilan, ...}
        """
        step("ONCELIKLI ILAN SECIMI (v4.0)")

        priority_ilanlar = {}

        for group_name, ilanlar in grouped_ilanlar.items():
            if not ilanlar:
                continue

            # Tarihe gore sirala (en yeni basta)
            # Tarih formati: DD.MM.YYYY veya YYYY-MM-DD
            def parse_date(ilan):
                tarih = ilan.get("tarih", "")
                # DD.MM.YYYY -> YYYYMMDD
                if "." in tarih:
                    parts = tarih.split(".")
                    if len(parts) == 3:
                        return f"{parts[2]}{parts[1]}{parts[0]}"
                return tarih

            sorted_ilanlar = sorted(
                ilanlar,
                key=lambda x: parse_date(x),
                reverse=True
            )

            # Sicil no olan tercih edilir
            for ilan in sorted_ilanlar:
                if ilan.get("sicil_no"):
                    priority_ilanlar[group_name] = ilan
                    break
            else:
                priority_ilanlar[group_name] = sorted_ilanlar[0]

            debug(f"{group_name}: {priority_ilanlar[group_name].get('unvan', 'N/A')[:40]}... "
                  f"({priority_ilanlar[group_name].get('tarih', 'N/A')})")

        success(f"Secilen gruplar: {list(priority_ilanlar.keys())}")
        return priority_ilanlar

    # =====================================================
    # v8.0 - PDF URL EXTRACTION (BASIT VE CALISIYOR!)
    # =====================================================

    async def click_and_download_pdf(self, row_index: int) -> Optional[bytes]:
        """
        PDF ikonuna tikla, popup ac, URL'den indir.

        v8.0: URL extraction - test edildi, calisiyor!

        Akis:
        1. Tablodaki row_index satirini bul
        2. Gazete kolonundaki (cells[7]) PDF linkine tikla
        3. Popup acilir
        4. object[data] veya embed[src]'den PDF URL'sini al
        5. page.request.get() ile PDF'i indir (session cookie korunur)

        Args:
            row_index: Tiklanacak satir indexi (0-based)

        Returns:
            bytes: PDF dosya icerigi veya None
        """
        step(f"PDF TIKLA VE INDIR (satir {row_index})")

        try:
            # 1. Tablodaki satiri bul
            rows = await self.page.query_selector_all("table.table tbody tr")
            if not rows:
                rows = await self.page.query_selector_all("table tbody tr")

            if not rows or row_index >= len(rows):
                error(f"Satir bulunamadi: row_index={row_index}")
                return None

            log(f"Tablo bulundu: {len(rows)} satir")

            # 2. PDF linkini bul (cells[7] = Gazete kolonu)
            cells = await rows[row_index].query_selector_all("td")
            if len(cells) < 8:
                error(f"Kolon sayisi yetersiz: {len(cells)}")
                return None

            pdf_link = await cells[7].query_selector("a")
            if not pdf_link:
                error("PDF linki bulunamadi")
                return None

            log("PDF linki bulundu, tiklanıyor...")

            # 3. Tikla ve popup bekle
            # v8.1 BUG FIX: Popup timeout 15s -> 30s (yavaş ağlarda fail oluyordu)
            try:
                async with self.page.context.expect_page(timeout=30000) as popup_info:
                    await pdf_link.click()

                popup = await popup_info.value
                await popup.wait_for_load_state("networkidle", timeout=30000)
                log("Popup acildi!")

                # Debug screenshot
                await popup.screenshot(path=str(self.DEBUG_DIR / "popup_viewer.png"))

                # 4. PDF URL'sini cikar
                pdf_url = await self._extract_pdf_url(popup)
                if not pdf_url:
                    warn("PDF URL bulunamadi")
                    await popup.close()
                    return None

                # 5. PDF'i indir
                full_url = f"{self.BASE_URL}{pdf_url}" if not pdf_url.startswith("http") else pdf_url
                log(f"PDF indiriliyor: {full_url}")

                resp = await popup.request.get(full_url)
                await popup.close()

                if resp.ok:
                    pdf_bytes = await resp.body()
                    if pdf_bytes and len(pdf_bytes) > 100 and pdf_bytes[:4] == b'%PDF':
                        success(f"PDF indirildi: {len(pdf_bytes)} bytes")
                        return pdf_bytes
                    else:
                        warn(f"Gecersiz PDF: {len(pdf_bytes) if pdf_bytes else 0} bytes")
                else:
                    error(f"HTTP hatasi: {resp.status}")

            except Exception as popup_err:
                warn(f"Popup hatasi: {popup_err}")

            return None

        except Exception as e:
            error(f"PDF indirme hatasi: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _extract_pdf_url(self, page) -> Optional[str]:
        """
        Popup sayfasindan PDF URL'sini cikar.

        TSG, PDF'i <object> veya <embed> tag'i icinde gosteriyor.
        URL, data veya src attribute'unda.

        Args:
            page: Playwright Page objesi (popup)

        Returns:
            str: PDF URL veya None
        """
        selectors = [
            ("object[data*='.pdf']", "data"),
            ("embed[src*='.pdf']", "src"),
            ("object[data*='gazete']", "data"),
            ("embed[src*='gazete']", "src"),
            ("object[data*='tmp_gazete']", "data"),
            ("embed[src*='tmp_gazete']", "src"),
        ]

        for selector, attr in selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    url = await elem.get_attribute(attr)
                    if url:
                        log(f"PDF URL bulundu ({selector}): {url}")
                        return url
            except:
                continue

        # Fallback: tum object ve embed'leri kontrol et
        try:
            for tag in ["object", "embed"]:
                elements = await page.query_selector_all(tag)
                for elem in elements:
                    for attr in ["data", "src"]:
                        url = await elem.get_attribute(attr)
                        if url and ('.pdf' in url.lower() or 'gazete' in url.lower()):
                            log(f"PDF URL bulundu (fallback {tag}): {url}")
                            return url
        except:
            pass

        return None

    async def _close_browser(self):
        """Browser'i kapat"""
        log("Browser kapatiliyor...")
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            success("Browser kapatildi")
        except:
            pass

        self.browser = None
        self.page = None
        self.playwright = None


# Standalone test
if __name__ == "__main__":
    import sys

    async def test():
        company = sys.argv[1] if len(sys.argv) > 1 else "Turkcell"
        step(f"TSG Scraper v3 Test: {company}")

        async with TSGScraper() as scraper:
            # Login test
            step("LOGIN TEST")
            login_success = await scraper.login()
            log(f"Login: {'BASARILI' if login_success else 'BASARISIZ'}")

            if login_success:
                # Arama test
                step("ARAMA TEST")
                results = await scraper.search_company(company)
                log(f"Sonuc sayisi: {len(results)}")

                for i, r in enumerate(results[:3], 1):
                    log(f"--- Sonuc {i} ---")
                    print(json.dumps(r, indent=2, ensure_ascii=False))

    asyncio.run(test())
