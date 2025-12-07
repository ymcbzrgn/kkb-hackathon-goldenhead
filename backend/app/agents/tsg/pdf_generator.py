"""
TSG PDF Generator - Profesyonel Gazete Sayfasi Olusturucu
KKB Hackathon 2024 - Golden Head

Bu modul, TSG sitesinden alinan verilerle profesyonel gorunumlu
bir Ticaret Sicili Gazetesi sayfasi olusturur.
"""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.agents.tsg.logger import log, step, success, error, warn, debug


def _register_turkish_fonts():
    """Turkce karakter destekli fontlari kaydet."""
    import os

    # macOS sistem fontlari
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux (Ubuntu)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("TurkishFont", font_path))
                debug(f"Font kaydedildi: {font_path}")
                return True
            except Exception as e:
                debug(f"Font kayit hatasi ({font_path}): {e}")

    warn("Turkce font bulunamadi, varsayilan font kullanilacak")
    return False


# Font kayit (import sirasinda bir kez calisir)
_TURKISH_FONT_AVAILABLE = _register_turkish_fonts()


class TSGPDFGenerator:
    """
    Profesyonel TSG Gazete sayfasi olusturucu.

    Hackathon icin ozel olarak tasarlanmis:
    - 5 zorunlu baslik formati
    - Turkce karakter destegi
    - Profesyonel tasarim
    """

    # Renkler
    NAVY = HexColor('#1a365d')       # Koyu mavi - header
    GOLD = HexColor('#d69e2e')       # Altin - vurgu
    LIGHT_GRAY = HexColor('#f7fafc') # Acik gri - arka plan
    DARK_GRAY = HexColor('#2d3748')  # Koyu gri - metin
    RED = HexColor('#c53030')        # Kirmizi - onemli

    # Sayfa boyutlari
    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 2 * cm

    # Zorunlu 5 Baslik (Hackathon kurali)
    REQUIRED_FIELDS = [
        ("Firma Unvani", "firma_unvani", "Firma Unvanı"),
        ("Tescil Konusu", "tescil_konusu", "Tescil Konusu"),
        ("Mersis Numarasi", "mersis_numarasi", "Mersis Numarası"),
        ("Yoneticiler", "yoneticiler", "Yöneticiler"),
        ("Imza Yetkilisi", "imza_yetkilisi", "İmza Yetkilisi"),
    ]

    # Ek basliklar (varsa)
    OPTIONAL_FIELDS = [
        ("Ticaret Sicil No", "ticaret_sicil_no", "Ticaret Sicil No"),
        ("Sermaye", "sermaye", "Sermaye"),
        ("Adres", "adres", "Adres"),
        ("Ortaklar", "ortaklar", "Ortaklar"),
        ("Pay Bilgisi", "pay_bilgisi", "Pay Bilgisi"),
    ]

    def __init__(self, output_dir: str = "/tmp/tsg_debug"):
        """
        Args:
            output_dir: PDF dosyalarinin kaydedilecegi dizin
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Font secimi
        if _TURKISH_FONT_AVAILABLE:
            self.font_normal = "TurkishFont"
            self.font_bold = "TurkishFont"  # Bold versiyonu yok, ayni fontu kullan
        else:
            self.font_normal = "Helvetica"
            self.font_bold = "Helvetica-Bold"

    def generate(self, data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        TSG Gazete sayfasi PDF'i olustur.

        Args:
            data: Yapilandirilmis veri
                {
                    "Firma Unvani": "...",
                    "Tescil Konusu": "...",
                    "Mersis Numarasi": "...",
                    "Yoneticiler": ["...", "..."] veya "...",
                    "Imza Yetkilisi": "...",
                    "gazete_no": "11407",
                    "tarih": "3 EYLUL 2025",
                    # Ek basliklar...
                }
            output_path: Cikti dosya yolu (opsiyonel)

        Returns:
            str: Olusturulan PDF dosya yolu
        """
        step("PDF OLUSTURULUYOR")

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{self.output_dir}/tsg_rapor_{timestamp}.pdf"

        try:
            # Canvas olustur
            c = canvas.Canvas(output_path, pagesize=A4)

            # Header ciz
            self._draw_header(c, data)

            # Ana icerik (5 baslik)
            y_position = self._draw_content(c, data)

            # Ek basliklar (varsa)
            y_position = self._draw_optional_fields(c, data, y_position)

            # Footer ciz
            self._draw_footer(c, data)

            # Kaydet
            c.save()

            success(f"PDF olusturuldu: {output_path}")
            return output_path

        except Exception as e:
            error(f"PDF olusturma hatasi: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _draw_header(self, c: canvas.Canvas, data: Dict[str, Any]) -> None:
        """Sayfa header'ini ciz."""
        # Arka plan (navy)
        c.setFillColor(self.NAVY)
        c.rect(0, self.PAGE_HEIGHT - 4*cm, self.PAGE_WIDTH, 4*cm, fill=True)

        # Altin cizgi
        c.setStrokeColor(self.GOLD)
        c.setLineWidth(3)
        c.line(0, self.PAGE_HEIGHT - 4*cm, self.PAGE_WIDTH, self.PAGE_HEIGHT - 4*cm)

        # Ana baslik
        c.setFillColor(white)
        c.setFont(self.font_bold, 20)
        title = "TURKIYE TICARET SICILI GAZETESI"
        title_width = c.stringWidth(title, self.font_bold, 20)
        c.drawString((self.PAGE_WIDTH - title_width) / 2, self.PAGE_HEIGHT - 2*cm, title)

        # Alt baslik (gazete no ve tarih)
        gazete_no = data.get("gazete_no", "N/A")
        tarih = data.get("tarih", datetime.now().strftime("%d.%m.%Y"))

        c.setFont(self.font_normal, 12)
        subtitle = f"Sayi: {gazete_no}  |  {tarih}"
        subtitle_width = c.stringWidth(subtitle, self.font_normal, 12)
        c.drawString((self.PAGE_WIDTH - subtitle_width) / 2, self.PAGE_HEIGHT - 3.2*cm, subtitle)

        # "ILAN BILGILERI" kutusu
        c.setFillColor(self.GOLD)
        box_width = 6 * cm
        box_height = 0.8 * cm
        box_x = (self.PAGE_WIDTH - box_width) / 2
        box_y = self.PAGE_HEIGHT - 5.5 * cm
        c.roundRect(box_x, box_y, box_width, box_height, 3, fill=True)

        c.setFillColor(self.NAVY)
        c.setFont(self.font_bold, 12)
        box_title = "ILAN BILGILERI"
        box_title_width = c.stringWidth(box_title, self.font_bold, 12)
        c.drawString(box_x + (box_width - box_title_width) / 2, box_y + 0.25*cm, box_title)

    def _draw_content(self, c: canvas.Canvas, data: Dict[str, Any]) -> float:
        """
        Ana icerik (5 zorunlu baslik) ciz.

        Returns:
            float: Son y pozisyonu
        """
        y = self.PAGE_HEIGHT - 7 * cm
        left_margin = self.MARGIN + 0.5*cm

        # Her zorunlu baslik icin
        for field_name, field_key, display_name in self.REQUIRED_FIELDS:
            # Deger bul (farkli key formatlarini dene)
            value = self._get_field_value(data, field_key, field_name, display_name)

            if value:
                # Baslik
                c.setFillColor(self.NAVY)
                c.setFont(self.font_bold, 11)
                c.drawString(left_margin, y, f"{display_name}:")

                # Deger
                c.setFillColor(self.DARK_GRAY)
                c.setFont(self.font_normal, 10)

                # Liste ise madde isareti ile yaz
                if isinstance(value, list):
                    y -= 0.5 * cm
                    for item in value:
                        if item:
                            c.drawString(left_margin + 0.5*cm, y, f"* {item}")
                            y -= 0.5 * cm
                else:
                    # Uzun metinleri sar
                    lines = self._wrap_text(str(value), 70)
                    y -= 0.5 * cm
                    for line in lines:
                        c.drawString(left_margin + 0.5*cm, y, line)
                        y -= 0.5 * cm

                y -= 0.3 * cm  # Basliklar arasi bosluk

        # Ayirici cizgi
        c.setStrokeColor(self.LIGHT_GRAY)
        c.setLineWidth(1)
        c.line(self.MARGIN, y, self.PAGE_WIDTH - self.MARGIN, y)
        y -= 0.5 * cm

        return y

    def _draw_optional_fields(self, c: canvas.Canvas, data: Dict[str, Any], y: float) -> float:
        """Opsiyonel alanlari ciz (varsa)."""
        left_margin = self.MARGIN + 0.5*cm

        for field_name, field_key, display_name in self.OPTIONAL_FIELDS:
            value = self._get_field_value(data, field_key, field_name, display_name)

            if value and y > 4*cm:  # Sayfa tasmasi kontrolu
                # Baslik
                c.setFillColor(self.DARK_GRAY)
                c.setFont(self.font_bold, 10)
                c.drawString(left_margin, y, f"{display_name}:")

                # Deger
                c.setFont(self.font_normal, 9)

                if isinstance(value, list):
                    y -= 0.4 * cm
                    for item in value[:5]:  # Max 5 item
                        if item:
                            c.drawString(left_margin + 0.5*cm, y, f"* {item}")
                            y -= 0.4 * cm
                else:
                    lines = self._wrap_text(str(value), 80)
                    y -= 0.4 * cm
                    for line in lines[:3]:  # Max 3 satir
                        c.drawString(left_margin + 0.5*cm, y, line)
                        y -= 0.4 * cm

                y -= 0.2 * cm

        return y

    def _draw_footer(self, c: canvas.Canvas, data: Dict[str, Any]) -> None:
        """Sayfa footer'ini ciz."""
        # Ayirici cizgi
        c.setStrokeColor(self.NAVY)
        c.setLineWidth(2)
        c.line(self.MARGIN, 3*cm, self.PAGE_WIDTH - self.MARGIN, 3*cm)

        # Footer metni
        c.setFillColor(self.DARK_GRAY)
        c.setFont(self.font_normal, 8)

        footer_lines = [
            "Kaynak: Turkiye Ticaret Sicili Gazetesi (tsg.gov.tr)",
            f"Olusturma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "AI Analiz: KKB Hackathon 2024 - Golden Head",
        ]

        y = 2.5 * cm
        for line in footer_lines:
            c.drawString(self.MARGIN, y, line)
            y -= 0.4 * cm

        # Hackathon logosu/damgasi
        c.setFillColor(self.GOLD)
        c.setFont(self.font_bold, 10)
        c.drawRightString(self.PAGE_WIDTH - self.MARGIN, 2.5*cm, "GOLDEN HEAD")

        c.setFillColor(self.DARK_GRAY)
        c.setFont(self.font_normal, 8)
        c.drawRightString(self.PAGE_WIDTH - self.MARGIN, 2*cm, "Hackathon 2024")

    def _get_field_value(self, data: Dict, *keys: str) -> Any:
        """Farkli key formatlarini deneyerek degeri bul."""
        for key in keys:
            # Direkt key
            if key in data:
                return data[key]

            # Turkce karakter varyasyonlari
            key_variations = [
                key,
                key.replace("i", "ı").replace("I", "İ"),
                key.replace("ı", "i").replace("İ", "I"),
                key.lower(),
                key.upper(),
                key.title(),
                key.replace("_", " "),
                key.replace(" ", "_"),
            ]

            for var in key_variations:
                if var in data:
                    return data[var]

        return None

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Uzun metni satirlara bol."""
        if len(text) <= max_chars:
            return [text]

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def to_image(self, pdf_path: str, dpi: int = 150) -> str:
        """
        PDF'i PNG'ye cevir (screenshot olarak kullanilacak).

        Args:
            pdf_path: PDF dosya yolu
            dpi: Cozunurluk (varsayilan 150)

        Returns:
            str: PNG dosya yolu
        """
        step("PDF -> PNG DONUSUMU")

        try:
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path, dpi=dpi)

            if not images:
                raise ValueError("PDF'den gorsel cikarilmadi")

            png_path = pdf_path.replace('.pdf', '.png')
            images[0].save(png_path, 'PNG')

            success(f"PNG olusturuldu: {png_path}")
            return png_path

        except Exception as e:
            error(f"PDF->PNG donusum hatasi: {e}")
            # Fallback: poppler yoksa hata ver
            warn("pdf2image icin 'poppler' kurulu olmali:")
            warn("  macOS: brew install poppler")
            warn("  Ubuntu: apt-get install poppler-utils")
            raise


# Standalone test
if __name__ == "__main__":
    step("TSG PDF Generator Test")

    # Ornek veri
    test_data = {
        "Firma Unvani": "TURKCELL ILETISIM HIZMETLERI A.S.",
        "Tescil Konusu": "Genel Kurul Karari",
        "Mersis Numarasi": "0621003569200018",
        "Yoneticiler": [
            "Ali Veli (Yonetim Kurulu Baskani)",
            "Ahmet Mehmet (Genel Mudur)",
            "Zeynep Fatma (CFO)"
        ],
        "Imza Yetkilisi": "Ali Veli - Munferiden yetkili",
        "gazete_no": "11407",
        "tarih": "3 EYLUL 2025",
        "Ticaret Sicil No": "123456",
        "Sermaye": "10.000.000 TL",
        "Adres": "Maltepe Mah. Buyukdere Cad. No:123 Sisli/Istanbul"
    }

    generator = TSGPDFGenerator()

    # PDF olustur
    pdf_path = generator.generate(test_data)
    print(f"\nPDF: {pdf_path}")

    # PNG'ye cevir
    try:
        png_path = generator.to_image(pdf_path)
        print(f"PNG: {png_path}")
    except Exception as e:
        warn(f"PNG donusumu basarisiz: {e}")

    success("Test tamamlandi!")
