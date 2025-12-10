"""
News OCR Fallback - Playwright Screenshot + Tesseract
LLM extraction başarısız olursa OCR'a düş

TSG OCR'dan adapt edildi - simplified version
"""
import io
import os
from typing import Optional

from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np
import pytesseract

from app.agents.news.logger import log, success, error, warn, debug


class NewsOCR:
    """
    Haber sayfası için fallback OCR.
    
    Kullanım senaryosu:
    1. LLM extraction başarısız olur
    2. Playwright screenshot alır
    3. OCR ile metin çıkarır
    4. LLM'e tekrar gönderir (daha temiz metin)
    """
    
    # Tesseract config
    LANG = "tur"  # Türkçe (fallback: eng)
    
    # Preprocessing ayarları (TSG'den hafifleştirilmiş)
    SCALE_FACTOR = 1.5  # Hafif upscale (haber sitesi zaten okunaklı)
    CONTRAST_FACTOR = 1.3  # Hafif contrast boost
    
    DEBUG_DIR = "/tmp/news_ocr_debug"
    
    @classmethod
    async def extract_from_page(cls, page, max_chars: int = 50000) -> str:
        """
        Playwright page'den screenshot + OCR ile metin çıkar.
        
        Args:
            page: Playwright page object
            max_chars: Maksimum karakter sayısı
        
        Returns:
            str: OCR ile çıkarılan metin
        """
        try:
            debug("OCR fallback başlıyor...")
            
            # 1. Screenshot al (PNG bytes)
            screenshot_bytes = await page.screenshot(type="png", full_page=True)
            debug(f"Screenshot alındı: {len(screenshot_bytes)} bytes")
            
            # 2. PIL Image'e çevir
            img = Image.open(io.BytesIO(screenshot_bytes))
            debug(f"Görsel yüklendi: {img.width}x{img.height}")
            
            # 3. Preprocessing
            processed = cls._preprocess_news_page(img)
            
            # Debug: kaydet
            if os.getenv("NEWS_OCR_DEBUG"):
                os.makedirs(cls.DEBUG_DIR, exist_ok=True)
                debug_path = f"{cls.DEBUG_DIR}/news_ocr_{hash(screenshot_bytes)}.png"
                processed.save(debug_path)
                debug(f"Debug görsel kaydedildi: {debug_path}")
            
            # 4. Tesseract OCR
            log("Tesseract OCR çalışıyor...")
            
            # Dil kontrolü
            available_langs = pytesseract.get_languages()
            lang = cls.LANG if cls.LANG in available_langs else "eng"
            debug(f"OCR dili: {lang}")
            
            # PSM 3: Fully automatic (haber sayfası için uygun)
            config = '--psm 3 --oem 3'
            
            text = pytesseract.image_to_string(processed, lang=lang, config=config)
            
            # 5. Temizle
            text = cls._clean_text(text)
            
            # 6. Limit
            if len(text) > max_chars:
                text = text[:max_chars]
                debug(f"OCR metni {max_chars} karaktere kısaltıldı")
            
            success(f"OCR tamamlandı: {len(text)} karakter")
            return text
            
        except Exception as e:
            error(f"OCR fallback hatası: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    @classmethod
    def _preprocess_news_page(cls, img: Image.Image) -> Image.Image:
        """
        Haber sayfası için preprocessing (simplified).
        
        Steps:
        1. Grayscale
        2. Contrast artırma (hafif)
        3. Upscale (gerekirse)
        """
        debug("Preprocessing başladı")
        
        # 1. Grayscale
        gray = ImageOps.grayscale(img)
        
        # 2. Kontrast artır (hafif)
        enhancer = ImageEnhance.Contrast(gray)
        contrasted = enhancer.enhance(cls.CONTRAST_FACTOR)
        debug(f"Kontrast artırıldı (x{cls.CONTRAST_FACTOR})")
        
        # 3. Upscale (sadece küçük görsel için)
        if img.width < 1500:
            new_size = (
                int(img.width * cls.SCALE_FACTOR),
                int(img.height * cls.SCALE_FACTOR)
            )
            contrasted = contrasted.resize(new_size, Image.LANCZOS)
            debug(f"Upscale: {contrasted.width}x{contrasted.height}")
        
        debug("Preprocessing tamamlandı")
        return contrasted
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """
        OCR metnini temizle.
        
        - Boş satırları kaldır
        - Çok kısa satırları atla (noise)
        - Gereksiz boşlukları temizle
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Çok kısa satırlar noise olabilir
            if len(line) > 3:
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        
        # Çoklu boşlukları teke düşür
        import re
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()


# Singleton instance
_ocr_instance = None

def get_ocr() -> NewsOCR:
    """Singleton OCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = NewsOCR()
    return _ocr_instance
