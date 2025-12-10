"""
Anadolu Ajansi (AA) News Scraper
Turkiye'nin resmi haber ajansi - en guvenilir kaynak

Sadece search() implement edilir.
get_article_detail() BaseNewsScraper'dan gelir (LLM-powered, generic!)

URL: https://www.aa.com.tr
"""
import re
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, success, error, warn, debug


class AANewsScraper(BaseNewsScraper):
    """
    Anadolu Ajansi scraper.
    
    Ozellikler:
    - Tier 1 kaynak (en guvenilir)
    - Semantic search (CSS fallback chain)
    - Generic LLM extraction (BaseNewsScraper'dan)
    """
    
    BASE_URL = "https://www.aa.com.tr"
    SEARCH_URL = "https://www.aa.com.tr/tr/search"  # FIX: /arama -> /search
    NAME = "Anadolu Ajansı"
    
    # Semantic search patterns (fallback chain)
    # NOT: Hard-coded CSS yok, semantic pattern'ler kullaniliyor!
    SEARCH_INPUT_PATTERNS = [
        "input[type='search']",
        "input[placeholder*='Ara']",
        "input[placeholder*='ara']",
        "input[name='query']",
        "input[name='q']",
        "input[name='search']"
    ]
    
    SEARCH_BUTTON_PATTERNS = [
        "button[type='submit']",
        "button:has-text('Ara')",
        "button:has-text('ARA')",
        "input[type='submit']",
        "form button"
    ]
    
    async def search(self, company_name: str, max_results: int = 5) -> List[Dict]:
        """
        AA'da firma adı ile arama yap.
        
        Strategy: Direct URL ile arama (GET parameter)
        Fallback: Input + Enter
        
        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı
        
        Returns:
            List[Dict]: Haber listesi
        """
        try:
            log(f"AA arama başlıyor: '{company_name}'")
            
            # STRATEGY 1: Direct URL ile arama (daha güvenilir!)
            # FIX: AA uses ?s= parameter, not ?query=
            encoded_query = urllib.parse.quote(company_name)
            search_url_with_query = f"{self.SEARCH_URL}/?s={encoded_query}"
            
            log(f"Direct URL ile arama: {search_url_with_query}")
            if not await self._safe_goto(search_url_with_query):
                error("AA arama URL'i açılamadı")
                return []
            
            await self._delay(5.0)  # HACKATHON: JS rendering için daha uzun bekle
            debug("Arama sayfası yüklendi, sonuçlar parse ediliyor...")
            
            # Sonuçları parse et
            results = await self._parse_search_results(max_results)
            
            if not results:
                warn(f"AA'da '{company_name}' için sonuç bulunamadı")
                return []
            
            success(f"AA: {len(results)} sonuç bulundu")
            return results
            
        except Exception as e:
            error(f"AA search hatası: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _find_search_input(self) -> Optional[str]:
        """
        Arama inputunu bul (semantic fallback chain).
        
        Returns:
            CSS selector veya None
        """
        for pattern in self.SEARCH_INPUT_PATTERNS:
            try:
                element = await self.page.query_selector(pattern)
                if element:
                    debug(f"Arama inputu bulundu: {pattern}")
                    return pattern
            except Exception:
                continue
        
        warn("Arama inputu hiçbir pattern ile bulunamadı!")
        return None
    
    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """
        Arama sonuçlarını parse et.

        Semantic parsing - gerçek haber linklerini filtrele!
        """
        results = []

        try:
            # HACKATHON: AA JavaScript ile dinamik yüklüyor - uzun bekle!
            try:
                await self.page.wait_for_selector("#haber", timeout=15000)  # 5s → 15s
                debug("#haber div'i bulundu")
            except Exception:
                warn("#haber div'i 15s içinde bulunamadı")

            # HACKATHON: Linkler için uzun bekle (JS rendering)
            try:
                await self.page.wait_for_selector("#haber a[href^='/tr/']", timeout=20000)  # 8s → 20s
                debug("#haber içinde linkler yüklendi")
            except Exception:
                warn("#haber linkler yüklenemedi, fallback kullanılıyor...")

            # AA'da gerçek haber linkleri: /tr/KATEGORI/haber-baslik-ID
            # Örnek: /tr/ekonomi/turk-telekom-aciklama-12345
            # EXCLUDE: /tr/sirkethaberleri, /tr/haberakademisi, /tr/kurumsal-haberler

            # ARAŞTIRMA SONUCU: AA sonuçları #haber div içinde
            link_patterns = [
                "#haber a[href^='/tr/']",           # HABER TAB içindeki linkler (EN GÜVENİLİR!)
                "#haber h4 a[href^='/tr/']",        # Başlık linkleri
                "article a[href^='/tr/']",          # article içindeki linkler
                "div.card a[href^='/tr/']",         # card içindeki linkler
            ]

            all_links = []
            for pattern in link_patterns:
                try:
                    links = await self.page.query_selector_all(pattern)
                    if links:
                        debug(f"'{pattern}' ile {len(links)} link bulundu")
                        all_links.extend(links)
                        if len(all_links) >= max_results * 3:  # Yeterli link toplandı
                            break
                except Exception as e:
                    debug(f"Pattern '{pattern}' hatası: {e}")
                    continue
            
            if not all_links:
                warn("Sonuç sayfasında link bulunamadı")
                return []
            
            # Linkleri filtrele ve işle
            # KRITIK: Footer/header linklerini exclude et
            excluded_paths = [
                '/sirkethaberleri', '/haberakademisi', '/kurumsal-haberler', '/kategori',
                '/p/',  # Policy sayfaları (gizlilik, kvkk, çerez)
                '/gizlilik', '/cerez', '/aydinlatma', '/kvkk', '/iletisim',
                '/hakkimizda', '/kunye', '/reklam', '/sozlesme',
                '/login', '/register', '/abone', '/uyelik'
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
                    
                    # Gerçek haber URL'i olmalı (slug pattern: /tr/kategori/haber-baslik-ID)
                    if href.count('/') < 3 or '-' not in href:
                        continue

                    # AA haberleri numeric ID ile biter
                    # URL format: /tr/kategori/haber-basligi/1234567
                    # last_part sadece numeric ID olmalı
                    last_part = href.rstrip('/').split('/')[-1]
                    # Sadece rakamlardan oluşan ve en az 5 haneli olmalı
                    if not (last_part.isdigit() and len(last_part) >= 5):
                        debug(f"ID pattern eşleşmedi: {href}")
                        continue
                    
                    url = self.BASE_URL + href if href.startswith("/") else href

                    # Önce title kontrolü yap (boş title'lı linkler duplicate olabilir)
                    title_text = await link.inner_text()
                    title = title_text.strip() if title_text else ""

                    # Çok kısa veya boş başlıkları atla (img linkler olabilir)
                    if len(title) < 10:
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
        async with AANewsScraper() as scraper:
            # Test arama
            results = await scraper.search("Türk Telekom", max_results=3)
            
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
