"""
DuckDuckGo Search Scraper - Hızlı ve Güvenilir Haber Arama

Google'a alternatif olarak DuckDuckGo kullanır.
Avantajları:
- Rate limiting yok
- CAPTCHA yok
- Daha hızlı yanıt (<1s/sorgu)
- html.duckduckgo.com JS gerektirmez

Dezavantajları:
- Tarih filtresi yok (after:/before: desteklenmiyor)
- Post-filtering ile çözülecek
"""
import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, step, success, error, warn, debug


class DuckDuckGoScraper(BaseNewsScraper):
    """
    DuckDuckGo HTML Search - JS gerektirmez, hızlı.

    Google'ın timeout sorunlarına alternatif.
    Site filtresi: "firma adı site:hurriyet.com.tr"
    """

    BASE_URL = "https://duckduckgo.com"
    SEARCH_URL = "https://html.duckduckgo.com/html"  # HTML versiyonu (JS yok)
    NAME = "DuckDuckGo"

    # Daha hızlı timeout'lar (Google'dan hızlı)
    PAGE_TIMEOUT = 15000      # 15s
    NAVIGATION_TIMEOUT = 10000  # 10s
    ELEMENT_TIMEOUT = 5000    # 5s
    REQUEST_DELAY = 0.5       # 0.5s (rate limiting yok)

    # 10 güvenilir haber kaynağı
    NEWS_SITES = [
        "aa.com.tr",           # Anadolu Ajansı
        "trthaber.com",        # TRT Haber
        "hurriyet.com.tr",     # Hürriyet
        "milliyet.com.tr",     # Milliyet
        "cnnturk.com",         # CNN Türk
        "dunya.com",           # Dünya Gazetesi
        "ekonomim.com",        # Ekonomim
        "bigpara.hurriyet.com.tr",  # Bigpara
        "ntv.com.tr",          # NTV
        "sozcu.com.tr",        # Sözcü
    ]

    # Arama suffix'leri (keyword genişletme)
    SEARCH_SUFFIXES = [
        "",              # Sadece firma adı
        "haber",         # Genel haber
        "dava",          # Hukuki
        "yatırım",       # Finansal
        "iflas",         # Risk
        "soruşturma",    # Hukuki risk
        "ihale",         # İş
        "konkordato",    # Finansal risk
        "satın alma",    # M&A
        "ortaklık",      # İş geliştirme
    ]

    # Legal suffix'ler (firma isimlerinden kaldırılacak)
    LEGAL_SUFFIXES = [
        "LİMİTED ŞİRKETİ", "LIMITED SIRKETI", "LİMİTED", "LIMITED",
        "ANONİM ŞİRKETİ", "ANONIM SIRKETI", "ANONİM", "ANONIM",
        "A.Ş.", "A.S.", "AŞ", "AS",
        "LTD. ŞTİ.", "LTD.STI.", "LTD ŞTİ", "LTD STI",
        "ŞTİ.", "STI.", "ŞTİ", "STI",
        "SAN. VE TİC.", "SAN.VE TIC.", "SANAYİ VE TİCARET",
        "TİC. LTD.", "TIC. LTD.", "TİCARET",
        "SANAYİ", "SANAYI"
    ]

    def _remove_legal_terms(self, name: str) -> str:
        """Firma isminden legal suffix'leri kaldır."""
        result = name.upper()
        for suffix in self.LEGAL_SUFFIXES:
            result = result.replace(suffix.upper(), "").strip()
        # Birden fazla boşluğu tek boşluğa indir
        result = " ".join(result.split())
        return result

    def _get_search_variants(self, company_name: str) -> List[str]:
        """
        Firma adından arama varyasyonları oluştur.
        Daha kısa/genel aramalardan başla, sonuç bulamazsa daha spesifik dene.
        """
        variants = []

        # 1. Legal suffix'siz temiz isim
        clean = self._remove_legal_terms(company_name)
        if clean and clean != company_name.upper():
            variants.append(clean)

        # 2. İlk 2 kelime (genellikle marka adı)
        words = clean.split() if clean else company_name.upper().split()
        if len(words) >= 2:
            variants.append(" ".join(words[:2]))

        # 3. İlk 3 kelime
        if len(words) >= 3:
            variants.append(" ".join(words[:3]))

        # Dedupe ve normalize
        seen = set()
        unique = []
        for v in variants:
            v_norm = v.strip().upper()
            if v_norm and v_norm not in seen and len(v_norm) >= 3:
                seen.add(v_norm)
                unique.append(v.strip())

        return unique

    async def search(self, company_name: str, max_results: int = 20) -> List[Dict]:
        """
        DuckDuckGo ile haber arama.

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Bulunan haberler
        """
        return await self.search_with_site(
            company_name=company_name,
            site=None,
            max_results=max_results
        )

    async def search_with_site(
        self,
        company_name: str,
        site: Optional[str] = None,
        suffix: str = "",
        max_results: int = 20
    ) -> List[Dict]:
        """
        Site filtreli DuckDuckGo araması.

        Args:
            company_name: Firma adı
            site: Site filtresi (örn: hurriyet.com.tr)
            suffix: Arama suffix'i (örn: "haber", "dava")
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Bulunan haberler
        """
        # Arama varyasyonları oluştur
        search_variants = self._get_search_variants(company_name)
        if not search_variants:
            search_variants = [company_name]

        all_results = []
        seen_urls = set()

        for variant in search_variants:
            if len(all_results) >= max_results:
                break

            results = await self._execute_search(variant, site, suffix)

            # Dedupe by URL
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

        return all_results[:max_results]

    async def _execute_search(
        self,
        search_term: str,
        site: Optional[str],
        suffix: str
    ) -> List[Dict]:
        """Tek bir arama sorgusunu çalıştır."""
        # Query oluştur
        query_parts = []

        # Firma adı (tırnaklı exact match)
        term = f'"{search_term}"'
        if suffix:
            term = f'{term} {suffix}'
        query_parts.append(term)

        # Site filtresi
        if site:
            query_parts.append(f"site:{site}")

        query = " ".join(query_parts)

        debug(f"[DuckDuckGo] Query: {query}")

        try:
            # DuckDuckGo HTML search URL
            # POST request yerine GET kullanıyoruz
            search_url = f"{self.SEARCH_URL}/?q={quote_plus(query)}&kl=tr-tr"

            if not await self._safe_goto(search_url):
                warn(f"[DuckDuckGo] Search page load failed")
                return []

            await asyncio.sleep(0.5)  # Kısa delay (rate limiting yok)

            # Sonuçları parse et
            results = await self._parse_search_results()

            if results:
                log(f"[DuckDuckGo] {len(results)} sonuç bulundu: {query[:50]}...")
            return results

        except Exception as e:
            error(f"[DuckDuckGo] Search error: {e}")
            return []

    async def _parse_search_results(self) -> List[Dict]:
        """
        DuckDuckGo HTML arama sonuçlarını parse et.

        html.duckduckgo.com selectors:
        - .result: Her sonuç container
        - .result__title: Başlık (a tag içinde)
        - .result__url: URL
        - .result__snippet: Snippet
        """
        results = []

        try:
            # DuckDuckGo HTML result selectors
            result_elements = await self.page.query_selector_all(".result")

            if not result_elements:
                # Alternatif selector dene
                result_elements = await self.page.query_selector_all(".web-result")

            for element in result_elements[:15]:  # Max 15 sonuç
                try:
                    # Başlık ve URL
                    title_el = await element.query_selector(".result__title a, .result__a")
                    if not title_el:
                        continue

                    title = await title_el.inner_text()
                    url = await title_el.get_attribute("href")

                    # DuckDuckGo redirect URL'lerini temizle
                    if url and "duckduckgo.com" in url:
                        # //duckduckgo.com/l/?uddg=REAL_URL formatı
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                        url = parsed.get("uddg", [url])[0]

                    # Snippet
                    snippet_el = await element.query_selector(".result__snippet")
                    snippet = await snippet_el.inner_text() if snippet_el else ""

                    # Geçerli sonuç mu kontrol et
                    if title and url and url.startswith("http"):
                        results.append({
                            "title": title.strip(),
                            "url": url,
                            "snippet": snippet.strip()[:500] if snippet else "",
                            "date": "unknown",  # DuckDuckGo tarih göstermiyor
                            "source": self._extract_source(url)
                        })

                except Exception as e:
                    debug(f"[DuckDuckGo] Result parse error: {e}")
                    continue

        except Exception as e:
            error(f"[DuckDuckGo] Parse error: {e}")

        return results

    def _extract_source(self, url: str) -> str:
        """URL'den kaynak adını çıkar."""
        try:
            domain = urlparse(url).netloc

            # www. prefix'ini kaldır
            if domain.startswith("www."):
                domain = domain[4:]

            # Bilinen kaynaklar
            source_map = {
                "aa.com.tr": "Anadolu Ajansı",
                "trthaber.com": "TRT Haber",
                "hurriyet.com.tr": "Hürriyet",
                "milliyet.com.tr": "Milliyet",
                "cnnturk.com": "CNN Türk",
                "dunya.com": "Dünya Gazetesi",
                "ekonomim.com": "Ekonomim",
                "bigpara.hurriyet.com.tr": "Bigpara",
                "ntv.com.tr": "NTV",
                "sozcu.com.tr": "Sözcü",
            }

            return source_map.get(domain, domain)

        except Exception:
            return "Unknown"

    async def search_all_sites(
        self,
        company_name: str,
        suffixes: Optional[List[str]] = None,
        max_per_site: int = 5
    ) -> List[Dict]:
        """
        Tüm haber sitelerinde arama.

        Args:
            company_name: Firma adı
            suffixes: Arama suffix'leri (None = varsayılan)
            max_per_site: Site başına max sonuç

        Returns:
            List[Dict]: Tüm sitelerden toplanan haberler
        """
        if suffixes is None:
            suffixes = self.SEARCH_SUFFIXES[:3]  # İlk 3 suffix (hızlı)

        all_results = []
        seen_urls = set()

        step(f"[DuckDuckGo] Tüm sitelerde arama: {company_name}")
        log(f"[DuckDuckGo] Sites: {len(self.NEWS_SITES)}, Suffixes: {len(suffixes)}")

        # Her site + suffix kombinasyonu için arama
        for site in self.NEWS_SITES:
            for suffix in suffixes:
                try:
                    results = await self.search_with_site(
                        company_name=company_name,
                        site=site,
                        suffix=suffix,
                        max_results=max_per_site
                    )

                    # Dedupe
                    for r in results:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)

                    # Kısa delay (rate limiting yok ama yine de nazik ol)
                    await asyncio.sleep(0.3)

                except Exception as e:
                    warn(f"[DuckDuckGo] Site search error ({site}, {suffix}): {e}")
                    continue

        success(f"[DuckDuckGo] Toplam {len(all_results)} benzersiz sonuç bulundu")
        return all_results

    async def quick_search(
        self,
        company_name: str,
        max_results: int = 30
    ) -> List[Dict]:
        """
        Hızlı arama - site filtresi olmadan.

        4 dakikalık demo mode için optimize edilmiş.
        Site filtresi kullanmadan daha hızlı sonuç alır.

        Args:
            company_name: Firma adı
            max_results: Maksimum sonuç sayısı

        Returns:
            List[Dict]: Bulunan haberler
        """
        all_results = []
        seen_urls = set()

        # Arama varyasyonları
        variants = self._get_search_variants(company_name)
        if not variants:
            variants = [company_name]

        # Her variant için "haber" suffix'i ile ara
        for variant in variants[:2]:  # Max 2 variant
            for suffix in ["haber", ""]:  # Sadece 2 suffix
                try:
                    results = await self._execute_search(variant, None, suffix)

                    for r in results:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)

                    if len(all_results) >= max_results:
                        break

                    await asyncio.sleep(0.3)

                except Exception as e:
                    warn(f"[DuckDuckGo] Quick search error: {e}")
                    continue

            if len(all_results) >= max_results:
                break

        log(f"[DuckDuckGo] Quick search: {len(all_results)} sonuç")
        return all_results[:max_results]
