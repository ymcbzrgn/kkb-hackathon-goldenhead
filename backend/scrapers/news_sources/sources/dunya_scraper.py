"""
Dunya Gazetesi News Scraper
Turkiye'nin oncu ekonomi gazetesi

URL: https://www.dunya.com
Search: /ara?key=QUERY
"""
import re
import urllib.parse
from typing import List, Dict, Optional

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class DunyaScraper(BaseNewsScraper):
    """
    Dunya Gazetesi scraper.

    Ozellikler:
    - Tier 1 kaynak (ekonomi odakli)
    - Direct URL search (/ara?key=)
    - Generic LLM extraction (BaseNewsScraper'dan)
    """

    BASE_URL = "https://www.dunya.com"
    SEARCH_URL = "https://www.dunya.com/ara"
    NAME = "Dünya Gazetesi"

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        Dunya'da firma adi ile arama yap.

        URL Pattern: /ara?key=QUERY

        Args:
            company_name: Firma adi
            max_results: Maksimum sonuc sayisi

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Dünya arama başlıyor: '{company_name}'")

            # Direct URL ile arama
            encoded_query = urllib.parse.quote(company_name)
            search_url = f"{self.SEARCH_URL}?key={encoded_query}"

            log(f"Search URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("Dünya arama URL'i açılamadı")
                return []

            await self._delay(3.0)  # Sonuçlar yüklensin
            debug("Arama sayfası yüklendi, sonuçlar parse ediliyor...")

            # Sonuçları parse et
            results = await self._parse_search_results(max_results)

            if not results:
                warn(f"Dünya'da '{company_name}' için sonuç bulunamadı")
                return []

            success(f"Dünya: {len(results)} sonuç bulundu")
            return results

        except Exception as e:
            error(f"Dünya search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Dunya URL pattern: /kategori/haber-baslik-haberi-ID
        Örnek: /ekonomi/turk-telekom-yeni-yatirim-haberi-123456
        """
        results = []

        try:
            # Dünya'da haber linkleri genellikle bu pattern'lerde
            link_patterns = [
                "article a[href*='-haberi-']",      # -haberi- içeren linkler (en güvenilir)
                "div.news-item a[href*='dunya.com']",
                "a[href*='/ekonomi/']",
                "a[href*='/gundem/']",
                "a[href*='/sektorler/']",
                "a[href*='-haberi-']"               # Genel -haberi- pattern
            ]

            all_links = []
            for pattern in link_patterns:
                links = await self.page.query_selector_all(pattern)
                if links:
                    debug(f"'{pattern}' ile {len(links)} link bulundu")
                    all_links.extend(links)
                    if len(all_links) >= max_results * 2:  # Yeterli link bulundu
                        break

            if not all_links:
                # Fallback: tüm a[href] linklerini al ve filtrele
                warn("Spesifik pattern bulunamadı, genel link arama yapılıyor...")
                all_links = await self.page.query_selector_all("a[href*='dunya.com'], a[href^='/']")

            if not all_links:
                warn("Sonuç sayfasında link bulunamadı")
                return []

            # Linkleri filtrele ve işle
            excluded_paths = ['/kategori', '/etiket', '/yazar', '/galeri', '/video', '/rss']
            seen_urls = set()

            for link in all_links:
                if len(results) >= max_results:
                    break

                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # Kategori/yazar sayfalarını exclude et
                    if any(excl in href for excl in excluded_paths):
                        continue

                    # ARAŞTIRMA SONUCU: Dünya haberleri "haberi-[ID]" pattern'i ile biter
                    # Örnek: turk-telekom-haberi-806118
                    if not re.search(r'haberi-\d+', href):
                        # Fallback: En az bir rakam içermeli
                        if not any(c.isdigit() for c in href.split('/')[-1]):
                            continue

                    # Full URL oluştur
                    if href.startswith("/"):
                        url = self.BASE_URL + href
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue

                    # Duplicate kontrolü
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Başlık al
                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else "Unknown"

                    # Çok kısa başlıkları atla
                    if len(title) < 15:
                        continue

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
        async with DunyaScraper() as scraper:
            # Test arama
            results = await scraper.search("ASELSAN", max_results=3)

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
