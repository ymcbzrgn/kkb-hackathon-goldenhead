"""
Milliyet News Scraper
Demirören Grubu - 70+ yıllık güvenilir gazete
URL: https://www.milliyet.com.tr
Search: /haberleri/SLUG (Tag-based)

DOĞRULANMIŞ: 21K+ THY haberi arşivde!
"""
import re
from typing import List, Dict

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class MilliyetScraper(BaseNewsScraper):
    """
    Milliyet News Scraper.

    Özellikler:
    - Demirören Grubu medyası (70+ yıllık)
    - Tag-based arama (/haberleri/SLUG)
    - Zengin arşiv (21K+ THY haberi!)
    """

    BASE_URL = "https://www.milliyet.com.tr"
    NAME = "Milliyet"

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
        Milliyet'te firma adı ile arama yap.

        Strategy: Tag-based URL (/haberleri/SLUG)

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Milliyet arama başlıyor: '{company_name}'")

            # Tag-based search: /haberleri/SLUG
            slug = self._slugify(company_name)
            search_url = f"{self.BASE_URL}/haberleri/{slug}"

            log(f"Milliyet arama URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("Milliyet arama URL'i açılamadı")
                return []

            await self._delay(3.0)
            results = await self._parse_search_results(max_results)

            if results:
                success(f"Milliyet: {len(results)} sonuç bulundu")
            else:
                warn(f"Milliyet'te '{company_name}' için sonuç bulunamadı")

            return results

        except Exception as e:
            error(f"Milliyet search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Milliyet URL format: /kategori/baslik-slug-7XXXXXX
        Örnek: /ekonomi/thy-ucus-7123456
        """
        results = []

        try:
            # Milliyet kategori linkleri (skorer, nabiz dahil)
            link_patterns = [
                "a[href*='/ekonomi/']",
                "a[href*='/gundem/']",
                "a[href*='/siyaset/']",
                "a[href*='/teknoloji/']",
                "a[href*='/skorer/']",
                "a[href*='/nabiz/']",
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
                warn("Milliyet sonuç sayfasında link bulunamadı")
                return []

            excluded_paths = ['/galeri/', '/video/', '/foto/', '/yazarlar/', '/skorer/']
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

                    # Milliyet haber URL: 7 haneli ID ile biter (örn: -7497604)
                    if not re.search(r'-\d{7}$', href):
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
                    debug(f"Milliyet sonuç {len(results)}: {title[:50]}...")

                except Exception as e:
                    debug(f"Link parse hatası: {e}")
                    continue

            return results

        except Exception as e:
            error(f"Milliyet sonuç parse hatası: {e}")
            return []


# Test
if __name__ == "__main__":
    import asyncio

    async def test():
        async with MilliyetScraper() as scraper:
            results = await scraper.search("THY", max_results=3)

            print(f"\n{len(results)} sonuç bulundu:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['url']}\n")

    asyncio.run(test())
