"""
Google Search Scraper - Tarih Filtreli Haber Arama

Google Search ile site bazlı + tarih filtreli arama yapar.
Query format: site:hurriyet.com.tr "firma adı" after:2022-01-01 before:2025-01-01
"""
import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus

from app.agents.news.sources.base_scraper import BaseNewsScraper
from app.agents.news.logger import log, step, success, error, warn, debug


class GoogleNewsScraper(BaseNewsScraper):
    """
    Google Search ile tarih filtreli haber arama.

    10 güvenilir haber kaynağı için site bazlı arama yapar.
    Tarih filtreleri: after:YYYY-MM-DD before:YYYY-MM-DD
    """

    BASE_URL = "https://www.google.com"
    SEARCH_URL = "https://www.google.com/search"
    NAME = "Google Search"

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

    PAGE_TIMEOUT = 30000
    NAVIGATION_TIMEOUT = 20000

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

        # 4. Sadece ilk kelime (3+ karakter ise)
        if len(words) >= 1 and len(words[0]) >= 3:
            variants.append(words[0])

        # Dedupe ve normalize
        seen = set()
        unique = []
        for v in variants:
            v_norm = v.strip().upper()
            if v_norm and v_norm not in seen and len(v_norm) >= 3:
                seen.add(v_norm)
                unique.append(v.strip())

        return unique

    async def search(self, company_name: str, max_results: int = 10) -> List[Dict]:
        """
        Basit Google araması (tarih filtresiz).
        Backward compatibility için.
        """
        return await self.search_with_date(
            company_name=company_name,
            site=None,
            date_from=None,
            date_to=None,
            max_results=max_results
        )

    async def search_with_date(
        self,
        company_name: str,
        site: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        suffix: str = "",
        max_results: int = 10,
        use_fallback: bool = True
    ) -> List[Dict]:
        """
        Tarih filtreli Google Search - PROGRESSIVE FALLBACK.

        Args:
            company_name: Firma adı
            site: Site filtresi (örn: hurriyet.com.tr)
            date_from: Başlangıç tarihi (YYYY-MM-DD)
            date_to: Bitiş tarihi (YYYY-MM-DD)
            suffix: Arama suffix'i (örn: "haber", "dava")
            max_results: Maksimum sonuç sayısı
            use_fallback: Progressive fallback kullan (default: True)

        Returns:
            List[Dict]: Bulunan haberler
        """
        # Arama varyasyonları oluştur
        if use_fallback:
            search_variants = self._get_search_variants(company_name)
            # İlk 2 kelimeyi en başa koy (genellikle marka adı)
            if len(search_variants) >= 2:
                search_variants = [search_variants[1]] + search_variants  # İlk 2 kelime önce
        else:
            search_variants = [company_name]

        all_results = []
        tried_queries = set()

        for variant in search_variants:
            if len(all_results) >= max_results:
                break

            # Level 1: Tırnak içi exact match
            results = await self._execute_search(
                variant, site, date_from, date_to, suffix,
                use_quotes=True, tried_queries=tried_queries
            )
            all_results.extend(results)

            if len(all_results) >= max_results:
                break

            # Level 2: Tırnaksız (any order match) - sadece kısa varyasyonlar için
            if len(variant.split()) <= 3:
                results = await self._execute_search(
                    variant, site, date_from, date_to, suffix,
                    use_quotes=False, tried_queries=tried_queries
                )
                all_results.extend(results)

        # Dedupe by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)

        return unique_results[:max_results]

    async def _execute_search(
        self,
        search_term: str,
        site: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        suffix: str,
        use_quotes: bool,
        tried_queries: set
    ) -> List[Dict]:
        """Tek bir arama sorgusunu çalıştır."""
        # Query oluştur
        query_parts = []

        # Site filtresi
        if site:
            query_parts.append(f"site:{site}")

        # Firma adı (tırnaklı veya tırnaksız)
        if use_quotes:
            term = f'"{search_term}"'
        else:
            term = search_term
        if suffix:
            term = f'{term} {suffix}'
        query_parts.append(term)

        # Tarih filtreleri
        if date_from:
            query_parts.append(f"after:{date_from}")
        if date_to:
            query_parts.append(f"before:{date_to}")

        query = " ".join(query_parts)

        # Aynı sorguyu tekrar çalıştırma
        if query in tried_queries:
            return []
        tried_queries.add(query)

        debug(f"[Google] Query: {query}")

        try:
            # Google search URL
            search_url = f"{self.SEARCH_URL}?q={quote_plus(query)}&num=10&hl=tr"

            if not await self._safe_goto(search_url):
                warn(f"[Google] Search page load failed")
                return []

            await asyncio.sleep(1.5)  # Google rate limiting

            # Sonuçları parse et
            results = await self._parse_search_results()

            if results:
                log(f"[Google] {len(results)} sonuç bulundu: {query[:50]}...")
            return results

        except Exception as e:
            error(f"[Google] Search error: {e}")
            return []

    async def _parse_search_results(self) -> List[Dict]:
        """
        Google arama sonuçlarını parse et.
        """
        results = []

        try:
            # Google search result selectors
            # Her sonuç bir div içinde: başlık (h3), URL (a), snippet (span)
            result_elements = await self.page.query_selector_all("div.g")

            if not result_elements:
                # Alternatif selector dene
                result_elements = await self.page.query_selector_all("[data-hveid]")

            for element in result_elements:
                try:
                    # Başlık
                    title_el = await element.query_selector("h3")
                    title = await title_el.inner_text() if title_el else ""

                    # URL
                    link_el = await element.query_selector("a[href]")
                    url = await link_el.get_attribute("href") if link_el else ""

                    # Google redirect URL'lerini temizle
                    if url and url.startswith("/url?"):
                        # /url?q=https://example.com&sa=... formatı
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                        url = parsed.get("q", [url])[0]

                    # Snippet
                    snippet_el = await element.query_selector("div[data-snc], div.VwiC3b, span.aCOpRe")
                    snippet = await snippet_el.inner_text() if snippet_el else ""

                    # Tarih (varsa)
                    date_el = await element.query_selector("span.MUxGbd, span.f")
                    date_text = await date_el.inner_text() if date_el else ""

                    # Geçerli sonuç mu kontrol et
                    if title and url and url.startswith("http"):
                        results.append({
                            "title": title.strip(),
                            "url": url,
                            "snippet": snippet.strip()[:500] if snippet else "",
                            "date": self._parse_date(date_text),
                            "source": self._extract_source(url)
                        })

                except Exception as e:
                    debug(f"[Google] Result parse error: {e}")
                    continue

        except Exception as e:
            error(f"[Google] Parse error: {e}")

        return results

    def _parse_date(self, date_text: str) -> str:
        """
        Tarih metnini parse et.
        Google formatları: "3 gün önce", "15 Kas 2024", etc.
        """
        if not date_text:
            return "unknown"

        # "3 gün önce" formatı
        if "önce" in date_text.lower():
            return date_text.strip()

        # "15 Kas 2024" formatı
        date_pattern = r"(\d{1,2})\s*(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)\s*(\d{4})"
        match = re.search(date_pattern, date_text)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"

        return date_text.strip() if date_text else "unknown"

    def _extract_source(self, url: str) -> str:
        """
        URL'den kaynak adını çıkar.
        """
        try:
            from urllib.parse import urlparse
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
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        suffixes: Optional[List[str]] = None,
        max_per_site: int = 5
    ) -> List[Dict]:
        """
        Tüm haber sitelerinde paralel arama.

        Args:
            company_name: Firma adı
            date_from: Başlangıç tarihi
            date_to: Bitiş tarihi
            suffixes: Arama suffix'leri (None = varsayılan)
            max_per_site: Site başına max sonuç

        Returns:
            List[Dict]: Tüm sitelerden toplanan haberler
        """
        if suffixes is None:
            suffixes = self.SEARCH_SUFFIXES[:5]  # İlk 5 suffix

        all_results = []
        seen_urls = set()

        step(f"[Google] Tüm sitelerde arama: {company_name}")
        log(f"[Google] Sites: {len(self.NEWS_SITES)}, Suffixes: {len(suffixes)}")
        log(f"[Google] Tarih: {date_from} → {date_to}")

        # Her site + suffix kombinasyonu için arama
        for site in self.NEWS_SITES:
            for suffix in suffixes:
                try:
                    results = await self.search_with_date(
                        company_name=company_name,
                        site=site,
                        date_from=date_from,
                        date_to=date_to,
                        suffix=suffix,
                        max_results=max_per_site
                    )

                    # Dedupe
                    for r in results:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)

                    # Rate limiting - Google'ı yormamak için
                    await asyncio.sleep(1)

                except Exception as e:
                    warn(f"[Google] Site search error ({site}, {suffix}): {e}")
                    continue

        success(f"[Google] Toplam {len(all_results)} benzersiz sonuç bulundu")
        return all_results
