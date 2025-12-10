"""
TRT Haber News Scraper
Devlet kanalı - En güvenilir kaynak
URL: https://www.trthaber.com
Search: /etiket/SLUG/ (Tag-based)

DOĞRULANMIŞ: Devlet kanalı, resmi haberler!
"""
import re
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class TRTHaberScraper(BaseNewsScraper):
    """
    TRT Haber News Scraper.

    Özellikler:
    - Devlet kanalı (en güvenilir)
    - Tag-based arama (/etiket/SLUG/)
    - Resmi açıklamalar için kritik
    """

    BASE_URL = "https://www.trthaber.com"
    NAME = "TRT Haber"

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
        TRT Haber'de firma adı ile arama yap.

        Strategy: Tag-based URL (/etiket/SLUG/)

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"TRT Haber arama başlıyor: '{company_name}'")

            # Tag-based search: /etiket/SLUG/
            slug = self._slugify(company_name)
            search_url = f"{self.BASE_URL}/etiket/{slug}/"

            log(f"TRT Haber arama URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("TRT Haber arama URL'i açılamadı")
                return []

            await self._delay(3.0)
            results = await self._parse_search_results(max_results)

            if results:
                success(f"TRT Haber: {len(results)} sonuç bulundu")
            else:
                warn(f"TRT Haber'de '{company_name}' için sonuç bulunamadı")

            return results

        except Exception as e:
            error(f"TRT Haber search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        TRT Haber URL pattern: /haber/kategori/slug-id.html
        Örnek: /haber/ekonomi/thy-aciklama-12345.html
        """
        results = []

        try:
            # TRT Haber linkleri - .html ile biten tüm /haber/ linkleri
            link_patterns = [
                "a[href*='/haber/'][href$='.html']",  # En güvenilir pattern!
                "a[href*='/haber/ekonomi/']",
                "a[href*='/haber/gundem/']",
                "a[href*='/haber/turkiye/']",
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
                warn("TRT Haber sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/galeri/', '/video/', '/canli/', '/spor/']
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

                    # TRT Haber: /haber/kategori/baslik-ID.html formatı
                    # ID 6 haneli, .html ile biter
                    if not re.search(r'-\d{6}\.html$', href):
                        continue

                    # ÖNCE title kontrolü (resim linkleri boş title'lı!)
                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else ""

                    if len(title) < 15:
                        continue  # Resim linki, atla

                    url = self.BASE_URL + href if href.startswith("/") else href

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    results.append({
                        "title": title,
                        "url": url,
                        "date": "unknown",
                        "snippet": title[:200]
                    })
                    debug(f"TRT Haber sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"TRT Haber sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with TRTHaberScraper() as scraper:
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
