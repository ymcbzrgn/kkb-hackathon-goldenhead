"""
Ekonomim News Scraper
Turkiye ekonomi haberleri sitesi

URL: https://www.ekonomim.com
Search: /ara?key=QUERY (Direct URL search)
"""
import urllib.parse
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class EkonomimScraper(BaseNewsScraper):
    """
    Ekonomim scraper.

    Ozellikler:
    - Tier 3 kaynak (ekonomi odakli)
    - Direct URL search (/ara?key=)
    - Generic LLM extraction (BaseNewsScraper'dan)
    """

    BASE_URL = "https://www.ekonomim.com"
    SEARCH_URL = "https://www.ekonomim.com/ara"
    NAME = "Ekonomim"

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        Ekonomim'de firma adi ile arama yap.

        URL Pattern: /ara?key=QUERY

        Args:
            company_name: Firma adi
            max_results: Maksimum sonuc sayisi

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Ekonomim arama başlıyor: '{company_name}'")

            # Direct URL ile arama
            encoded_query = urllib.parse.quote(company_name)
            search_url = f"{self.SEARCH_URL}?key={encoded_query}"

            log(f"Search URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("Ekonomim arama URL'i açılamadı")
                return []

            await self._delay(3.0)  # JS sonuçları yüklensin
            debug("Arama sayfası yüklendi, sonuçlar parse ediliyor...")

            # Sonuçları parse et
            results = await self._parse_search_results(max_results)

            if not results:
                warn(f"Ekonomim'de '{company_name}' için sonuç bulunamadı")
                return []

            success(f"Ekonomim: {len(results)} sonuç bulundu")
            return results

        except Exception as e:
            error(f"Ekonomim search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Ekonomim URL pattern: -haberi- veya numeric ID
        """
        results = []

        try:
            # Ekonomim haber link pattern'leri
            link_patterns = [
                "a[href*='-haberi-']",           # Haber pattern (en güvenilir)
                "h3 a[href^='/']",               # Başlık linkleri
                "h4 a[href^='/']",
                "article a[href^='/']",
                "a[href^='/sirketler/']",
                "a[href^='/sektorler/']",
            ]

            all_links = []
            for pattern in link_patterns:
                links = await self.page.query_selector_all(pattern)
                if links:
                    debug(f"'{pattern}' ile {len(links)} link bulundu")
                    all_links.extend(links)
                    if len(all_links) >= max_results * 2:
                        break

            if not all_links:
                # Fallback: tüm linkler
                all_links = await self.page.query_selector_all("a[href^='/']")

            if not all_links:
                warn("Sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/kategori/', '/etiket/', '/yazar/', '/galeri/', '/video/', '/sayfa/']
            seen_urls = set()

            for link in all_links:
                if len(results) >= max_results:
                    break

                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    if any(excl in href for excl in excluded_paths):
                        continue

                    # Haber URL kontrolü
                    if '-haberi-' not in href and not any(c.isdigit() for c in href.split('/')[-1]):
                        continue

                    # Full URL
                    if href.startswith("/"):
                        url = self.BASE_URL + href
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else "Unknown"

                    if len(title) < 15:
                        continue

                    results.append({
                        "title": title,
                        "url": url,
                        "date": "unknown",
                        "snippet": title[:200]
                    })
                    debug(f"Sonuç {len(results)}: {title[:50]}...")

                except Exception:
                    continue

            return results

        except Exception as e:
            error(f"Sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with EkonomimScraper() as scraper:
            # Test arama
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
