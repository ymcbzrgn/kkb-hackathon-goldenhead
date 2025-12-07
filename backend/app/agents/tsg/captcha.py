"""
CAPTCHA OCR - Tesseract ile CAPTCHA Cozme
TSG CAPTCHA icin optimize edilmis preprocessing + OCR
"""
import base64
import io
import os
import re
from typing import Optional

from PIL import Image, ImageFilter, ImageOps
import numpy as np
import pytesseract

from app.agents.tsg.logger import log, step, success, error, warn, debug


class CaptchaOCR:
    """TSG CAPTCHA icin optimize edilmis OCR."""

    SCALE_FACTOR = 3  # 146x36 -> 438x108
    BLUR_RADIUS = 0.5
    DEBUG_DIR = "/tmp/tsg_debug"

    @classmethod
    def preprocess_image(cls, image_bytes: bytes) -> Image.Image:
        """
        CAPTCHA gorselini OCR icin hazirla.

        Pipeline:
        1. Upscale (3x) - kucuk gorsel, daha fazla detay
        2. Grayscale - renk bilgisini kaldir
        3. Blur - gurultu cizgilerini yumusat
        4. Threshold (Otsu) - binary donusum
        """
        debug(f"Preprocessing basladi ({len(image_bytes)} bytes)")

        # Bytes -> PIL Image
        img = Image.open(io.BytesIO(image_bytes))
        debug(f"Orijinal boyut: {img.width}x{img.height}")

        # 1. Upscale
        new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
        img = img.resize(new_size, Image.LANCZOS)
        debug(f"Upscale sonrasi: {img.width}x{img.height}")

        # 2. Grayscale
        gray = ImageOps.grayscale(img)

        # 3. Gaussian Blur
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=cls.BLUR_RADIUS))

        # 4. Otsu Threshold
        arr = np.array(blurred)
        threshold = cls._otsu_threshold(arr)
        debug(f"Otsu threshold: {threshold}")
        binary = ((arr > threshold) * 255).astype(np.uint8)

        debug("Preprocessing tamamlandi")
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
    def read_captcha(cls, image_base64: str) -> str:
        """
        Base64 CAPTCHA gorselinden metin cikar.

        Args:
            image_base64: Base64 encoded PNG/JPEG

        Returns:
            str: 3-6 karakter CAPTCHA metni
        """
        step("OCR CAPTCHA OKUNUYOR")
        try:
            # Base64 -> bytes
            image_bytes = base64.b64decode(image_base64)
            debug(f"Base64 decode: {len(image_bytes)} bytes")

            # Preprocess
            processed = cls.preprocess_image(image_bytes)

            # Debug: kaydet
            os.makedirs(cls.DEBUG_DIR, exist_ok=True)
            processed.save(f"{cls.DEBUG_DIR}/ocr_processed.png")
            debug("Processed gorsel kaydedildi: /tmp/tsg_debug/ocr_processed.png")

            # Tesseract OCR
            # --psm 8: Treat the image as a single word
            # tessedit_char_whitelist: Sadece bu karakterler
            config = '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            log("Tesseract OCR calisiyor...")
            text = pytesseract.image_to_string(processed, config=config)

            # Temizle - sadece alfanumerik
            captcha = re.sub(r'[^A-Za-z0-9]', '', text.strip().upper())

            # 3-6 karakter (TSG CAPTCHA genellikle 4 karakter)
            if len(captcha) > 6:
                captcha = captcha[:6]

            success(f"OCR Result: '{captcha}' (raw: '{text.strip()}')")
            return captcha

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
