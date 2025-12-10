"""
CAPTCHA OCR - Tesseract ile CAPTCHA Cozme
TSG CAPTCHA icin optimize edilmis preprocessing + OCR

v2: Coklu threshold + PSM denemesi ile daha yuksek basari orani
"""
import base64
import io
import os
import re
from typing import Optional, List, Tuple
from collections import Counter

from PIL import Image, ImageFilter, ImageOps
import numpy as np
import pytesseract

from app.agents.tsg.logger import log, step, success, error, warn, debug


class CaptchaOCR:
    """TSG CAPTCHA icin optimize edilmis OCR."""

    SCALE_FACTOR = 3  # 146x36 -> 438x108
    BLUR_RADIUS = 0.5
    DEBUG_DIR = "/tmp/tsg_debug"

    # TSG CAPTCHA genellikle 4-6 karakter
    MIN_CAPTCHA_LEN = 3
    MAX_CAPTCHA_LEN = 6

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
    def _preprocess_inverted(cls, image_bytes: bytes, threshold: int) -> Image.Image:
        """Inverted (ters) threshold ile preprocessing - bazi CAPTCHA'lar icin"""
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)
        gray = ImageOps.grayscale(img)
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=cls.BLUR_RADIUS))
        arr = np.array(blurred)
        # Ters threshold
        binary = ((arr < threshold) * 255).astype(np.uint8)
        return Image.fromarray(binary)

    @classmethod
    def _preprocess_adaptive(cls, image_bytes: bytes) -> Image.Image:
        """Adaptive threshold benzeri - bolgesel ortalama"""
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)
        gray = ImageOps.grayscale(img)

        # Daha guclu blur
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=1.0))
        arr = np.array(blurred)

        # Local mean kullan
        from scipy.ndimage import uniform_filter
        local_mean = uniform_filter(arr.astype(float), size=15)
        binary = ((arr > local_mean - 10) * 255).astype(np.uint8)
        return Image.fromarray(binary)

    @classmethod
    def _preprocess_sharpened(cls, image_bytes: bytes) -> Image.Image:
        """Sharpen + threshold"""
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)

        # Sharpen filtresi uygula
        img = img.filter(ImageFilter.SHARPEN)
        gray = ImageOps.grayscale(img)

        arr = np.array(gray)
        threshold = cls._otsu_threshold(arr)
        binary = ((arr > threshold) * 255).astype(np.uint8)
        return Image.fromarray(binary)

    @staticmethod
    def _otsu_threshold(gray_array: np.ndarray) -> int:
        """Otsu's method ile optimal threshold bul."""
        hist, _ = np.histogram(gray_array.flatten(), bins=256, range=(0, 256))
        total = gray_array.size

        sum_total = np.sum(np.arange(256) * hist)
        sum_bg, weight_bg, max_var, threshold = 0, 0, 0, 0

        for i in range(256):
            weight_bg += hist[i]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break

            sum_bg += i * hist[i]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg

            var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if var_between > max_var:
                max_var = var_between
                threshold = i

        return threshold

    @classmethod
    def _is_valid_captcha(cls, text: str) -> bool:
        """CAPTCHA metninin gecerli olup olmadigini kontrol et"""
        if not text:
            return False
        # Sadece alfanumerik
        clean = re.sub(r'[^A-Za-z0-9]', '', text)
        return cls.MIN_CAPTCHA_LEN <= len(clean) <= cls.MAX_CAPTCHA_LEN

    @classmethod
    def _select_best_result(cls, results: List[str]) -> str:
        """En iyi sonucu sec - en cok tekrarlanan veya optimal uzunlukta olan"""
        if not results:
            return ""

        # Temizle
        clean_results = [re.sub(r'[^A-Za-z0-9]', '', r).upper() for r in results]
        valid_results = [r for r in clean_results if cls._is_valid_captcha(r)]

        if not valid_results:
            # Gecerli sonuc yoksa en uzun olani al
            return max(clean_results, key=len) if clean_results else ""

        # En cok tekrarlanan
        counter = Counter(valid_results)
        most_common = counter.most_common(1)[0]

        # 2+ kez tekrarlaniyorsa kesinlikle dogrudur
        if most_common[1] >= 2:
            return most_common[0]

        # 4 karakter olanlar oncelikli (TSG genellikle 4 karakter)
        four_char = [r for r in valid_results if len(r) == 4]
        if four_char:
            return Counter(four_char).most_common(1)[0][0]

        return most_common[0]

    @classmethod
    def read_captcha(cls, image_base64: str) -> str:
        """
        Base64 CAPTCHA gorselinden metin cikar.
        Coklu preprocessing + PSM denemesi ile yuksek basari orani.

        Args:
            image_base64: Base64 encoded PNG/JPEG

        Returns:
            str: 3-6 karakter CAPTCHA metni
        """
        step("OCR CAPTCHA OKUNUYOR (v2 - coklu deneme)")
        try:
            # Base64 -> bytes
            image_bytes = base64.b64decode(image_base64)
            debug(f"Base64 decode: {len(image_bytes)} bytes")

            # Debug klasoru olustur
            os.makedirs(cls.DEBUG_DIR, exist_ok=True)

            # Tum preprocessing yontemlerini dene
            preprocessing_methods = [
                ("otsu", lambda: cls._preprocess_otsu(image_bytes)),
                ("fixed_120", lambda: cls._preprocess_fixed(image_bytes, 120)),
                ("fixed_140", lambda: cls._preprocess_fixed(image_bytes, 140)),
                ("fixed_160", lambda: cls._preprocess_fixed(image_bytes, 160)),
                ("fixed_180", lambda: cls._preprocess_fixed(image_bytes, 180)),
                ("inverted_120", lambda: cls._preprocess_inverted(image_bytes, 120)),
                ("sharpened", lambda: cls._preprocess_sharpened(image_bytes)),
            ]

            # scipy varsa adaptive de ekle
            try:
                from scipy.ndimage import uniform_filter
                preprocessing_methods.append(("adaptive", lambda: cls._preprocess_adaptive(image_bytes)))
            except ImportError:
                debug("scipy bulunamadi, adaptive preprocessing atlanıyor")

            # PSM modlari (8=single word, 7=single line, 13=raw line)
            psm_modes = [8, 7, 13, 6]

            # Whitelist config
            whitelist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

            all_results = []
            debug(f"Toplam {len(preprocessing_methods)} preprocessing, {len(psm_modes)} PSM modu deneniyor...")

            for prep_name, prep_func in preprocessing_methods:
                try:
                    processed = prep_func()

                    # Debug: ilk preprocessing'i kaydet
                    if prep_name == "otsu":
                        processed.save(f"{cls.DEBUG_DIR}/ocr_processed_otsu.png")

                    for psm in psm_modes:
                        config = f'--psm {psm} -c tessedit_char_whitelist={whitelist}'
                        try:
                            text = pytesseract.image_to_string(processed, config=config)
                            clean = re.sub(r'[^A-Za-z0-9]', '', text.strip().upper())

                            if clean:
                                all_results.append(clean)
                                debug(f"  {prep_name}/PSM{psm}: '{clean}'")

                        except Exception as e:
                            debug(f"  {prep_name}/PSM{psm} OCR hatasi: {e}")
                            continue

                except Exception as e:
                    debug(f"  {prep_name} preprocessing hatasi: {e}")
                    continue

            # En iyi sonucu sec
            if all_results:
                debug(f"Toplam {len(all_results)} sonuc elde edildi")
                captcha = cls._select_best_result(all_results)

                # Uzunluk kontrol
                if len(captcha) > cls.MAX_CAPTCHA_LEN:
                    captcha = captcha[:cls.MAX_CAPTCHA_LEN]

                success(f"OCR Result: '{captcha}' (toplam {len(all_results)} deneme)")
                return captcha
            else:
                error("Hicbir OCR denemesi sonuc vermedi!")
                return ""

        except Exception as e:
            error(f"OCR Error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    @classmethod
    def read_captcha_from_file(cls, file_path: str) -> str:
        """
        Dosyadan CAPTCHA oku (debug icin).

        Args:
            file_path: Gorsel dosyasi yolu

        Returns:
            str: CAPTCHA metni
        """
        log(f"Dosyadan CAPTCHA okunuyor: {file_path}")
        with open(file_path, "rb") as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode()
        return cls.read_captcha(image_base64)


# Standalone test
if __name__ == "__main__":
    # Test with sample CAPTCHA
    test_file = "/tmp/tsg_debug/modal_captcha.png"

    if os.path.exists(test_file):
        step(f"OCR Test: {test_file}")
        result = CaptchaOCR.read_captcha_from_file(test_file)
        success(f"CAPTCHA Result: {result}")
    else:
        warn(f"Test file not found: {test_file}")
        log("Run TSG scraper first to capture a CAPTCHA image.")
