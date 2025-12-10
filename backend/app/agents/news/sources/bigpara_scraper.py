"""
Bigpara (Hürriyet) News Scraper
Ekonomi/Finans odaklı - Tier 1 kaynak
URL: https://bigpara.hurriyet.com.tr
Search: /haberler/ekonomi-haberleri/?searchKey=QUERY

HACKATHON: Finans haberleri için kritik kaynak!
"""
import urllib.parse
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class BigparaScraper(BaseNewsScraper):
    """
    Bigpara News Scraper.

    Özellikler:
    - Hürriyet'in finans platformu
    - Direct URL search (?searchKey=)
    - Ekonomi/borsa haberleri odaklı
    """

    BASE_URL = "https://bigpara.hurriyet.com.tr"
    SEARCH_URL = "https://bigpara.hurriyet.com.tr/haberler/ekonomi-haberleri/"
    NAME = "Bigpara"

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        Bigpara'da firma adı ile arama yap.

        Strategy: Direct URL search (?searchKey=QUERY)

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Bigpara arama başlıyor: '{company_name}'")

            encoded_query = urllib.parse.quote(company_name)
            search_url = f"{self.SEARCH_URL}?searchKey={encoded_query}"

            log(f"Bigpara arama URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("Bigpara arama URL'i açılamadı")
                return []

            await self._delay(3.0)
            results = await self._parse_search_results(max_results)

            if results:
                success(f"Bigpara: {len(results)} sonuç bulundu")
            else:
                warn(f"Bigpara'da '{company_name}' için sonuç bulunamadı")

            return results

        except Exception as e:
            error(f"Bigpara search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Bigpara URL format: /ekonomi-haberleri/baslik-metni_ID######/
        """
        results = []

        try:
            # Bigpara haber link pattern'leri
            link_patterns = [
                "a[href*='/ekonomi-haberleri/'][href*='_ID']",
                "a[href*='-haberleri/']",
                "h3 a[href^='/']",
                "article a[href^='/']",
            ]

            all_links = []
            for pattern in link_patterns:
                try:
                    links = await self.page.query_selector_all(pattern)
                    if links:
                        debug(f"'{pattern}' ile {len(links)} link bulundu")
                        all_links.extend(links)
                        if len(all_links) >= max_results * 3:
                            break
                except Exception:
                    continue

            if not all_links:
                warn("Bigpara sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/galeri/', '/video/', '/canli/', '/borsa/', '/doviz/', '/altin/']
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

                    # Haber URL kontrolü (_ID pattern veya -haberleri/)
                    if '_ID' not in href and '-haberleri/' not in href:
                        continue

                    url = self.BASE_URL + href if href.startswith("/") else href

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else ""

                    if len(title) < 15:
                        continue

                    results.append({
                        "title": title,
                        "url": url,
                        "date": "unknown",
                        "snippet": title[:200]
                    })
                    debug(f"Bigpara sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"Bigpara sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with BigparaScraper() as scraper:
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
