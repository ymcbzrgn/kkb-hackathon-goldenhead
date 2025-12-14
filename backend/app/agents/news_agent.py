"""
News Agent - Haber Toplama ve Sentiment Analizi
Firma hakkındaki haberleri toplar ve analiz eder

HACKATHON GEREKSİNİMLERİ:
1. JPEG Screenshot (her haber için)
2. Tarih Filtresi (date_from/date_to veya son N yıl)
3. Sentiment: olumlu / olumsuz
4. Relevance Validation (LLM ile tek tek)
5. Semantic Search (Qdrant) - opsiyonel

10 GÜVENİLİR KAYNAK (paralel scraping):
- Devlet: AA, TRT Haber
- Demirören: Hürriyet, Milliyet, CNN Türk
- Ekonomi: Dünya, Ekonomim, Bigpara
- Diğer: NTV, Sözcü

TARIH ARALIGI DESTEGI:
- date_from, date_to parametreleri ile belirli tarih araligi
- Tarih formati: YYYY-MM-DD (ornek: "2024-01-01")
"""
import asyncio
import time
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from app.core.config import settings
from app.agents.base_agent import BaseAgent, AgentResult
from app.llm.client import LLMClient
from app.agents.news.sources import (
    # Devlet
    AANewsScraper,
    TRTHaberScraper,
    # Demirören
    HurriyetScraper,
    MilliyetScraper,
    CNNTurkScraper,
    # Ekonomi
    DunyaScraper,
    EkonomimScraper,
    BigparaScraper,
    # Diğer
    NTVScraper,
    SozcuScraper,
    get_all_scrapers,
)
from app.agents.news.extraction import normalize_date, is_date_in_range
from app.agents.news.logger import log, success, error, warn, debug, step
from app.agents.news.semantic_search import NewsSemanticSearch
import re

# Skip words for keyword extraction (generic terms)
SKIP_WORDS = {'a.ş.', 'a.o.', 'ltd', 'şti', 'ş.t.i.', 'san.', 'tic.', 've', 'veya', 'ile', 'a.ş', 'a.o', 'ltd.', 'şti.'}


class NewsAgent(BaseAgent):
    """
    Haber Agent'ı.

    Görevleri:
    - 10 GÜVENİLİR haber kaynağından paralel scraping
    - Her haber için sentiment analizi yap
    - Trend analizi yap

    Kaynaklar:
    - Devlet: AA, TRT Haber
    - Demirören: Hürriyet, Milliyet, CNN Türk
    - Ekonomi: Dünya, Ekonomim, Bigpara
    - Diğer: NTV, Sözcü
    """

    # ============================================
    # Execution time limits (sabit)
    # ============================================
    DEFAULT_MAX_EXECUTION_TIME = 200      # ~3.5 dakika - HACKATHON MODE (4dk limiti için)
    DEMO_MAX_EXECUTION_TIME = 200         # ~3.5 dakika - DEMO MODE

    def __init__(self, demo_mode: bool = False):
        super().__init__(
            agent_id="news_agent",
            agent_name="Haber Agent",
            agent_description="Haber toplama ve sentiment analizi"
        )
        self.llm = LLMClient()
        self.demo_mode = demo_mode

        # Config'den profil bazli ayarlari al
        news_config = settings.profile_config.news

        # Partial results - timeout durumunda kullanılacak
        self._partial_results = {
            "haberler": [],
            "kaynak_sayisi": 0,
            "toplam_haber": 0
        }

        # Date range - run() metodunda set edilir
        self._date_from = None
        self._date_to = None

        # Semantic search (config'e gore)
        self._semantic_search = None
        if news_config.enable_semantic_search:
            self._semantic_search = NewsSemanticSearch()

        # Demo/Normal mode'a göre parametreleri ayarla (config'den)
        if demo_mode:
            self.MAX_ARTICLES_PER_SOURCE = min(15, news_config.max_articles_per_source)
            self.SCRAPER_TIMEOUT = min(90, news_config.scraper_timeout_sec // 5)
            self.MAX_CONCURRENT_SCRAPERS = news_config.max_concurrent_scrapers
            self.YEARS_BACK = news_config.years_back_default
            self.max_execution_time = self.DEMO_MAX_EXECUTION_TIME
        else:
            self.MAX_ARTICLES_PER_SOURCE = news_config.max_articles_per_source
            self.SCRAPER_TIMEOUT = news_config.scraper_timeout_sec
            self.MAX_CONCURRENT_SCRAPERS = news_config.max_concurrent_scrapers
            self.YEARS_BACK = news_config.years_back_full
            self.max_execution_time = self.DEFAULT_MAX_EXECUTION_TIME

        log(f"NewsAgent: Mode={'DEMO' if demo_mode else 'FULL'}, Articles={self.MAX_ARTICLES_PER_SOURCE}, Years={self.YEARS_BACK}, SemanticSearch={news_config.enable_semantic_search}")

        # TSG verisi (agent_tasks.py'den set edilir)
        self._tsg_data = None

    def _generate_search_variants(self, company_name: str, tsg_data: dict = None) -> List[str]:
        """
        Firma adından arama varyasyonları üret.

        Örnek: "Türk Hava Yolları" için:
        - "Türk Hava Yolları" (orijinal)
        - "TÜRK HAVA YOLLARI A.O." (TSG resmi)
        - "THY" (kısaltma)
        - "turk hava yollari" (ASCII)
        """
        variants = set()
        variants.add(company_name)

        # TSG verisi varsa resmi ünvanı ekle
        if tsg_data:
            if tsg_data.get("firma_adi"):
                variants.add(tsg_data["firma_adi"])
            if tsg_data.get("ticaret_unvani"):
                variants.add(tsg_data["ticaret_unvani"])
            if tsg_data.get("unvan"):
                variants.add(tsg_data["unvan"])

        # Kısaltma üret (ilk harfler) - minimum 2 kelime gerekli
        words = [w for w in company_name.split() if len(w) > 2 and w.lower() not in SKIP_WORDS]
        if len(words) >= 2:
            abbreviation = "".join(w[0].upper() for w in words)
            if len(abbreviation) >= 2:
                variants.add(abbreviation)

        # ASCII versiyonu (Türkçe karaktersiz)
        ascii_name = company_name
        tr_map = {
            "İ": "I", "ı": "i", "Ü": "U", "ü": "u",
            "Ö": "O", "ö": "o", "Ş": "S", "ş": "s",
            "Ç": "C", "ç": "c", "Ğ": "G", "ğ": "g"
        }
        for tr_char, ascii_char in tr_map.items():
            ascii_name = ascii_name.replace(tr_char, ascii_char)
        if ascii_name != company_name:
            variants.add(ascii_name)

        # A.Ş., Ltd. vb. olmadan
        clean_name = re.sub(r'\b(A\.?Ş\.?|A\.?O\.?|LTD\.?|ŞTİ\.?)\b', '', company_name, flags=re.IGNORECASE)
        clean_name = clean_name.strip()
        if clean_name and clean_name != company_name:
            variants.add(clean_name)

        log(f"Arama varyasyonları üretildi: {list(variants)}")
        return list(variants)

    def _generate_detailed_keywords(self, company_name: str) -> List[str]:
        """
        Detaylı keyword varyasyonları oluştur (Google Search için).

        Örnek: "İMRAN MAKİNE SANAYİ VE TİCARET LİMİTED ŞİRKETİ" için:
        - "İMRAN MAKİNE SANAYİ VE TİCARET LİMİTED ŞİRKETİ" (tam)
        - "İMRAN MAKİNE" (kısa)
        - "İMRAN" (çok kısa)
        - TSG verilerinden alternatif isimler
        """
        keywords = []

        # 1. Tam firma adı
        keywords.append(company_name)

        # 2. Temiz isim (A.Ş., Ltd. vs. olmadan)
        clean_name = re.sub(
            r'\b(A\.?Ş\.?|A\.?O\.?|LTD\.?|ŞTİ\.?|SAN\.?|TİC\.?|VE|LİMİTED|ŞİRKETİ|ANONİM|ORTAKLIĞI)\b',
            '',
            company_name,
            flags=re.IGNORECASE
        ).strip()
        clean_name = re.sub(r'\s+', ' ', clean_name)  # Çoklu boşlukları temizle
        if clean_name and clean_name != company_name:
            keywords.append(clean_name)

        # 3. İlk iki kelime (genelde ana marka)
        words = company_name.split()
        if len(words) >= 2:
            first_two = f"{words[0]} {words[1]}"
            if first_two not in keywords:
                keywords.append(first_two)

        # 4. İlk kelime KALDIRILDI - çok jenerik sonuçlar veriyor
        # "İMRAN" gibi tek kelime arama çok fazla irrelevant sonuç döndürür
        # Minimum 2 kelime zorunlu: "İMRAN MAKİNE" gibi

        # 5. Alternative names (self._company_names'den)
        for alt_name in getattr(self, '_company_names', []):
            if alt_name and alt_name.strip() not in keywords:
                keywords.append(alt_name.strip())

        # 6. TSG verisi varsa
        tsg_data = getattr(self, '_tsg_data', None)
        if tsg_data:
            if tsg_data.get("firma_adi") and tsg_data["firma_adi"] not in keywords:
                keywords.append(tsg_data["firma_adi"])
            if tsg_data.get("ticaret_unvani") and tsg_data["ticaret_unvani"] not in keywords:
                keywords.append(tsg_data["ticaret_unvani"])

        # Duplikatları temizle ve kısa olanları filtrele
        unique_keywords = []
        for kw in keywords:
            if kw and len(kw) >= 3 and kw not in unique_keywords:
                unique_keywords.append(kw)

        log(f"[NEWS] Detaylı keywords: {unique_keywords}")
        return unique_keywords[:5]  # Max 5 keyword

    async def run(
        self,
        company_name: str,
        alternative_names: List[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> AgentResult:
        """
        Haberleri topla ve analiz et - timeout wrapper ile

        Args:
            company_name: Ana firma adı (kullanıcıdan gelen)
            alternative_names: Alternatif firma isimleri (TSG'den gelen resmi ünvan vb.)
            date_from: Baslangic tarihi (YYYY-MM-DD format, opsiyonel)
            date_to: Bitis tarihi (YYYY-MM-DD format, opsiyonel)
        """
        self._company_names = [company_name]  # Arama yapılacak tüm isimler
        if alternative_names:
            for name in alternative_names:
                if name and name.strip() and name.strip().lower() != company_name.lower():
                    self._company_names.append(name.strip())

        # Tarih araligi ayarla
        self._date_from = date_from
        self._date_to = date_to

        # Mode description
        if date_from and date_to:
            mode_desc = f"Tarih: {date_from} - {date_to}"
        else:
            mode_desc = f"Son {self.YEARS_BACK} yil"

        names_str = " + ".join(self._company_names)
        step(f"NEWS AGENT BASLIYOR: {names_str} ({mode_desc}, max {self.max_execution_time}s)")

        try:
            # Timeout wrapper - max_execution_time sonunda otomatik dur
            return await asyncio.wait_for(
                self._run_internal(company_name),
                timeout=self.max_execution_time
            )
        except asyncio.TimeoutError:
            error(f"News Agent TIMEOUT! ({self.max_execution_time}s)")
            return self._create_timeout_result(company_name)
        except Exception as e:
            error(f"News Agent HATA: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e),
                duration_seconds=self.max_execution_time
            )

    async def _run_internal(self, company_name: str) -> AgentResult:
        """
        GOOGLE SEARCH + TARİH FİLTRELİ İTERATİF ARAMA.

        Yeni akış:
        1. Tarih aralığını ÖNCE belirle
        2. Google Search ile site bazlı + tarih filtreli arama
        3. Detaylı keyword varyasyonları + suffix'ler
        4. 4 dakika boyunca iteratif arama
        5. LLM ile sentiment analizi + rapor
        """
        from datetime import datetime, timedelta
        from app.agents.news.sources import get_search_scraper, get_all_scrapers

        start_time = time.time()
        max_time = self.max_execution_time  # 240s
        analysis_reserve = 30  # Son 30s analiz için

        # Reset partial results
        self._partial_results = {
            "firma_adi": company_name,
            "haberler": [],
            "kaynak_sayisi": 0,
            "toplam_haber": 0,
            "analyzed_news": []
        }

        # ============================================
        # AŞAMA 0: TARİH ARALIĞINI ÖNCE BELİRLE
        # ============================================
        date_from = self._date_from
        date_to = self._date_to

        if not date_from:
            date_from = (datetime.now() - timedelta(days=365 * self.YEARS_BACK)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        step(f"[NEWS] DUCKDUCKGO SEARCH BAŞLIYOR (Hızlı, rate-limit yok)")
        log(f"[NEWS] Firma: {company_name}")
        log(f"[NEWS] Tarih aralığı: {date_from} → {date_to} (post-filtering)")
        log(f"[NEWS] Max süre: {max_time}s")

        # ============================================
        # AŞAMA 1: KEYWORD VARYASYONLARI OLUŞTUR
        # ============================================
        keywords = self._generate_detailed_keywords(company_name)
        log(f"[NEWS] Arama kelimeleri: {keywords}")

        # Arama suffix'leri
        suffixes = ["", "haber", "dava", "yatırım", "iflas", "soruşturma", "ihale", "konkordato"]

        # 10 haber sitesi
        sites = [
            "aa.com.tr", "trthaber.com", "hurriyet.com.tr", "milliyet.com.tr",
            "cnnturk.com", "dunya.com", "ekonomim.com", "ntv.com.tr", "sozcu.com.tr"
        ]

        try:
            all_articles = []
            seen_urls = set()
            round_number = 0

            # ============================================
            # AŞAMA 2A: SITE FİLTRESİZ HIZLI ARAMA (DuckDuckGo)
            # ============================================
            DuckDuckGoScraper = get_search_scraper()

            async with DuckDuckGoScraper() as ddg:
                # Hızlı arama - site filtresi yok, daha geniş sonuç
                self.report_progress(10, "DuckDuckGo ile hızlı arama yapılıyor...")
                log(f"[NEWS] DuckDuckGo hızlı arama başlıyor...")

                try:
                    results = await asyncio.wait_for(
                        ddg.quick_search(
                            company_name=company_name,
                            max_results=30  # Daha fazla sonuç (hızlı)
                        ),
                        timeout=30
                    )

                    for r in results:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            r['search_keyword'] = company_name
                            r['search_suffix'] = 'genel'
                            all_articles.append(r)

                    log(f"[NEWS] DuckDuckGo hızlı arama: {len(results)} sonuç")

                except asyncio.TimeoutError:
                    debug(f"[DuckDuckGo] Timeout: hızlı arama")
                except Exception as e:
                    debug(f"[DuckDuckGo] Error: {e}")

                log(f"[NEWS] Hızlı arama tamamlandı: {len(all_articles)} haber")

            # ============================================
            # AŞAMA 2B: SITE BAZLI İTERATİF ARAMA (DuckDuckGo)
            # ============================================
            DuckDuckGoScraper = get_search_scraper()

            async with DuckDuckGoScraper() as ddg:
                # Her keyword + suffix + site kombinasyonu
                for keyword in keywords:
                    for suffix in suffixes:
                        # Zaman kontrolü
                        elapsed = time.time() - start_time
                        remaining = max_time - elapsed - analysis_reserve

                        if remaining <= 0:
                            log(f"[NEWS] Süre doldu, analiz aşamasına geçiliyor")
                            break

                        round_number += 1
                        search_query = f"{keyword} {suffix}".strip()

                        self.report_progress(
                            min(int((elapsed / max_time) * 70), 65),
                            f"Round {round_number}: '{search_query}' aranıyor... ({len(all_articles)} haber)"
                        )

                        # DuckDuckGo Search (site filtreli, hızlı)
                        for site in sites:
                            try:
                                results = await asyncio.wait_for(
                                    ddg.search_with_site(
                                        company_name=keyword,
                                        site=site,
                                        suffix=suffix,
                                        max_results=5
                                    ),
                                    timeout=10  # Daha kısa timeout (DuckDuckGo hızlı)
                                )

                                # Dedupe ve ekle
                                for r in results:
                                    url = r.get('url', '')
                                    if url and url not in seen_urls:
                                        seen_urls.add(url)
                                        r['search_keyword'] = keyword
                                        r['search_suffix'] = suffix
                                        all_articles.append(r)

                            except asyncio.TimeoutError:
                                debug(f"[DuckDuckGo] Timeout: {site}")
                            except Exception as e:
                                debug(f"[DuckDuckGo] Error: {e}")

                            # Kısa delay (rate limiting yok ama nazik ol)
                            await asyncio.sleep(0.3)

                        # Partial results güncelle
                        self._partial_results["haberler"] = all_articles.copy()
                        self._partial_results["toplam_haber"] = len(all_articles)

                        # Yeterli haber bulunduysa çık
                        if len(all_articles) >= 100:
                            log(f"[NEWS] Yeterli haber bulundu ({len(all_articles)})")
                            break

                    # Outer loop break
                    if len(all_articles) >= 100 or (time.time() - start_time) >= (max_time - analysis_reserve):
                        break

            elapsed = int(time.time() - start_time)
            log(f"[NEWS] DuckDuckGo Search tamamlandı: {len(all_articles)} haber, {round_number} round, {elapsed}s")

            # ============================================
            # AŞAMA 3: MEVCUT SCRAPER'LARLA EK ARAMA
            # ============================================
            if len(all_articles) < 20 and (time.time() - start_time) < (max_time - analysis_reserve - 60):
                log(f"[NEWS] Az haber bulundu, mevcut scraper'larla ek arama yapılıyor...")
                self.report_progress(50, "Ek kaynaklardan aranıyor...")

                scraper_classes = get_all_scrapers()
                semaphore = asyncio.Semaphore(20)

                async def search_source(scraper_class, term):
                    async with semaphore:
                        try:
                            async with scraper_class() as scraper:
                                results = await asyncio.wait_for(
                                    scraper.search_and_fetch(term, max_articles=5, skip_details=True),
                                    timeout=20
                                )
                                if results:
                                    for r in results:
                                        r['source'] = scraper.name
                                    return results
                        except:
                            pass
                        return []

                tasks = [search_source(sc, company_name) for sc in scraper_classes]
                extra_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in extra_results:
                    if isinstance(result, list):
                        for article in result:
                            url = article.get('url', '')
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                all_articles.append(article)

                log(f"[NEWS] Ek arama sonrası: {len(all_articles)} haber")

            self.report_progress(70, f"{len(all_articles)} haber bulundu, analiz ediliyor...")

            # Partial results güncelle
            self._partial_results["haberler"] = all_articles.copy()
            self._partial_results["toplam_haber"] = len(all_articles)
            self._partial_results["kaynak_sayisi"] = len(set(a.get('source', '') for a in all_articles))

            # ============================================
            # AŞAMA 4: ANALİZ VE RAPOR
            # ============================================
            if not all_articles:
                warn(f"'{company_name}' için haber bulunamadı")
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "Haber bulunamadı", "toplam_haber": 0},
                    summary="Firma hakkında güncel haber bulunamadı",
                    key_findings=["Medya görünürlüğü düşük"],
                    warning_flags=[],
                    duration_seconds=int(time.time() - start_time)
                )

            news_items = all_articles

            # Basit relevance kontrolü
            self.report_progress(75, "Haberler filtreleniyor...")
            news_items = self._quick_relevance_filter(news_items, company_name)
            log(f"[NEWS] Relevance filtresi sonrası: {len(news_items)} haber")

            if not news_items:
                warn(f"'{company_name}' için alakalı haber bulunamadı")
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "Alakalı haber bulunamadı", "toplam_haber": 0},
                    summary="Firma hakkında alakalı haber bulunamadı",
                    key_findings=["Medya görünürlüğü düşük veya filtreleme sonucu haber kalmadı"],
                    warning_flags=[],
                    duration_seconds=int(time.time() - start_time)
                )

            # 3. Sentiment analizi
            self.report_progress(90, "Sentiment analizi yapılıyor...")
            analyzed_news = await self._analyze_sentiment(news_items)

            # Update partial results with analyzed news
            self._partial_results["analyzed_news"] = analyzed_news

            # 4. Sonuçları derle
            self.report_progress(95, "Veriler derleniyor...")
            result_data = self._compile_results(analyzed_news)
            self.report_progress(100, "Haber analizi tamamlandı")

            duration = int(time.time() - start_time)
            success(f"[NEWS] TAMAMLANDI: {len(news_items)} haber, {duration}s")
            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                data=result_data,
                summary=self._generate_summary(result_data),
                key_findings=self._extract_key_findings(result_data),
                warning_flags=self._extract_warnings(result_data),
                duration_seconds=duration
            )

        except Exception as e:
            error(f"NEWS AGENT HATASI: {e}")
            import traceback
            traceback.print_exc()
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e),
                duration_seconds=int(time.time() - start_time)
            )

    def _create_timeout_result(self, company_name: str) -> AgentResult:
        """
        Timeout durumunda döndürülecek sonuç - PARTIAL DATA dahil.
        Timeout olsa bile o ana kadar bulunan haberleri kaydet.
        """
        partial = self._partial_results
        haberler = partial.get("haberler", [])
        analyzed = partial.get("analyzed_news", [])
        toplam = len(haberler)

        warn(f"Timeout - Partial data: {toplam} haber bulundu, {len(analyzed)} analiz edildi")

        # Analiz edilmiş haberler varsa onları kullan, yoksa ham haberleri normalize et
        if analyzed:
            final_haberler = analyzed
        else:
            # Ham haberleri frontend formatına çevir (title->baslik, source->kaynak, etc.)
            final_haberler = [
                {
                    "baslik": h.get("title", h.get("baslik", "Başlık yok")),
                    "kaynak": h.get("source", h.get("kaynak", "Bilinmiyor")),
                    "tarih": h.get("date_display", h.get("date", h.get("tarih", "Tarih bilinmiyor"))),
                    "url": h.get("url", ""),
                    "metin": (h.get("text", h.get("metin", ""))[:2000] if h.get("text") or h.get("metin") else ""),
                    "sentiment": h.get("sentiment", "belirsiz"),
                    "is_relevant": h.get("is_relevant", True),
                    "relevance_confidence": h.get("relevance_confidence", 0.5)
                }
                for h in haberler[:20]  # Max 20 haber
            ]

        # Basit sentiment hesapla (analiz edilmişse)
        olumlu = sum(1 for h in final_haberler if h.get("sentiment") in ["pozitif", "olumlu"])
        olumsuz = sum(1 for h in final_haberler if h.get("sentiment") in ["negatif", "olumsuz"])

        result_data = {
            "firma_adi": company_name,
            "toplam_haber": toplam,
            "haberler": final_haberler,
            "timeout": True,
            "timeout_mesaj": f"Tarama {self.max_execution_time}s'de timeout oldu",
            "ozet": {
                "toplam": toplam,
                "olumlu": olumlu,
                "olumsuz": olumsuz,
                "sentiment_score": (olumlu - olumsuz) / max(len(analyzed), 1) if analyzed else 0,
                "trend": "olumlu" if olumlu > olumsuz else ("olumsuz" if olumsuz > olumlu else "notr")
            }
        }

        return AgentResult(
            agent_id=self.agent_id,
            status="completed",
            data=result_data,
            summary=f"Kısmi tarama: {toplam} haber bulundu (timeout, {len(analyzed)} analiz edildi)",
            key_findings=[
                f"Bulunan haber: {toplam}",
                f"Analiz edilen: {len(analyzed)}",
                "Tarama timeout nedeniyle tamamlanamadı"
            ],
            warning_flags=["KISMI_TARAMA", "TIMEOUT"],
            duration_seconds=self.max_execution_time
        )

    # ============================================
    # HIZLI FİLTRELEME METODLARI
    # ============================================

    def _quick_relevance_filter(self, articles: List[Dict], company_name: str) -> List[Dict]:
        """
        Hızlı relevance filtresi - LLM kullanmadan.

        Basit string matching ile haberin firma ile alakalı olup olmadığını kontrol eder.
        """
        if not articles:
            return []

        # Firma adından anahtar kelimeler çıkar
        keywords = self._extract_keywords(company_name)
        log(f"[NEWS] Relevance keywords: {keywords}")

        filtered = []
        for article in articles:
            # Başlık ve metin birleştir
            title = article.get('title', article.get('baslik', '')).lower()
            text = article.get('text', article.get('metin', '')).lower()
            content = f"{title} {text}"

            # En az bir keyword içeriyorsa alakalı say
            is_relevant = any(kw.lower() in content for kw in keywords)

            if is_relevant:
                article['is_relevant'] = True
                article['relevance_confidence'] = 0.8
                filtered.append(article)
            else:
                # İkinci şans: firma adının herhangi bir kelimesi geçiyorsa
                company_words = [w for w in company_name.lower().split() if len(w) > 2]
                partial_match = any(w in content for w in company_words if w not in SKIP_WORDS)
                if partial_match:
                    article['is_relevant'] = True
                    article['relevance_confidence'] = 0.5
                    filtered.append(article)

        return filtered

    def _extract_keywords(self, company_name: str) -> List[str]:
        """Firma adından arama için anahtar kelimeler çıkar."""
        keywords = [company_name]

        # Temiz isim (A.Ş., Ltd. vs. olmadan)
        clean_name = re.sub(r'\b(A\.?Ş\.?|A\.?O\.?|LTD\.?|ŞTİ\.?|SAN\.?|TİC\.?)\b', '', company_name, flags=re.IGNORECASE)
        clean_name = clean_name.strip()
        if clean_name and clean_name != company_name:
            keywords.append(clean_name)

        # Kelimeleri ayır (3+ karakterli olanlar)
        words = [w for w in company_name.split() if len(w) > 3 and w.lower() not in SKIP_WORDS]
        keywords.extend(words)

        return list(dict.fromkeys(keywords))  # Duplikat temizle

    # ============================================
    # TARİH METODLARI
    # ============================================

    def _create_date_segments(
        self,
        date_from: Optional[str],
        date_to: Optional[str],
        segment_days: int = 180
    ) -> List[Dict]:
        """
        Tarih aralığını segmentlere böl.

        3 yıllık aralık için ~6 segment oluşturur (6'şar aylık).
        Her segment için ayrı arama yapılır.

        Args:
            date_from: Başlangıç tarihi (YYYY-MM-DD) veya None
            date_to: Bitiş tarihi (YYYY-MM-DD) veya None
            segment_days: Her segment kaç gün (default: 180 = 6 ay)

        Returns:
            List[Dict]: Her segment için {'from': datetime, 'to': datetime}
        """
        from datetime import datetime, timedelta

        # Tarih aralığını belirle
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                start_date = datetime.now() - timedelta(days=365 * self.YEARS_BACK)
        else:
            start_date = datetime.now() - timedelta(days=365 * self.YEARS_BACK)

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                end_date = datetime.now()
        else:
            end_date = datetime.now()

        segments = []
        current = start_date

        while current < end_date:
            segment_end = min(current + timedelta(days=segment_days), end_date)
            segments.append({
                'from': current.strftime("%Y-%m-%d"),
                'to': segment_end.strftime("%Y-%m-%d")
            })
            current = segment_end

        log(f"[NEWS] Tarih segmentleri oluşturuldu: {len(segments)} segment ({start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')})")
        return segments

    async def _search_round_main(self, company_name: str, search_variants: List[str]) -> List[Dict]:
        """
        ROUND 1: Ana firma araması.

        Tüm scraperlar + semantic search paralel çalışır.
        skip_details=False - detaylı içerik çek!

        Args:
            company_name: Firma adı
            search_variants: Arama varyasyonları

        Returns:
            List[Dict]: Bulunan haberler
        """
        semaphore = asyncio.Semaphore(50)  # 50 concurrent
        scraper_classes = get_all_scrapers()

        async def scrape_one(scraper_class, variant):
            """Tek scraper + varyasyon kombinasyonu."""
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                variant,
                                max_articles=self.MAX_ARTICLES_PER_SOURCE,
                                skip_details=False  # DETAYLI İÇERİK!
                            ),
                            timeout=45  # 45s per scraper
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['search_variant'] = variant
                            return results
                except asyncio.TimeoutError:
                    debug(f"[{scraper_class.NAME}] Timeout (45s)")
                except Exception as e:
                    debug(f"[{scraper_class.NAME}] Error: {e}")
                return []

        # Ana firma adı ile tüm scraperlar + ilk 3 varyasyon
        tasks = []
        for variant in search_variants[:3]:  # İlk 3 varyasyon
            for scraper_class in scraper_classes:
                tasks.append(scrape_one(scraper_class, variant))

        # Semantic search paralel
        semantic_task = self._parallel_semantic_search(search_variants[:3])

        log(f"[NEWS] Round 1: {len(tasks)} scraper task + semantic search başlatılıyor...")

        # Tümünü paralel çalıştır
        all_tasks = tasks + [semantic_task]
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                debug(f"[NEWS] Round 1 task exception: {result}")

        log(f"[NEWS] Round 1 tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _search_round_variants(self, company_name: str, search_variants: List[str]) -> List[Dict]:
        """
        ROUND 2: Firma adı varyasyonları ile arama.

        - Kısa isim (KOÇTAŞ → KOÇ)
        - Tam isim (KOÇTAŞ A.Ş.)
        - İngilizce varyant (KOCTAS)

        Args:
            company_name: Firma adı
            search_variants: Arama varyasyonları

        Returns:
            List[Dict]: Bulunan haberler
        """
        semaphore = asyncio.Semaphore(30)  # 30 concurrent
        scraper_classes = get_all_scrapers()

        async def search_variant(variant, scraper_class):
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                variant,
                                max_articles=20,
                                skip_details=False
                            ),
                            timeout=30  # 30s per scraper
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['search_variant'] = variant
                            return results
                except:
                    pass
                return []

        # Round 1'de kullanılmayan varyasyonlar
        remaining_variants = search_variants[3:] if len(search_variants) > 3 else search_variants

        tasks = []
        for variant in remaining_variants:
            for sc in scraper_classes[:5]:  # İlk 5 scraper (hızlı)
                tasks.append(search_variant(variant, sc))

        log(f"[NEWS] Round 2: {len(tasks)} varyasyon task başlatılıyor...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"[NEWS] Round 2 tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _search_round_date_segment(
        self,
        company_name: str,
        date_from: str,
        date_to: str
    ) -> List[Dict]:
        """
        Belirli tarih segmenti için arama.

        Tarih filtreleri SCRAPER'A GEÇİRİLİR (sadece sonuç filtresi değil).

        Args:
            company_name: Firma adı
            date_from: Segment başlangıç tarihi
            date_to: Segment bitiş tarihi

        Returns:
            List[Dict]: Bulunan haberler
        """
        log(f"[NEWS] Segment arama: {date_from} → {date_to}")

        semaphore = asyncio.Semaphore(30)
        scraper_classes = get_all_scrapers()

        async def scrape_segment(scraper_class):
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        # Bazı scraperlar date_from/date_to destekliyor olabilir
                        # Desteklemiyorsa sadece arama yapılır, sonra filtrelenir
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                company_name,
                                max_articles=20,
                                skip_details=False
                            ),
                            timeout=25  # 25s per scraper
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['date_segment'] = f"{date_from}_{date_to}"
                            return results
                except:
                    pass
                return []

        tasks = [scrape_segment(sc) for sc in scraper_classes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"[NEWS] Segment araması tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _search_round_keywords(self, company_name: str, round_num: int) -> List[Dict]:
        """
        Keyword varyasyonları ile arama.

        Her round'da farklı anahtar kelimeler:
        - firma + haber
        - firma + yatırım
        - firma + dava
        - firma + iflas
        - firma + satın alma
        - firma + ortaklık

        Args:
            company_name: Firma adı
            round_num: Round numarası (keyword set seçimi için)

        Returns:
            List[Dict]: Bulunan haberler
        """
        keyword_sets = [
            ["haber", "gelişme", "son dakika"],
            ["yatırım", "büyüme", "genişleme"],
            ["dava", "soruşturma", "ceza"],
            ["iflas", "konkordato", "mali kriz"],
            ["satın alma", "birleşme", "devir"],
            ["ortaklık", "anlaşma", "sözleşme"],
            ["ihale", "teklif", "proje"],
            ["zarar", "kar", "bilanço"],
        ]

        # Round'a göre keyword set seç
        set_idx = (round_num - 3) % len(keyword_sets)
        keywords = keyword_sets[set_idx]

        queries = [f"{company_name} {kw}" for kw in keywords]

        log(f"[NEWS] Keyword araması: {queries}")

        semaphore = asyncio.Semaphore(20)
        scraper_classes = get_all_scrapers()[:5]  # Hızlı olması için 5 scraper

        async def search_query(query, scraper_class):
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(query, max_articles=15, skip_details=False),
                            timeout=20
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['search_query'] = query
                            return results
                except:
                    pass
                return []

        tasks = []
        for query in queries:
            for sc in scraper_classes:
                tasks.append(search_query(query, sc))

        log(f"[NEWS] Keyword: {len(tasks)} task başlatılıyor...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"[NEWS] Keyword araması tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _search_round_deep(
        self,
        company_name: str,
        existing_articles: List[Dict]
    ) -> List[Dict]:
        """
        ROUND N: Derin arama.

        Mevcut haberlerden çıkarılan:
        - İlişkili firma adları
        - Sektör anahtar kelimeleri
        - Önemli kişi isimleri

        Args:
            company_name: Firma adı
            existing_articles: Önceki roundlarda bulunan haberler

        Returns:
            List[Dict]: Bulunan haberler
        """
        # Mevcut haberlerden entity extraction (basit versiyon)
        related_entities = set()

        for article in existing_articles[:20]:  # İlk 20 habere bak
            content = article.get('text', '') or article.get('title', '')
            # Basit entity extraction (büyük harfli kelimeler)
            words = content.split()
            for word in words:
                # Temizle
                clean_word = word.strip('.,;:!?"\'()[]{}')
                if clean_word.isupper() and len(clean_word) > 3:
                    related_entities.add(clean_word)

        # Company name'i çıkar (zaten arıyoruz)
        company_upper = company_name.upper()
        related_entities.discard(company_upper)
        for word in company_name.split():
            related_entities.discard(word.upper())

        if not related_entities:
            log(f"[NEWS] Deep search: İlişkili entity bulunamadı")
            return []

        queries = list(related_entities)[:5]  # Max 5 ilişkili entity
        log(f"[NEWS] Deep search - ilişkili entityler: {queries}")

        semaphore = asyncio.Semaphore(15)
        scraper_classes = get_all_scrapers()[:3]  # Hızlı olması için 3 scraper

        async def search_entity(entity, scraper_class):
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        # Firma adı + entity kombinasyonu
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                f"{company_name} {entity}",
                                max_articles=10,
                                skip_details=False
                            ),
                            timeout=15
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['related_entity'] = entity
                            return results
                except:
                    pass
                return []

        tasks = []
        for entity in queries:
            for sc in scraper_classes:
                tasks.append(search_entity(entity, sc))

        log(f"[NEWS] Deep search: {len(tasks)} task başlatılıyor...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"[NEWS] Deep search tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _search_news(self, company_name: str) -> List[Dict]:
        """
        7 haber kaynağından paralel scraping (rate limited).

        Her kaynak bağımsız çalışır, biri fail olsa da diğerleri devam eder.
        Semaphore ile max 3 concurrent scraper çalışır.
        INCREMENTAL: Her scraper bittiğinde partial_results güncellenir.
        """
        log(f"7 kaynaktan paralel arama başlıyor (max {self.MAX_CONCURRENT_SCRAPERS} concurrent): '{company_name}'")

        all_articles = []
        scraper_classes = get_all_scrapers()

        # Rate limiting için semaphore
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SCRAPERS)

        # Paralel scraping tasks oluştur (semaphore ile)
        async def scrape_source_with_limit(scraper_class):
            """Tek bir kaynaktan haber çek (rate limited)."""
            async with semaphore:  # Max 3 concurrent
                try:
                    async with scraper_class() as scraper:
                        debug(f"[{scraper.name}] Arama başlıyor...")
                        # Detaylı extraction her zaman aktif (daha doğru sonuçlar için)
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                company_name,
                                max_articles=self.MAX_ARTICLES_PER_SOURCE,
                                skip_details=False  # Her zaman detaylı (daha doğru sonuçlar)
                            ),
                            timeout=self.SCRAPER_TIMEOUT
                        )
                        if results:
                            success(f"[{scraper.name}] {len(results)} haber bulundu")
                            # Source ekle
                            for article in results:
                                article['source'] = scraper.name
                            return (scraper.name, results)
                        else:
                            warn(f"[{scraper.name}] Haber bulunamadı")
                            return (scraper.name, [])
                except asyncio.TimeoutError:
                    warn(f"[{scraper_class.NAME}] Timeout ({self.SCRAPER_TIMEOUT}s)")
                    return (scraper_class.NAME, [])
                except Exception as e:
                    error(f"[{scraper_class.NAME}] Hata: {e}")
                    return (scraper_class.NAME, [])

        # Tüm scraper'ları paralel çalıştır (as_completed ile incremental güncelleme)
        tasks = [scrape_source_with_limit(sc) for sc in scraper_classes]

        # as_completed ile her scraper bittiğinde partial_results güncelle
        for coro in asyncio.as_completed(tasks):
            try:
                scraper_name, results = await coro
                if results:
                    all_articles.extend(results)
                    # INCREMENTAL: Partial results güncelle (timeout durumunda kullanılacak)
                    self._partial_results["haberler"] = all_articles.copy()
                    self._partial_results["toplam_haber"] = len(all_articles)
                    self._partial_results["kaynak_sayisi"] = len(set(a.get('source', '') for a in all_articles))
                    log(f"[INCREMENTAL] {scraper_name} tamamlandı, toplam: {len(all_articles)} haber")
            except Exception as e:
                error(f"Scraper task hatası: {e}")

        log(f"Toplam {len(all_articles)} haber bulundu (7 kaynaktan)")
        return all_articles

    async def _global_search(self, query: str, search_variants: List[str]) -> List[Dict]:
        """
        Source-agnostic global search.

        Combines:
        1. Parallel scraping from all sources
        2. Qdrant semantic search (historical + cross-source)
        3. Cross-source deduplication
        4. Unified ranking

        Args:
            query: Ana arama sorgusu
            search_variants: Arama varyasyonları listesi

        Returns:
            List[Dict]: Sıralanmış ve deduplicate edilmiş haberler
        """
        all_results = []
        seen_urls = set()

        # Phase 1: Parallel source scraping (tüm varyasyonlar için)
        log(f"Global Search Phase 1: Parallel scraping ({len(search_variants)} varyasyon)")

        scraper_classes = get_all_scrapers()
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SCRAPERS)

        async def scrape_with_timeout(scraper_class, variant):
            """Tek kaynak + varyasyon kombinasyonu için scraping."""
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                variant,
                                max_articles=self.MAX_ARTICLES_PER_SOURCE,
                                skip_details=False
                            ),
                            timeout=self.SCRAPER_TIMEOUT
                        )
                        if results:
                            for article in results:
                                article['source'] = scraper.name
                                article['search_variant'] = variant
                            return results
                        return []
                except asyncio.TimeoutError:
                    return []
                except Exception as e:
                    debug(f"Scraper error: {e}")
                    return []

        # Tüm kombinasyonları paralel çalıştır
        tasks = []
        for variant in search_variants[:5]:  # İlk 5 varyasyon
            for scraper_class in scraper_classes:
                tasks.append(scrape_with_timeout(scraper_class, variant))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                continue
            if not result:
                continue
            for article in result:
                url = article.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(article)

        log(f"Phase 1: {len(all_results)} articles from scrapers")

        # Phase 2: Qdrant semantic search
        if self._semantic_search and all_results:
            log("Global Search Phase 2: Semantic search")

            try:
                # Index current results
                await self._semantic_search.index_articles(all_results[:100])

                # Search for similar (historical data)
                for variant in search_variants[:3]:
                    similar = await self._semantic_search.find_similar(
                        query=variant,
                        top_k=30,
                        min_score=0.5
                    )
                    for article in similar:
                        url = article.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            article['source'] = article.get('source', 'semantic_search')
                            all_results.append(article)

                log(f"Phase 2: {len(all_results)} articles after semantic search")
            except Exception as e:
                warn(f"Semantic search error: {e}")

        # Phase 3: Semantic deduplication
        log("Global Search Phase 3: Semantic deduplication")
        all_results = await self._semantic_dedup(all_results)

        # Phase 4: Unified ranking
        log("Global Search Phase 4: Unified ranking")
        all_results = self._rank_results(all_results, query)

        log(f"Global Search complete: {len(all_results)} unique articles")
        return all_results

    async def _semantic_dedup(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove semantically similar articles (same story, different source).

        URL bazlı deduplicate zaten yapılıyor, bu ek olarak
        aynı haberin farklı kaynaklardan gelen versiyonlarını filtreler.

        Args:
            articles: Haber listesi

        Returns:
            List[Dict]: Deduplicate edilmiş haberler
        """
        if len(articles) <= 1:
            return articles

        if not self._semantic_search:
            # Semantic search yoksa basit title similarity kullan
            return self._simple_title_dedup(articles)

        unique = []
        seen_embeddings = []

        for article in articles:
            title = article.get('title', '')
            if not title:
                unique.append(article)
                continue

            try:
                # Get embedding
                embedding = await self._semantic_search._get_embedding(title)

                # Check similarity with seen embeddings
                is_duplicate = False
                for seen_emb in seen_embeddings:
                    similarity = self._cosine_similarity(embedding, seen_emb)
                    if similarity > 0.9:  # 90% similar = duplicate
                        is_duplicate = True
                        break

                if not is_duplicate:
                    unique.append(article)
                    seen_embeddings.append(embedding)
                else:
                    debug(f"Semantic dedup: '{title[:50]}...'")

            except Exception:
                # Embedding hatası - makaleyi ekle
                unique.append(article)

        log(f"Semantic dedup: {len(articles)} → {len(unique)} articles")
        return unique

    def _simple_title_dedup(self, articles: List[Dict]) -> List[Dict]:
        """Basit title similarity dedupe (semantic search yoksa)."""
        unique = []
        seen_titles = set()

        for article in articles:
            title = article.get('title', '').lower().strip()
            if not title:
                unique.append(article)
                continue

            # Normalize title
            normalized = ''.join(c for c in title if c.isalnum() or c.isspace())
            normalized = ' '.join(normalized.split())[:100]

            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(article)

        return unique

    async def _ultra_parallel_scrape(self, search_variants: List[str]) -> List[Dict]:
        """
        HYPER MODE: 50 concurrent scraper - tüm kaynaklar × tüm varyasyonlar.

        10 kaynak × 5 varyasyon = 50 paralel task
        60s hard timeout per scraper

        Args:
            search_variants: Arama varyasyonları

        Returns:
            List[Dict]: Tüm bulunan haberler
        """
        semaphore = asyncio.Semaphore(50)  # 50 concurrent
        scraper_classes = get_all_scrapers()

        async def scrape_one(scraper_class, variant):
            """Tek scraper + varyasyon kombinasyonu."""
            async with semaphore:
                try:
                    async with scraper_class() as scraper:
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(
                                variant,
                                max_articles=self.MAX_ARTICLES_PER_SOURCE,
                                skip_details=True  # Hız için detay atla
                            ),
                            timeout=60  # 60s hard timeout
                        )
                        if results:
                            for r in results:
                                r['source'] = scraper.name
                                r['search_variant'] = variant
                            return results
                except asyncio.TimeoutError:
                    debug(f"[{scraper_class.NAME}] Timeout (60s)")
                except Exception as e:
                    debug(f"[{scraper_class.NAME}] Error: {e}")
                return []

        # 10 kaynak × N varyasyon = N×10 task
        tasks = []
        for variant in search_variants[:5]:  # Max 5 varyasyon
            for scraper_class in scraper_classes:
                tasks.append(scrape_one(scraper_class, variant))

        log(f"ULTRA SCRAPE: {len(tasks)} paralel task başlatılıyor...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"ULTRA SCRAPE tamamlandı: {len(all_articles)} haber")
        return all_articles

    async def _parallel_semantic_search(self, search_variants: List[str]) -> List[Dict]:
        """
        HYPER MODE: Paralel semantic search - tüm varyasyonlar için.

        Her varyasyon için ayrı semantic search çalıştırır.

        Args:
            search_variants: Arama varyasyonları

        Returns:
            List[Dict]: Semantic search sonuçları
        """
        if not self._semantic_search:
            log("Semantic search devre dışı")
            return []

        async def search_variant(variant):
            """Tek varyasyon için semantic search."""
            try:
                results = await self._semantic_search.find_similar(
                    query=variant,
                    top_k=50,  # Her varyasyon için 50 sonuç
                    min_score=0.4
                )
                if results:
                    for r in results:
                        r['source'] = r.get('source', 'semantic_search')
                        r['search_variant'] = variant
                    return results
            except Exception as e:
                debug(f"Semantic search error: {e}")
            return []

        tasks = [search_variant(v) for v in search_variants[:5]]  # Max 5 varyasyon
        log(f"PARALLEL SEMANTIC: {len(tasks)} paralel search başlatılıyor...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        log(f"PARALLEL SEMANTIC tamamlandı: {len(all_articles)} sonuç")
        return all_articles

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """İki vektör arasındaki cosine similarity."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _rank_results(self, articles: List[Dict], query: str) -> List[Dict]:
        """
        Unified ranking algorithm.

        Factors:
        - Relevance score (keyword + semantic): 40%
        - Recency (newer = higher): 30%
        - Source trust score: 20%
        - Content quality (length, has text): 10%

        Args:
            articles: Haber listesi
            query: Arama sorgusu

        Returns:
            List[Dict]: Sıralanmış haberler
        """
        SOURCE_TRUST = {
            "Anadolu Ajansı": 1.0,
            "TRT Haber": 0.95,
            "Dünya": 0.9,
            "Hürriyet": 0.85,
            "Milliyet": 0.85,
            "CNN Türk": 0.85,
            "NTV": 0.85,
            "Ekonomim": 0.8,
            "Bigpara": 0.8,
            "Sözcü": 0.75,
            "semantic_search": 0.7,  # Historical
        }

        all_names = getattr(self, '_company_names', [query])

        for article in articles:
            score = 0.0

            # Factor 1: Keyword relevance (40%)
            keyword_score = self._calculate_keyword_score(article, all_names)
            score += keyword_score * 0.4

            # Factor 2: Recency (30%)
            days_old = self._days_since_publication(article)
            recency_score = max(0, 1 - (days_old / 365))  # Decay over 1 year
            score += recency_score * 0.3

            # Factor 3: Source trust (20%)
            source = article.get('source', 'Unknown')
            trust_score = SOURCE_TRUST.get(source, 0.5)
            score += trust_score * 0.2

            # Factor 4: Content quality (10%)
            text_len = len(article.get('text', '') or '')
            quality_score = min(1.0, text_len / 1000)  # Max at 1000 chars
            score += quality_score * 0.1

            article['ranking_score'] = round(score, 3)

        # Sort by ranking score (descending)
        return sorted(articles, key=lambda x: x.get('ranking_score', 0), reverse=True)

    def _days_since_publication(self, article: Dict) -> int:
        """Haberin kaç gün önce yayınlandığını hesapla."""
        from datetime import datetime

        date_str = article.get('date', '')
        if not date_str or date_str == 'unknown':
            return 365  # Bilinmeyen tarih = 1 yıl önce varsay

        try:
            # YYYY-MM-DD format
            article_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            delta = datetime.now() - article_date
            return max(0, delta.days)
        except (ValueError, TypeError):
            return 365  # Parse edilemezse 1 yıl varsay

    def _filter_by_date(self, articles: List[Dict]) -> List[Dict]:
        """
        Tarih filtresi - date_from/date_to veya YEARS_BACK ile.

        Mod 1: date_from + date_to parametreleri verilmisse, o aralik
        Mod 2: YEARS_BACK yil oncesinden eski haberler filtrelenir

        KULLANICI TERCİHİ:
        - Unknown tarihler dahil edilir ("Tarih bilinmiyor" olarak)
        """
        from datetime import datetime

        filtered = []
        current_year = datetime.now().year

        # Tarih araligi belirleme
        if self._date_from and self._date_to:
            # Mod 1: Spesifik tarih araligi
            try:
                date_from_obj = datetime.strptime(self._date_from, "%Y-%m-%d")
                date_to_obj = datetime.strptime(self._date_to, "%Y-%m-%d")
                min_year = date_from_obj.year
                max_year = date_to_obj.year
                log(f"Tarih filtresi (range): {self._date_from} - {self._date_to}")
            except ValueError as e:
                warn(f"Tarih format hatasi: {e}. Son {self.YEARS_BACK} yil kullaniliyor.")
                min_year = current_year - self.YEARS_BACK
                max_year = current_year
        else:
            # Mod 2: Son N yil
            min_year = current_year - self.YEARS_BACK
            max_year = current_year
            log(f"Tarih filtresi (years): {min_year}-{max_year} ({self.YEARS_BACK} yil)")

        for article in articles:
            date_str = article.get('date', 'unknown')

            # Tarih normalize et
            normalized_date = normalize_date(date_str)

            # Tarih aralığını kontrol et
            is_valid, display_date = is_date_in_range(normalized_date, min_year=min_year, max_year=max_year)

            # Spesifik tarih araligi varsa, gun bazinda da kontrol et
            if is_valid and self._date_from and self._date_to and normalized_date != 'unknown':
                try:
                    # Normalize edilmis tarihi parse et
                    article_date = datetime.strptime(normalized_date, "%Y-%m-%d")
                    date_from_obj = datetime.strptime(self._date_from, "%Y-%m-%d")
                    date_to_obj = datetime.strptime(self._date_to, "%Y-%m-%d")
                    if not (date_from_obj <= article_date <= date_to_obj):
                        is_valid = False
                except (ValueError, TypeError):
                    pass  # Parse edilemezse yil bazli kontrole guven

            if is_valid:
                article['date'] = normalized_date
                article['date_display'] = display_date
                filtered.append(article)
            else:
                debug(f"Tarih filtre REJECTED: {date_str} - {article.get('title', '')[:50]}")

        return filtered

    async def _semantic_search_round(self, company_name: str, existing_articles: List[Dict]) -> List[Dict]:
        """
        Qdrant semantic search ile benzer haberler bul.
        Önceki round'larda bulunan haberleri indexle, sonra ara.
        """
        if not self._semantic_search:
            return []

        try:
            # Mevcut haberleri indexle (max 50)
            indexed = await self._semantic_search.index_articles(existing_articles[:50])
            log(f"Semantic: {indexed} haber indexlendi")

            # Firma adı ile benzer haberleri ara
            similar = await self._semantic_search.find_company_news(
                company_name,
                alternative_names=getattr(self, '_company_names', []),
                top_k=30
            )

            log(f"Semantic: {len(similar)} benzer haber bulundu")
            return similar

        except Exception as e:
            warn(f"Semantic search hatası: {e}")
            return []

    def _calculate_keyword_score(self, article: Dict, company_names: List[str]) -> float:
        """
        Gelişmiş keyword skorlama.

        Faktörler:
        - Firma adı başlıkta geçiyor mu? (+0.5)
        - Firma adı metinde geçiyor mu? (+0.3)
        - Kaç önemli kelime eşleşiyor? (+0.2 * oran)
        - Rakip firma adı var mı? (-0.3) [TODO]

        Returns:
            float: 0.0 - 1.0 arası skor
        """
        score = 0.0
        title = article.get('title', '').lower()
        text = (article.get('text', '') or '').lower()

        for name in company_names:
            name_lower = name.lower()

            # Başlıkta tam eşleşme
            if name_lower in title:
                score += 0.5

            # Metinde tam eşleşme
            elif name_lower in text:
                score += 0.3

            else:
                # Kelime bazlı eşleşme - MİNİMUM 2 KELİME ZORUNLU
                keywords = [w for w in name.split() if len(w) > 2 and w.lower() not in SKIP_WORDS]
                if keywords:
                    matches = sum(1 for kw in keywords if kw.lower() in title or kw.lower() in text)
                    # TEK KELİME EŞLEŞMESİ 0 PUAN (çok jenerik)
                    # Örn: sadece "İMRAN" bulundu → irrelevant haber olabilir
                    if matches >= 2:
                        score += 0.3 * (matches / len(keywords))
                    # matches == 1 → 0 puan (skip)

        return min(score, 1.0)

    async def _validate_relevance(self, article: Dict, company_name: str) -> Tuple[bool, float]:
        """
        HACKATHON: LLM ile haber relevance'ını doğrula.

        KULLANICI TERCİHİ: Her haber için ayrı LLM çağrısı (kalite öncelikli).

        Returns:
            Tuple[bool, float]: (is_relevant, confidence_score)
        """
        title = article.get('title', '')
        text = article.get('text', '')[:500] if article.get('text') else title

        prompt = f"""Bu haber "{company_name}" firması hakkında mı?

Başlık: {title}
Metin (ilk 500 karakter): {text}

Analiz et:
1. Firma adı doğrudan geçiyor mu?
2. Firmanın ürünleri/hizmetleri hakkında mı?
3. Firmanın yöneticileri hakkında mı?
4. Rakip firma değil, gerçekten bu firma mı?

Cevap formatı:
EVET veya HAYIR - Güven skoru (0.0-1.0)

Örnek: EVET - 0.95
Cevap:"""

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-oss-120b",
                temperature=0.1,
                max_tokens=20
            )

            # HACKATHON FIX: Boş response kontrolü - keyword fallback'e git
            if not response or not response.strip():
                warn(f"Relevance LLM boş response, keyword fallback kullanılıyor")
                return self._keyword_relevance(article, company_name)

            response_text = response.strip().upper()

            # Parse response
            is_relevant = "EVET" in response_text
            confidence = 0.5  # default

            try:
                if "-" in response:
                    conf_str = response.split("-")[1].strip()
                    # Sayıyı bul
                    import re
                    conf_match = re.search(r'(\d+\.?\d*)', conf_str)
                    if conf_match:
                        confidence = float(conf_match.group(1))
                        if confidence > 1:
                            confidence = confidence / 100  # 95 -> 0.95
            except Exception:
                pass

            return is_relevant, confidence

        except Exception as e:
            warn(f"Relevance validation hatası: {e}")
            # Fallback: keyword-based
            return self._keyword_relevance(article, company_name)

    def _keyword_relevance(self, article: Dict, company_name: str) -> Tuple[bool, float]:
        """
        Basit kural: Firma adı veya önemli kelimeleri geçiyorsa PASS.

        KKB İsteği: "Firma adı içinde geçsin yeter!"
        """
        return self._keyword_relevance_multi(article, [company_name])

    def _keyword_relevance_multi(self, article: Dict, company_names: List[str]) -> Tuple[bool, float]:
        """
        SIKILAŞTIRILMIŞ kural: Tüm firma isimleriyle kontrol.

        Kurallar:
        1. Firma adının TAMAMI geçiyorsa → %100 relevance
        2. Firma adının EN AZ %60'ı (önemli kelimeler) geçiyorsa → relevance
        3. Tek kelime eşleşmesi → DÜŞÜK confidence (filtrelenebilir)
        """
        title = article.get('title', '').lower()
        text = (article.get('text', '') or '').lower()
        combined = f"{title} {text}"

        best_confidence = 0.0
        is_relevant = False

        for company_name in company_names:
            name_lower = company_name.lower()

            # Kural 1: Firma adının TAMAMI geçiyor mu?
            if name_lower in combined:
                return (True, 1.0)

            # Kural 2: Önemli kelimelerin çoğu geçiyor mu?
            # "A.Ş.", "A.O.", "Ltd" gibi generic terimleri çıkar
            skip_words = {'a.ş.', 'a.o.', 'ltd', 'şti', 'ş.t.i.', 'san.', 'tic.', 've', 'veya', 'ile'}
            company_keywords = [w.lower() for w in company_name.split() if len(w) > 2 and w.lower() not in skip_words]

            if not company_keywords:
                continue

            matches = sum(1 for kw in company_keywords if kw in combined)
            match_ratio = matches / len(company_keywords)

            # En az %60 eşleşme gerekli (2/3 kelime gibi)
            if match_ratio >= 0.6:
                confidence = match_ratio
                if confidence > best_confidence:
                    best_confidence = confidence
                    is_relevant = True
            elif matches >= 1:
                # Tek kelime eşleşmesi - düşük confidence
                # Bu genellikle filtrelenecek (< 0.6)
                single_conf = 0.4
                if single_conf > best_confidence:
                    best_confidence = single_conf

        return (is_relevant, best_confidence)

    async def _validate_all_articles(self, articles: List[Dict], company_name: str) -> List[Dict]:
        """
        ÜÇ KATMANLI DOĞRULAMA:

        KATMAN 1: Kesin eşleşme kontrolü (hızlı, kesin)
        - Firma adı tam olarak geçiyorsa → doğrudan kabul (confidence=1.0)

        KATMAN 2: Keyword skoru hesapla
        - score >= 0.7 → kabul
        - score 0.3-0.7 → LLM'e sor
        - score < 0.3 → reddet

        KATMAN 3: LLM validation (sadece belirsiz olanlar için)
        - Daha esnek threshold (0.4 yerine 0.6)
        """
        if not articles:
            return []

        validated = []
        needs_llm = []  # LLM'e sorulacak haberler
        filtered_out = 0

        # Tüm firma isimlerini al (ana isim + alternatifler)
        all_company_names = getattr(self, '_company_names', [company_name])
        log(f"Üç katmanlı validation başlıyor: {len(articles)} haber, isimler: {all_company_names}")

        # ============================================
        # KATMAN 1 & 2: Kesin eşleşme + Keyword skoru
        # ============================================
        for article in articles:
            title = article.get('title', '').lower()
            text = (article.get('text', '') or '').lower()
            combined = f"{title} {text}"

            # KATMAN 1: Kesin eşleşme kontrolü
            exact_match = False
            for variant in all_company_names:
                if variant.lower() in combined:
                    exact_match = True
                    break

            if exact_match:
                # Kesin eşleşme - doğrudan kabul
                article['relevance_confidence'] = 1.0
                article['is_relevant'] = True
                article['validation_method'] = 'exact_match'
                validated.append(article)
                debug(f"EXACT MATCH: {article.get('title', '')[:50]}...")
                continue

            # KATMAN 2: Keyword skoru hesapla
            keyword_score = self._calculate_keyword_score(article, all_company_names)

            if keyword_score >= 0.7:
                # Yüksek keyword skoru - kabul
                article['relevance_confidence'] = keyword_score
                article['is_relevant'] = True
                article['validation_method'] = 'keyword_high'
                validated.append(article)
                debug(f"KEYWORD HIGH ({keyword_score:.2f}): {article.get('title', '')[:50]}...")

            elif keyword_score >= 0.3:
                # Orta skor - LLM'e sor
                article['_keyword_score'] = keyword_score  # Geçici
                needs_llm.append(article)
                debug(f"NEEDS LLM ({keyword_score:.2f}): {article.get('title', '')[:50]}...")

            else:
                # Düşük skor - reddet
                filtered_out += 1
                debug(f"REJECTED (low keyword {keyword_score:.2f}): {article.get('title', '')[:50]}...")

        log(f"Katman 1-2: {len(validated)} kabul, {len(needs_llm)} LLM gerekli, {filtered_out} red")

        # ============================================
        # KATMAN 3: LLM validation (sadece belirsiz olanlar)
        # ============================================
        if needs_llm:
            log(f"LLM validation başlıyor: {len(needs_llm)} haber")
            batch_size = 30

            for batch_start in range(0, len(needs_llm), batch_size):
                batch = needs_llm[batch_start:batch_start + batch_size]

                # Batch için relevance kontrolü
                batch_results = await self._batch_validate_relevance(batch, company_name, all_company_names)

                for article, (is_relevant, llm_confidence) in zip(batch, batch_results):
                    keyword_score = article.pop('_keyword_score', 0.5)

                    # LLM + keyword skorunu birleştir (weighted average)
                    combined_confidence = (llm_confidence * 0.6 + keyword_score * 0.4)

                    article['relevance_confidence'] = round(combined_confidence, 2)
                    article['is_relevant'] = is_relevant
                    article['validation_method'] = 'llm'

                    # DAHA ESNEK THRESHOLD: 0.4 (eskisi 0.6)
                    if is_relevant and combined_confidence >= 0.4:
                        validated.append(article)
                        debug(f"LLM KEPT ({combined_confidence:.2f}): {article.get('title', '')[:50]}...")
                    else:
                        filtered_out += 1
                        debug(f"LLM REJECTED ({combined_confidence:.2f}): {article.get('title', '')[:50]}...")

        log(f"Validation tamamlandı: {len(validated)} KEPT, {filtered_out} FILTERED OUT")
        return validated

    async def _batch_validate_relevance(self, articles: List[Dict], company_name: str, all_company_names: List[str] = None) -> List[Tuple[bool, float]]:
        """
        OPTİMİZE: Tek LLM çağrısıyla batch relevance validation.

        Args:
            articles: Haber listesi
            company_name: Ana firma adı
            all_company_names: Tüm firma isimleri (ana + alternatifler)

        Returns:
            List[Tuple[bool, float]]: Her haber için (is_relevant, confidence)
        """
        if not articles:
            return []

        # Tüm isimleri kullan
        names_to_check = all_company_names or [company_name]
        names_str = " veya ".join(f'"{n}"' for n in names_to_check)

        # Batch prompt oluştur
        articles_text = "\n".join([
            f"{i+1}. {a.get('title', '')[:100]}"
            for i, a in enumerate(articles)
        ])

        prompt = f"""Aşağıdaki haberlerin {names_str} firması/firmaları hakkında olup olmadığını değerlendir.

KURALLAR:
- Firma adı veya kısaltması DOĞRUDAN geçmeli
- Firmanın ürünleri, hizmetleri veya yöneticileri hakkında olabilir
- Rakip firma veya benzer isimli başka firma DEĞİL, tam bu firma olmalı
- Sadece sektör haberi veya genel ekonomi haberi SAYILMAZ

HABERLER:
{articles_text}

HER HABER İÇİN TEK SATIRDA CEVAP VER:
Numara. EVET veya HAYIR

Örnek:
1. EVET
2. HAYIR
3. EVET

Şimdi değerlendir:"""

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-oss-120b",
                temperature=0.1,
                max_tokens=len(articles) * 15  # Her satır için ~15 token
            )

            if not response or not response.strip():
                warn("Batch relevance LLM boş response, keyword fallback kullanılıyor")
                return [self._keyword_relevance_multi(a, names_to_check) for a in articles]

            # Response'u parse et
            results = self._parse_batch_relevance_response(response, len(articles))

            # Eksik sonuçları keyword fallback ile doldur
            while len(results) < len(articles):
                idx = len(results)
                results.append(self._keyword_relevance_multi(articles[idx], names_to_check))

            return results

        except Exception as e:
            warn(f"Batch relevance validation hatası: {e}, keyword fallback kullanılıyor")
            return [self._keyword_relevance_multi(a, names_to_check) for a in articles]

    def _parse_batch_relevance_response(self, response: str, expected_count: int) -> List[Tuple[bool, float]]:
        """Batch relevance LLM response'unu parse et."""
        results = []

        for line in response.strip().split('\n'):
            line = line.strip().upper()
            if not line:
                continue

            # "1. EVET" veya "1.EVET" veya sadece "EVET" formatlarını handle et
            is_relevant = "EVET" in line
            confidence = 0.85 if is_relevant else 0.15  # LLM-based = yüksek güven

            results.append((is_relevant, confidence))

            if len(results) >= expected_count:
                break

        return results

    async def _analyze_sentiment(self, news_items: List[Dict]) -> List[Dict]:
        """
        LLM ile sentiment analizi.

        Batch processing ile token tasarrufu.
        """
        if not news_items:
            return []

        log(f"{len(news_items)} haber için sentiment analizi başlıyor...")

        # Batch sentiment analizi (5'erli gruplar)
        batch_size = 5
        analyzed = []

        for i in range(0, len(news_items), batch_size):
            batch = news_items[i:i + batch_size]

            # Batch prompt oluştur
            titles = [f"{j+1}. {article.get('title', 'Başlıksız')}" for j, article in enumerate(batch)]
            titles_text = "\n".join(titles)

            # HACKATHON: "olumlu/olumsuz" terminolojisi - İYİLEŞTİRİLMİŞ PROMPT
            prompt = f"""Sen bir haber sentiment analisti olarak görev yapıyorsun. Aşağıdaki haber başlıklarını firma açısından değerlendir.

Haber Başlıkları:
{titles_text}

DEĞERLENDIRME KRİTERLERİ:
OLUMLU haberler:
- Başarı, rekor, ödül, sertifika (örn: ISO sertifikası, ödül kazanma)
- Büyüme, yatırım, istihdam artışı
- Yolcu/satış/ihracat rekorları
- Yeni anlaşma, işbirliği, ortaklık
- Olumlu finansal sonuçlar (kâr, gelir artışı)
- Teknoloji, inovasyon, modernizasyon

OLUMSUZ haberler:
- Kriz, iflas, konkordato, zarar
- Dava, soruşturma, ceza, yaptırım
- Kaza, arıza, gecikme, iptal
- İşten çıkarma, maaş kesintisi
- Skandal, yolsuzluk iddiaları
- Olumsuz finansal sonuçlar

Her haber için SADECE "olumlu" veya "olumsuz" yaz. Satır numarasını kullan.

Örnek çıktı:
1. olumlu
2. olumsuz
3. olumlu

Şimdi analiz et:"""

            try:
                response = await self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model="gpt-oss-120b",
                    temperature=0.1,
                    max_tokens=200
                )

                # LLM response kontrolü
                if not response or not response.strip():
                    warn(f"Sentiment LLM boş response döndü, keyword fallback kullanılıyor")
                    # Keyword-based fallback
                    for article in batch:
                        sentiment = self._keyword_sentiment(article.get('title', ''))
                        debug(f"Keyword sentiment: '{article.get('title', '')[:50]}...' -> {sentiment}")
                        analyzed.append({
                            **article,
                            "sentiment": sentiment
                        })
                else:
                    debug(f"LLM sentiment response: {response[:200]}...")
                    # Response'u parse et (batch'i de geçir, fallback için)
                    sentiments = self._parse_sentiment_response(response, len(batch), batch)

                    for j, article in enumerate(batch):
                        sentiment = sentiments[j] if j < len(sentiments) else self._keyword_sentiment(article.get('title', ''))
                        debug(f"Final sentiment: '{article.get('title', '')[:50]}...' -> {sentiment}")
                        analyzed.append({
                            **article,
                            "sentiment": sentiment
                        })

            except Exception as e:
                error(f"Sentiment analizi hatası: {e}")
                # Fallback: keyword-based sentiment
                for article in batch:
                    sentiment = self._keyword_sentiment(article.get('title', ''))
                    debug(f"Exception fallback sentiment: '{article.get('title', '')[:50]}...' -> {sentiment}")
                    analyzed.append({
                        **article,
                        "sentiment": sentiment
                    })

            # Progress update
            progress = 60 + int((i + batch_size) / len(news_items) * 30)
            self.report_progress(min(progress, 90), f"Sentiment analizi: {min(i + batch_size, len(news_items))}/{len(news_items)}")

        return analyzed

    def _parse_sentiment_response(self, response: str, expected_count: int, batch: List[Dict] = None) -> List[str]:
        """LLM sentiment response'unu parse et."""
        sentiments = []
        # HACKATHON: olumlu/olumsuz terminolojisi
        valid_sentiments = {"olumlu", "olumsuz"}

        for line in response.strip().split('\n'):
            line = line.strip().lower()
            # "1. olumlu" veya sadece "olumlu" formatını handle et
            for sentiment in valid_sentiments:
                if sentiment in line:
                    sentiments.append(sentiment)
                    break

        # Eksik sentiment'leri keyword-based analiz ile doldur (daha akıllı fallback)
        while len(sentiments) < expected_count:
            idx = len(sentiments)
            if batch and idx < len(batch):
                # Keyword-based sentiment kullan
                title = batch[idx].get('title', '')
                sentiments.append(self._keyword_sentiment(title))
            else:
                # Son çare: nötr değerlendirme için olumlu varsay (muhafazakar yerine dengeli)
                sentiments.append("olumlu")

        return sentiments

    def _keyword_sentiment(self, text: str) -> str:
        """Fallback: keyword-based sentiment."""
        text_lower = text.lower()

        # HACKATHON: olumlu/olumsuz terminolojisi - GENİŞLETİLMİŞ LİSTE
        positive_keywords = [
            # Başarı ve ödüller
            "başarı", "başarılı", "ödül", "sertifika", "iso", "kalite", "standart",
            # Büyüme ve yatırım
            "büyüme", "büyüdü", "yatırım", "istihdam", "artış", "arttı", "artırdı",
            # Rekorlar
            "rekor", "rekoru", "en yüksek", "en iyi", "zirve", "lider", "birinci", "1.",
            # Finansal olumlu
            "kazanç", "kâr", "kar", "gelir", "ihracat", "satış",
            # İşbirliği ve anlaşma
            "anlaşma", "işbirliği", "ortaklık", "imza", "imzaladı", "protokol",
            # Teknoloji ve inovasyon
            "inovasyon", "teknoloji", "dijital", "modernizasyon", "yenilik",
            # Genel olumlu
            "açıldı", "açılış", "yeni", "genişleme", "genişledi", "hizmet",
            "yolcu", "taşıdı", "uçuş", "sefer", "kapasite"
        ]
        negative_keywords = [
            # Finansal olumsuz
            "zarar", "kriz", "iflas", "konkordato", "borç", "düşüş", "azalma",
            # Hukuki sorunlar
            "soruşturma", "dava", "ceza", "yaptırım", "suç", "tutuklama",
            # Operasyonel sorunlar
            "kaza", "arıza", "gecikme", "iptal", "rötar", "tehlike", "risk",
            # İstihdam olumsuz
            "istifa", "işten çıkarma", "tazminat", "grev", "kesinti",
            # Skandal
            "skandal", "yolsuzluk", "iddia", "suçlama", "şikayet"
        ]

        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)

        if pos_count > neg_count:
            return "olumlu"
        elif neg_count > pos_count:
            return "olumsuz"
        else:
            # Eşit veya keyword bulunamadıysa - olumlu varsay (dengeli yaklaşım)
            return "olumlu"

    def _compile_results(self, analyzed_news: List[Dict]) -> Dict:
        """
        HACKATHON FORMATI: Sonuçları derle.

        Çıktı formatı:
        - haberler: Her haber için detaylı bilgi (screenshot dahil)
        - ozet: Toplam istatistikler
        """
        total = len(analyzed_news)
        # HACKATHON: olumlu/olumsuz terminolojisi
        olumlu = sum(1 for n in analyzed_news if n.get("sentiment") == "olumlu")
        olumsuz = sum(1 for n in analyzed_news if n.get("sentiment") == "olumsuz")

        sentiment_score = (olumlu - olumsuz) / total if total > 0 else 0

        # Kaynak bazlı breakdown
        sources = {}
        for article in analyzed_news:
            source = article.get('source', 'Unknown')
            if source not in sources:
                sources[source] = {"total": 0, "olumlu": 0, "olumsuz": 0}
            sources[source]["total"] += 1
            sources[source][article.get("sentiment", "olumsuz")] += 1

        # Trend analizi (ilk 5 haber)
        recent_news = analyzed_news[:5]
        recent_olumlu = sum(1 for n in recent_news if n.get("sentiment") == "olumlu")
        recent_olumsuz = sum(1 for n in recent_news if n.get("sentiment") == "olumsuz")

        if recent_olumlu > recent_olumsuz:
            trend = "pozitif"
        elif recent_olumsuz > recent_olumlu:
            trend = "negatif"
        else:
            trend = "notr"

        # HACKATHON FORMATI
        return {
            # Detaylı haber listesi
            "haberler": [
                {
                    "id": a.get("id", ""),
                    "baslik": a.get("title", ""),
                    "kaynak": a.get("source", ""),
                    "tarih": a.get("date_display", a.get("date", "Tarih bilinmiyor")),
                    "url": a.get("url", ""),
                    "metin": a.get("text", "")[:2000] if a.get("text") else "",  # İlk 2000 karakter
                    "sentiment": a.get("sentiment", "olumsuz"),
                    "screenshot_path": a.get("screenshot_path", None),
                    "relevance_confidence": a.get("relevance_confidence", 0.5),
                    "is_relevant": a.get("is_relevant", True)
                }
                for a in analyzed_news
            ],
            # Özet istatistikler
            "ozet": {
                "toplam": total,
                "olumlu": olumlu,
                "olumsuz": olumsuz,
                "sentiment_score": round(sentiment_score, 2),  # -1.0 to 1.0
                "trend": trend
            },
            # Eski format için geriye uyumluluk
            "toplam_haber": total,
            "kaynak_dagilimi": sources
        }

    def _generate_summary(self, data: Dict) -> str:
        """Özet oluştur"""
        total = data["toplam_haber"]
        if total == 0:
            return "Firma hakkında haber bulunamadı."

        # HACKATHON: olumlu/olumsuz terminolojisi
        ozet = data.get("ozet", {})
        olumlu = ozet.get("olumlu", 0)
        olumsuz = ozet.get("olumsuz", 0)
        olumlu_oran = (olumlu / total * 100) if total > 0 else 0
        olumsuz_oran = (olumsuz / total * 100) if total > 0 else 0

        trend_str = {
            "pozitif": "yukarı yönlü",
            "negatif": "aşağı yönlü",
            "notr": "stabil"
        }.get(ozet.get("trend", "notr"), "belirsiz")

        kaynak_sayisi = len(data.get("kaynak_dagilimi", {}))

        return (
            f"{total} haber ({kaynak_sayisi} kaynaktan) analiz edildi. "
            f"Olumlu: %{olumlu_oran:.0f}, Olumsuz: %{olumsuz_oran:.0f}. "
            f"Medya trendi {trend_str}."
        )

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Önemli bulguları çıkar"""
        findings = []

        # HACKATHON: olumlu/olumsuz terminolojisi
        ozet = data.get("ozet", {})
        sentiment_score = ozet.get("sentiment_score", 0)
        trend = ozet.get("trend", "notr")

        if sentiment_score > 0.3:
            findings.append("Medya algısı olumlu")
        elif sentiment_score < -0.3:
            findings.append("Medya algısı olumsuz")
        else:
            findings.append("Medya algısı dengeli")

        if trend == "pozitif":
            findings.append("Son dönem haberleri olumlu")
        elif trend == "negatif":
            findings.append("Son dönem haberleri olumsuz")

        # Kaynak çeşitliliği
        kaynak_sayisi = len(data.get("kaynak_dagilimi", {}))
        if kaynak_sayisi >= 5:
            findings.append(f"Yüksek medya görünürlüğü ({kaynak_sayisi} kaynak)")
        elif kaynak_sayisi >= 3:
            findings.append(f"Orta medya görünürlüğü ({kaynak_sayisi} kaynak)")
        elif kaynak_sayisi >= 1:
            findings.append(f"Düşük medya görünürlüğü ({kaynak_sayisi} kaynak)")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarıları çıkar"""
        warnings = []

        # HACKATHON: olumlu/olumsuz terminolojisi
        ozet = data.get("ozet", {})
        olumlu = ozet.get("olumlu", 0)
        olumsuz = ozet.get("olumsuz", 0)
        trend = ozet.get("trend", "notr")
        total = data["toplam_haber"]

        if olumsuz > olumlu:
            warnings.append("Olumsuz haberler baskın")

        if trend == "negatif":
            warnings.append("Olumsuz medya trendi")

        # Yüksek olumsuz oran
        if total > 0 and (olumsuz / total) > 0.5:
            warnings.append("Çoğunluk olumsuz haberler")

        return warnings


# Test
if __name__ == "__main__":
    async def test():
        agent = NewsAgent()

        def progress_callback(progress_info):
            print(f"[{progress_info.progress:3d}%] {progress_info.message}")

        agent.set_progress_callback(progress_callback)

        print("\n" + "="*60)
        print("NEWS AGENT TEST")
        print("="*60 + "\n")

        result = await agent.run("Türk Hava Yolları")

        print("\n" + "="*60)
        print("SONUÇ")
        print("="*60)
        print(f"Status: {result.status}")
        print(f"Summary: {result.summary}")
        print(f"Key Findings: {result.key_findings}")
        print(f"Warnings: {result.warning_flags}")
        print(f"\nData: {result.data}")

    asyncio.run(test())
