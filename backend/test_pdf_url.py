#!/usr/bin/env python3
"""
TSG PDF URL Extraction Test - v7.2
Amaç: object[data] veya embed[src]'den PDF URL'sini çekip indir
"""

import asyncio
import sys
sys.path.insert(0, "/Users/yamacbezirgan/Desktop/kkb-hackathon-goldenhead/backend")

from pathlib import Path
from app.agents.tsg_scraper import TSGScraper

DEBUG_DIR = Path("/tmp/tsg_debug")
DEBUG_DIR.mkdir(exist_ok=True)


async def test_pdf_url_extraction():
    """Mevcut scraper ile login yap, sonra PDF URL extraction test et."""

    print("=" * 60)
    print("TSG PDF URL Extraction Test - v7.2")
    print("=" * 60)

    scraper = TSGScraper()

    try:
        # 1. Browser baslatma
        print("\n[1] Browser baslatiliyor...")
        await scraper._init_browser()

        # 2. Login (CAPTCHA dahil)
        print("\n[2] Login yapiliyor...")
        login_ok = await scraper.login()
        if not login_ok:
            print("LOGIN BASARISIZ!")
            return False
        print("LOGIN OK!")

        # 3-4. Firma ara (search_company icinde sayfa yonlendirmesi var)
        print("\n[3-4] Turkcell araniyor...")
        results = await scraper.search_company("Turkcell")
        if not results:
            print("ARAMA SONUCU YOK!")
            return False
        print(f"Bulunan: {len(results)} sonuc")

        # 5. Ilk PDF ikonuna tikla ve popup bekle
        print("\n[5] PDF ikonuna tiklanarak popup aciliyor...")

        # Tablodaki ilk satiri bul
        rows = await scraper.page.query_selector_all("table.table tbody tr")
        if not rows:
            rows = await scraper.page.query_selector_all("table tbody tr")

        if not rows:
            print("TABLO SATIRI BULUNAMADI!")
            return False

        print(f"Tablo satirlari: {len(rows)}")

        # Ilk satirdan PDF linkini bul
        cells = await rows[0].query_selector_all("td")
        if len(cells) < 8:
            print(f"KOLON SAYISI YETERSIZ: {len(cells)}")
            return False

        pdf_cell = cells[7]  # 8. kolon = Gazete
        pdf_link = await pdf_cell.query_selector("a")

        if not pdf_link:
            print("PDF LINKI BULUNAMADI!")
            cell_html = await pdf_cell.inner_html()
            print(f"Cell HTML: {cell_html[:200]}")
            return False

        # 6. Popup bekleyerek tikla
        print("\n[6] PDF ikonuna tiklanip popup bekleniyor...")

        try:
            async with scraper.page.context.expect_page(timeout=10000) as popup_info:
                await pdf_link.click()

            popup = await popup_info.value
            print("POPUP ACILDI!")

            # Sayfa yuklensin
            await popup.wait_for_load_state("networkidle", timeout=15000)

            # Screenshot al
            await popup.screenshot(path=str(DEBUG_DIR / "popup_viewer.png"))
            print(f"Screenshot: {DEBUG_DIR / 'popup_viewer.png'}")

            # 7. PDF URL'sini bul (YENİ YAKLASIM!)
            print("\n[7] PDF URL araniyor (object/embed/iframe)...")

            pdf_url = None

            # object[data] dene
            obj = await popup.query_selector("object[data*='.pdf']")
            if obj:
                pdf_url = await obj.get_attribute("data")
                print(f"PDF URL (object): {pdf_url}")

            if not pdf_url:
                # embed[src] dene
                embed = await popup.query_selector("embed[src*='.pdf']")
                if embed:
                    pdf_url = await embed.get_attribute("src")
                    print(f"PDF URL (embed): {pdf_url}")

            if not pdf_url:
                # iframe dene
                iframe = await popup.query_selector("iframe[src*='.pdf']")
                if iframe:
                    pdf_url = await iframe.get_attribute("src")
                    print(f"PDF URL (iframe): {pdf_url}")

            if not pdf_url:
                # object veya embed, .pdf olmadan
                obj2 = await popup.query_selector("object[data*='gazete']")
                if obj2:
                    pdf_url = await obj2.get_attribute("data")
                    print(f"PDF URL (object-gazete): {pdf_url}")

                embed2 = await popup.query_selector("embed[src*='gazete']")
                if embed2:
                    pdf_url = await embed2.get_attribute("src")
                    print(f"PDF URL (embed-gazete): {pdf_url}")

            if not pdf_url:
                # Tum object ve embed'leri listele
                print("\nTum object'ler:")
                all_obj = await popup.query_selector_all("object")
                for o in all_obj:
                    data = await o.get_attribute("data")
                    print(f"  - {data}")

                print("\nTum embed'ler:")
                all_embed = await popup.query_selector_all("embed")
                for e in all_embed:
                    src = await e.get_attribute("src")
                    print(f"  - {src}")

                # Page HTML'i debug icin
                html = await popup.content()
                with open(DEBUG_DIR / "popup_html.txt", "w") as f:
                    f.write(html)
                print(f"\nPopup HTML: {DEBUG_DIR / 'popup_html.txt'}")

                print("\nPDF URL BULUNAMADI!")
                await popup.close()
                return False

            # 8. PDF'i indir
            print("\n[8] PDF indiriliyor...")

            # Tam URL yap
            if not pdf_url.startswith("http"):
                full_url = f"https://www.ticaretsicil.gov.tr{pdf_url}"
            else:
                full_url = pdf_url

            print(f"Tam URL: {full_url}")

            # page.request.get ile indir (session cookie'leri korunur)
            resp = await popup.request.get(full_url)

            if resp.ok:
                pdf_bytes = await resp.body()

                # PDF dosyasina kaydet
                pdf_path = DEBUG_DIR / "test_pdf.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                print(f"\nBASARILI!")
                print(f"PDF boyutu: {len(pdf_bytes)} bytes")
                print(f"PDF dosyasi: {pdf_path}")

                # PDF mi kontrol et
                if pdf_bytes[:4] == b'%PDF':
                    print("PDF HEADER DOGRU! (%PDF)")
                    return True
                else:
                    print(f"UYARI: PDF header beklenmiyor: {pdf_bytes[:20]}")
                    return False
            else:
                print(f"HTTP HATA: {resp.status}")
                return False

            await popup.close()

        except Exception as popup_err:
            print(f"POPUP HATASI: {popup_err}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"\nHATA: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Browser'i kapat
        try:
            if scraper.browser:
                await scraper.browser.close()
        except:
            pass


if __name__ == "__main__":
    result = asyncio.run(test_pdf_url_extraction())
    print("\n" + "=" * 60)
    if result:
        print("TEST BASARILI!")
    else:
        print("TEST BASARISIZ!")
    print("=" * 60)
    sys.exit(0 if result else 1)
