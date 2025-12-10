"""
Sozcu Gazetesi News Scraper
Turkiye'nin yaygin okunan gazetelerinden biri

URL: https://www.sozcu.com.tr
Search: /arama?search=QUERY
"""
import re
import urllib.parse
from typing import List, Dict, Optional

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class SozcuScraper(BaseNewsScraper):
    """
    Sozcu Gazetesi scraper.

    Ozellikler:
    - Tier 1 kaynak (genis okuyucu kitlesi)
    - Direct URL search (/arama?search=)
    - Generic LLM extraction (BaseNewsScraper'dan)
    """

    BASE_URL = "https://www.sozcu.com.tr"
    SEARCH_URL = "https://www.sozcu.com.tr/arama"
    NAME = "Sözcü"

    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        Sozcu'de firma adi ile arama yap.

        URL Pattern: /arama?search=QUERY

        Args:
            company_name: Firma adi
            max_results: Maksimum sonuc sayisi

        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"Sözcü arama başlıyor: '{company_name}'")

            # Direct URL ile arama
            encoded_query = urllib.parse.quote(company_name)
            search_url = f"{self.SEARCH_URL}?search={encoded_query}"

            log(f"Search URL: {search_url}")
            if not await self._safe_goto(search_url):
                error("Sözcü arama URL'i açılamadı")
                return []

            await self._delay(3.0)  # Sonuçlar yüklensin
            debug("Arama sayfası yüklendi, sonuçlar parse ediliyor...")

            # Sonuçları parse et
            results = await self._parse_search_results(max_results)

            if not results:
                warn(f"Sözcü'de '{company_name}' için sonuç bulunamadı")
                return []

            success(f"Sözcü: {len(results)} sonuç bulundu")
            return results

        except Exception as e:
            error(f"Sözcü search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Sozcu URL pattern: /haber-baslik-pID veya /kategori/haber-baslik-haberi-ID
        Örnek: /ekonomi/turk-telekom-yeni-yatirim-haberi-p123456
        """
        results = []

        try:
            # ARAŞTIRMA SONUCU: Sözcü'de linkler relative (/slug-pID)
            # URL Pattern: /haber-basligi-pNNNNNN (6+ haneli ID)
            link_patterns = [
                "a[href^='/'][href*='-p']",              # Relative + -pID pattern (EN GÜVENİLİR)
                "article a[href^='/']",                   # Article içindeki relative linkler
                "a[href*='-p'][href*='sozcu.com.tr']",    # Absolute -pID pattern
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
                # Fallback: tüm a[href] linklerini al
                warn("Spesifik pattern bulunamadı, genel link arama yapılıyor...")
                all_links = await self.page.query_selector_all("a[href*='sozcu.com.tr']")

            if not all_links:
                warn("Sonuç sayfasında link bulunamadı")
                return []

            # Linkleri filtrele ve işle
            # KRITIK: Footer/header/policy linklerini exclude et
            excluded_paths = [
                '/arama', '/etiket/', '/yazar/', '/galeri/', '/video/', '/kategori',
                '/hukuk/', '/cerez', '/gizlilik', '/kvkk', '/aydinlatma',
                '/iletisim', '/hakkimizda', '/kunye', '/reklam', '/sozlesme',
                '/uyelik', '/abone', '/login', '/politika'
            ]
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

                    # ARAŞTIRMA SONUCU: Sözcü haberleri -p[5-6 digit] ile biter
                    # Örnek: /thy-ile-anlasmasi-p266626
                    # Regex ile daha sıkı validation
                    if not re.search(r'-p\d{5,}$', href) and not re.search(r'-wp\d+$', href):
                        # Fallback: haberi içermeli veya en az bir rakam içermeli
                        if 'haberi' not in href:
                            if not any(c.isdigit() for c in href.split('/')[-1]):
                                debug(f"Pattern eşleşmedi: {href}")
                                continue

                    # Full URL
                    if href.startswith("/"):
                        url = self.BASE_URL + href
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue

                    # Önce title kontrolü yap (boş title'lı linkler duplicate olabilir)
                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else ""

                    # Çok kısa veya boş başlıkları atla (img linkler olabilir)
                    if len(title) < 15:
                        continue

                    # Duplicate kontrolü (title kontrolünden SONRA!)
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

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
        async with SozcuScraper() as scraper:
            # Test arama
            results = await scraper.search("Koç Holding", max_results=3)

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
