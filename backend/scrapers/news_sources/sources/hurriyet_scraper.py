"""
Hurriyet Gazetesi News Scraper
Turkiye'nin en buyuk gazetelerinden biri

URL: https://www.hurriyet.com.tr
Search: Tag-based crawl (/haberleri/{keyword})
"""
from typing import List, Dict, Optional
import urllib.parse
import re

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class HurriyetScraper(BaseNewsScraper):
    """
    Hurriyet Gazetesi scraper.

    Ozellikler:
    - Tier 2 kaynak (genis kapsam)
    - Tag-based crawl (/haberleri/{keyword})
    - Firma adini slug'a cevirir
    - Generic LLM extraction (BaseNewsScraper'dan)
    """

    BASE_URL = "https://www.hurriyet.com.tr"
    NAME = "Hürriyet"

    def _slugify(self, text: str) -> str:
        """
        Firma adini URL-safe slug'a cevir.

        Ornek: "Türk Hava Yolları" -> "turk-hava-yollari"
        """
        # Turkce karakterleri cevir
        tr_chars = {
            'ç': 'c', 'Ç': 'c',
            'ğ': 'g', 'Ğ': 'g',
            'ı': 'i', 'İ': 'i',
            'ö': 'o', 'Ö': 'o',
            'ş': 's', 'Ş': 's',
            'ü': 'u', 'Ü': 'u',
        }

        slug = text.lower()
        for tr, en in tr_chars.items():
            slug = slug.replace(tr, en)

        # Alfanumerik olmayan karakterleri tire ile degistir
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Bastaki ve sondaki tireleri kaldir
        slug = slug.strip('-')
        # Birden fazla tireyi tek tireye indir
        slug = re.sub(r'-+', '-', slug)

        return slug

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        Hurriyet'te firma adi ile arama yap.

        Strategy: Tag-based crawl
        URL Pattern: /haberleri/{slugified-company-name}

        Args:
            company_name: Firma adi
            max_results: Maksimum sonuc sayisi

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Hürriyet arama başlıyor: '{company_name}'")

            # Firma adini slug'a cevir
            slug = self._slugify(company_name)
            tag_url = f"{self.BASE_URL}/haberleri/{slug}"

            log(f"Tag URL: {tag_url}")
            if not await self._safe_goto(tag_url):
                # Alternatif: Ekonomi sayfasinda ara
                warn(f"Tag sayfası bulunamadı, ekonomi kategorisi deneniyor...")
                ekon_url = f"{self.BASE_URL}/ekonomi/"
                if not await self._safe_goto(ekon_url):
                    error("Hürriyet sayfası açılamadı")
                    return []

            await self._delay(3.0)  # Sonuçlar yüklensin
            debug("Sayfa yüklendi, sonuçlar parse ediliyor...")

            # Sonuçları parse et
            results = await self._parse_search_results(max_results, company_name)

            if not results:
                warn(f"Hürriyet'te '{company_name}' için sonuç bulunamadı")
                return []

            success(f"Hürriyet: {len(results)} sonuç bulundu")
            return results

        except Exception as e:
            error(f"Hürriyet search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int, company_name: str) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Hurriyet URL pattern: /kategori/haber-baslik-ID
        Ornek: /ekonomi/turk-hava-yollari-yeni-ucak-41234567

        FIX: Relevance filter KALDIRILDI!
        Tag sayfası (/haberleri/{slug}) zaten firma ile ilgili haberleri listeliyor.
        Ekstra keyword filtering gereksiz ve sonuçları yanlışlıkla reddediyor.
        """
        results = []

        try:
            # ARAŞTIRMA SONUCU: Hürriyet URL pattern: /[kategori]/[slug]-[8-digit-ID]
            # Örnek: /gundem/thy-ucagi-havalandi-42978760
            link_patterns = [
                "a[href^='/gundem/']",               # Gündem kategorisi
                "a[href^='/ekonomi/']",              # Ekonomi kategorisi
                "a[href^='/dunya/']",                # Dünya kategorisi
                "article a[href^='/']",              # Article içindeki linkler
                "h3 a[href^='/']",                   # Başlık linkleri (h3)
                "h2 a[href^='/']",                   # Başlık linkleri (h2)
            ]

            all_links = []
            for pattern in link_patterns:
                links = await self.page.query_selector_all(pattern)
                if links:
                    debug(f"'{pattern}' ile {len(links)} link bulundu")
                    all_links.extend(links)
                    if len(all_links) >= max_results * 3:
                        break

            if not all_links:
                warn("Spesifik pattern bulunamadı, genel link arama yapılıyor...")
                all_links = await self.page.query_selector_all("a[href*='hurriyet.com.tr']")

            if not all_links:
                warn("Sonuç sayfasında link bulunamadı")
                return []

            # Linkleri filtrele ve işle
            excluded_paths = ['/haberleri/', '/kategori/', '/etiket/', '/yazar/', '/galeri/', '/video/', '/index/']
            seen_urls = set()

            for link in all_links:
                if len(results) >= max_results:
                    break

                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # Kategori sayfalarını exclude et
                    if any(excl in href for excl in excluded_paths):
                        continue

                    # ARAŞTIRMA SONUCU: Hürriyet haberleri 8 haneli numeric ID ile biter
                    # Örnek: -42978760
                    last_part = href.rstrip('/').split('/')[-1]
                    if not re.search(r'-\d{7,9}$', last_part):
                        debug(f"ID pattern eşleşmedi: {href}")
                        continue

                    # Full URL
                    if href.startswith("/"):
                        url = self.BASE_URL + href
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue

                    # Başlık al (duplicate kontrolünden önce!)
                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else ""

                    # Çok kısa başlıkları atla
                    if len(title) < 15:
                        continue

                    # Duplicate kontrolü (title kontrolünden SONRA!)
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # FIX: Relevance check KALDIRILDI!
                    # Tag sayfası zaten firma ile ilgili haberleri listeliyor.
                    # Sadece URL pattern validation yeterli.

                    results.append({
                        "title": title,
                        "url": url,
                        "date": "unknown",
                        "snippet": title[:200]
                    })
                    debug(f"Sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"Sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with HurriyetScraper() as scraper:
            # Test arama
            results = await scraper.search("Türk Hava Yolları", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

            # Test detail (ilk haber)
            if results:
                print("İlk haberin detayı alınıyor...")
                detail = await scraper.get_article_detail(results[0]['url'])

                if detail:
                    print(f"\nTitle: {detail['title']}")
                    print(f"Date: {detail['date']}")
                    print(f"Text: {detail['text'][:200]}...")
                    print(f"Image: {detail['image_url']}")
                else:
                    print("Detay alınamadı!")

    asyncio.run(test())
