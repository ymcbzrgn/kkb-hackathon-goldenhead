"""
CNN Türk News Scraper
Demirören Grubu - Uluslararası marka
URL: https://www.cnnturk.com
Search: /haberleri/SLUG (Tag-based)

DOĞRULANMIŞ: Uluslararası marka güvenilirliği!
"""
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class CNNTurkScraper(BaseNewsScraper):
    """
    CNN Türk News Scraper.

    Özellikler:
    - Demirören Grubu (uluslararası marka)
    - Tag-based arama (/haberleri/SLUG)
    - JS-heavy site, uzun delay gerekli
    """

    BASE_URL = "https://www.cnnturk.com"
    NAME = "CNN Türk"

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
        CNN Türk'te firma adı ile arama yap.

        Strategy: Tag-based URL (/haberleri/SLUG)

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"CNN Türk arama başlıyor: '{company_name}'")

            # Tag-based search: /haberleri/SLUG
            slug = self._slugify(company_name)
            search_url = f"{self.BASE_URL}/haberleri/{slug}"

            log(f"CNN Türk arama URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("CNN Türk arama URL'i açılamadı")
                return []

            # JS rendering için uzun bekle
            await self._delay(5.0)
            results = await self._parse_search_results(max_results)

            if results:
                success(f"CNN Türk: {len(results)} sonuç bulundu")
            else:
                warn(f"CNN Türk'te '{company_name}' için sonuç bulunamadı")

            return results

        except Exception as e:
            error(f"CNN Türk search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        CNN Türk URL pattern: /kategori/slug-haberi
        """
        results = []

        try:
            # CNN Türk kategori linkleri
            link_patterns = [
                "a[href*='/ekonomi/']",
                "a[href*='/turkiye/']",
                "a[href*='/dunya/']",
                "a[href*='/teknoloji/']",
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
                warn("CNN Türk sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/galeri/', '/video/', '/fotogaleri/', '/yazarlar/', '/canli/']
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

                    # Haber URL kontrolü - kategori içermeli
                    if not any(cat in href for cat in ['/ekonomi/', '/turkiye/', '/dunya/', '/spor/', '/teknoloji/']):
                        continue

                    # Çok kısa URL'ler kategori sayfası olabilir
                    if href.count('/') < 3:
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
                    debug(f"CNN Türk sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"CNN Türk sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with CNNTurkScraper() as scraper:
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
