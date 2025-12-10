"""
NTV News Scraper
Doğuş Grubu - Çok güvenilir kaynak
URL: https://www.ntv.com.tr
Search: /ara/SLUG (Tag-based)

DOĞRULANMIŞ: 4+ haber THY aramasında!
"""
import re
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class NTVScraper(BaseNewsScraper):
    """
    NTV News Scraper.

    Özellikler:
    - Doğuş Grubu medyası
    - Tag-based arama (/ara/SLUG)
    - 7 haneli haber ID pattern
    """

    BASE_URL = "https://www.ntv.com.tr"
    NAME = "NTV"

    def _slugify(self, text: str) -> str:
        """Firma adını URL-uyumlu slug'a çevir."""
        return (text.lower()
                .replace(' ', '-')
                .replace('ı', 'i')
                .replace('ş', 's')
                .replace('ğ', 'g')
                .replace('ü', 'u')
                .replace('ö', 'o')
                .replace('ç', 'c'))

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        NTV'de firma adı ile arama yap.

        Strategy: Tag-based URL (/ara/SLUG)

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"NTV arama başlıyor: '{company_name}'")

            # Tag-based search: /ara/SLUG
            slug = self._slugify(company_name)
            search_url = f"{self.BASE_URL}/ara/{slug}"

            log(f"NTV arama URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("NTV arama URL'i açılamadı")
                return []

            await self._delay(3.0)
            results = await self._parse_search_results(max_results)

            if results:
                success(f"NTV: {len(results)} sonuç bulundu")
            else:
                warn(f"NTV'de '{company_name}' için sonuç bulunamadı")

            return results

        except Exception as e:
            error(f"NTV search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        NTV URL pattern: /kategori/slug-7haneli_id
        Örnek: /ntvpara/thy-haberleri-1234567
        """
        results = []

        try:
            # NTV kategori linkleri
            link_patterns = [
                "a[href*='/ntvpara/']",
                "a[href*='/turkiye/']",
                "a[href*='/dunya/']",
                "a[href*='/ekonomi/']",
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
                warn("NTV sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/galeri/', '/video/', '/fotogaleri/', '/canli/']
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

                    # NTV haber URL: 7 haneli ID ile biter (1600000-1799999 aralığı)
                    if not re.search(r'-1[67]\d{5}$', href):
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
                    debug(f"NTV sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"NTV sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with NTVScraper() as scraper:
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
