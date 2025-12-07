"""
TSG Gazete OCR - Tesseract ile Gazete Sayfasi Okuma
Hackathon icin gazete screenshot'larindan metin cikartma
"""
import io
import os
from typing import Optional

from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np
import pytesseract

from app.agents.tsg.logger import log, step, success, error, warn, debug


class GazeteOCR:
    """
    TSG Gazete sayfasi icin optimize edilmis OCR.

    Gazete sayfasi karakteristikleri:
    - Cok sutunlu layout
    - Kucuk font
    - Turkce karakterler
    """

    # Tesseract Turkce dil paketi
    LANG = "tur"  # Turkce yoksa "eng" kullan

    # Preprocessing ayarlari
    SCALE_FACTOR = 2  # Upscale
    CONTRAST_FACTOR = 1.5  # Kontrast artirma
    SHARPNESS_FACTOR = 2.0  # Keskinlestirme

    DEBUG_DIR = "/tmp/tsg_debug"

    @classmethod
    def read_gazete_page(cls, image_path: str) -> str:
        """
        Gazete sayfasi screenshot'indan metin cikar.

        Args:
            image_path: Screenshot dosya yolu

        Returns:
            str: Gazete sayfasi metni
        """
        step("GAZETE OCR BASLIYOR")

        if not os.path.exists(image_path):
            error(f"Dosya bulunamadi: {image_path}")
            return ""

        try:
            # Gorseli oku
            img = Image.open(image_path)
            debug(f"Gorsel yuklendi: {img.width}x{img.height}")

            # Preprocessing
            processed = cls._preprocess_gazete(img)

            # Debug: preprocessed gorseli kaydet
            os.makedirs(cls.DEBUG_DIR, exist_ok=True)
            debug_path = f"{cls.DEBUG_DIR}/gazete_ocr_processed.png"
            processed.save(debug_path)
            debug(f"Processed gorsel kaydedildi: {debug_path}")

            # Tesseract OCR
            log("Tesseract OCR calisiyor...")

            # Turkce dil paketi kontrol et
            available_langs = pytesseract.get_languages()
            lang = cls.LANG if cls.LANG in available_langs else "eng"
            debug(f"OCR dili: {lang}")

            # OCR config
            # --psm 3: Fully automatic page segmentation (default)
            # --psm 6: Assume a single uniform block of text
            config = f'--psm 3 --oem 3'

            text = pytesseract.image_to_string(processed, lang=lang, config=config)

            # Temizle
            text = cls._clean_text(text)

            success(f"OCR tamamlandi: {len(text)} karakter")
            return text

        except Exception as e:
            error(f"Gazete OCR hatasi: {e}")
            import traceback
            traceback.print_exc()
            return ""

    @classmethod
    def _preprocess_gazete(cls, img: Image.Image) -> Image.Image:
        """
        Gazete sayfasi icin preprocessing.

        Steps:
        1. Grayscale
        2. Contrast artirma
        3. Sharpness artirma
        4. Upscale
        5. Threshold (adaptive)
        """
        debug("Preprocessing basladi")

        # 1. Grayscale
        gray = ImageOps.grayscale(img)
        debug("Grayscale tamamlandi")

        # 2. Kontrast artir
        enhancer = ImageEnhance.Contrast(gray)
        contrasted = enhancer.enhance(cls.CONTRAST_FACTOR)
        debug(f"Kontrast artirildi (x{cls.CONTRAST_FACTOR})")

        # 3. Keskinlestir
        enhancer = ImageEnhance.Sharpness(contrasted)
        sharpened = enhancer.enhance(cls.SHARPNESS_FACTOR)
        debug(f"Keskinlestirme tamamlandi (x{cls.SHARPNESS_FACTOR})")

        # 4. Upscale (gerekirse)
        if img.width < 2000:
            new_size = (img.width * cls.SCALE_FACTOR, img.height * cls.SCALE_FACTOR)
            sharpened = sharpened.resize(new_size, Image.LANCZOS)
            debug(f"Upscale tamamlandi: {sharpened.width}x{sharpened.height}")

        # 5. Adaptive threshold (Otsu)
        arr = np.array(sharpened)
        threshold = cls._otsu_threshold(arr)
        debug(f"Otsu threshold: {threshold}")
        binary = ((arr > threshold) * 255).astype(np.uint8)

        result = Image.fromarray(binary)
        debug("Preprocessing tamamlandi")

        return result

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

    @staticmethod
    def _clean_text(text: str) -> str:
        """OCR metnini temizle."""
        if not text:
            return ""

        # Gereksiz bosluk ve satir sonlarini temizle
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Cok kisa satirlari atla (noise)
            if len(line) > 2:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @classmethod
    def extract_ilan_from_page(cls, page_text: str, firma_adi: str) -> str:
        """
        Gazete sayfasindan belirli firmaya ait ilani cikar.

        v9.1: Ilan blok bazli kesme (paragraf yerine)

        Args:
            page_text: Full gazete sayfasi metni
            firma_adi: Aranacak firma adi

        Returns:
            str: Firmaya ait ilan metni
        """
        import re

        if not page_text or not firma_adi:
            return page_text

        # Firma adini bul (case insensitive)
        firma_match = re.search(re.escape(firma_adi), page_text, re.IGNORECASE)
        if not firma_match:
            warn(f"Firma adi bulunamadi: {firma_adi}")
            return page_text

        firma_pos = firma_match.start()
        debug(f"Firma bulundu pozisyon: {firma_pos}")

        # Ilan baslangici: "Ilan Sira No" veya "T.C." ifadesi
        # Firma pozisyonundan geriye dogru ara
        start_patterns = [r'[Ii]lan\s*S[iu]ra\s*No', r'T\.C\.']
        start_pos = 0

        for pattern in start_patterns:
            matches = list(re.finditer(pattern, page_text[:firma_pos]))
            if matches:
                # En son (firmaya en yakin) eslemeyi al
                last_match = matches[-1]
                if last_match.start() > start_pos:
                    start_pos = last_match.start()
                    debug(f"Ilan baslangici bulundu: {start_pos}")

        # Ilan sonu: Sonraki "Ilan Sira No" veya "(number)" - en az 500 karakter sonra
        end_pos = len(page_text)
        search_start = firma_pos + 200  # En az 200 karakter sonra ara

        end_patterns = [r'[Ii]lan\s*S[iu]ra\s*No', r'\(\d{6,}\)']
        for pattern in end_patterns:
            match = re.search(pattern, page_text[search_start:])
            if match:
                potential_end = search_start + match.start()
                if potential_end < end_pos:
                    end_pos = potential_end
                    debug(f"Ilan sonu bulundu: {end_pos}")

        # Ilan metnini kes
        ilan_text = page_text[start_pos:end_pos].strip()

        if len(ilan_text) > 100:
            debug(f"Firma ilani kesildi: {len(ilan_text)} karakter")
            return ilan_text

        # Fallback: Firma etrafinda 2000 karakter
        warn("Ilan blogu bulunamadi, firma etrafindaki metin kesiliyor")
        start = max(0, firma_pos - 500)
        end = min(len(page_text), firma_pos + 1500)
        return page_text[start:end]


    # =====================================================
    # v9.0 - PDF OCR (Scanned PDF Support)
    # =====================================================

    @classmethod
    def read_pdf_file(cls, pdf_path: str) -> str:
        """
        PDF dosyasindan OCR ile metin cikar.

        TSG PDF'leri taranmis gorsel oldugundan:
        1. PDF -> PNG (pdf2image)
        2. PNG -> Text (Tesseract)

        Args:
            pdf_path: PDF dosya yolu

        Returns:
            str: OCR ile okunan metin
        """
        step("PDF OCR BASLIYOR")

        if not os.path.exists(pdf_path):
            error(f"PDF bulunamadi: {pdf_path}")
            return ""

        try:
            from pdf2image import convert_from_path

            # PDF -> PNG (her sayfa icin)
            log("PDF sayfalari PNG'ye donusturuluyor...")
            images = convert_from_path(
                pdf_path,
                dpi=300,  # Yuksek cozunurluk = daha iyi OCR
                fmt='png'
            )

            log(f"{len(images)} sayfa donusturuldu")

            all_text = []
            for i, img in enumerate(images):
                log(f"Sayfa {i+1}/{len(images)} OCR yapiliyor...")

                # Preprocessing
                processed = cls._preprocess_gazete(img)

                # Debug: kaydet
                os.makedirs(cls.DEBUG_DIR, exist_ok=True)
                debug_path = f"{cls.DEBUG_DIR}/pdf_page_{i}.png"
                processed.save(debug_path)
                debug(f"Sayfa {i+1} kaydedildi: {debug_path}")

                # Tesseract OCR
                available_langs = pytesseract.get_languages()
                lang = cls.LANG if cls.LANG in available_langs else "eng"
                config = '--psm 3 --oem 3'

                text = pytesseract.image_to_string(processed, lang=lang, config=config)
                text = cls._clean_text(text)

                if text:
                    all_text.append(f"--- SAYFA {i+1} ---\n{text}")
                    log(f"Sayfa {i+1}: {len(text)} karakter")

            full_text = "\n\n".join(all_text)
            success(f"PDF OCR tamamlandi: {len(full_text)} karakter")
            return full_text

        except ImportError as e:
            error(f"pdf2image yuklu degil: pip install pdf2image")
            error(f"Ayrica poppler-utils gerekli: brew install poppler (macOS)")
            return ""
        except Exception as e:
            error(f"PDF OCR hatasi: {e}")
            import traceback
            traceback.print_exc()
            return ""

    @classmethod
    def read_pdf_bytes(cls, pdf_bytes: bytes) -> str:
        """
        PDF bytes'dan OCR ile metin cikar.

        Args:
            pdf_bytes: PDF dosya icerigi (bytes)

        Returns:
            str: OCR ile okunan metin
        """
        import tempfile

        if not pdf_bytes or len(pdf_bytes) < 100:
            warn("PDF bytes bos veya cok kisa")
            return ""

        # Temp dosyaya kaydet
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name

        log(f"PDF temp dosyaya kaydedildi: {temp_path} ({len(pdf_bytes)} bytes)")

        try:
            return cls.read_pdf_file(temp_path)
        finally:
            # Temp dosyayi sil
            try:
                os.unlink(temp_path)
            except:
                pass


# Standalone test
if __name__ == "__main__":
    import sys

    test_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tsg_debug/gazete_sayfa_0.png"

    # PDF mi yoksa gorsel mi?
    if test_file.lower().endswith('.pdf'):
        step(f"PDF OCR Test: {test_file}")
        result = GazeteOCR.read_pdf_file(test_file)
    elif os.path.exists(test_file):
        step(f"Gazete OCR Test: {test_file}")
        result = GazeteOCR.read_gazete_page(test_file)
    else:
        warn(f"Test dosyasi bulunamadi: {test_file}")
        log("Oncelikle TSG Agent'i calistirarak gazete screenshot'i alin.")
        result = ""

    if result:
        print("\n" + "="*50)
        print("OCR SONUCU:")
        print("="*50)
        print(result[:2000] if len(result) > 2000 else result)
        print("="*50)
        print(f"Toplam {len(result)} karakter")
