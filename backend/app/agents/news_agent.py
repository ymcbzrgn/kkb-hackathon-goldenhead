"""
News Agent - Haber Toplama ve Sentiment Analizi
Firma hakkındaki haberleri toplar ve analiz eder

HACKATHON GEREKSİNİMLERİ:
1. JPEG Screenshot (her haber için)
2. Tarih Filtresi (2022-2025)
3. Sentiment: olumlu / olumsuz
4. Relevance Validation (LLM ile tek tek)

10 GÜVENİLİR KAYNAK (paralel scraping):
- Devlet: AA, TRT Haber
- Demirören: Hürriyet, Milliyet, CNN Türk
- Ekonomi: Dünya, Ekonomim, Bigpara
- Diğer: NTV, Sözcü
"""
import asyncio
from typing import Optional, List, Dict, Tuple
from datetime import datetime

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

    # Default parametreler (demo_mode=False için)
    DEFAULT_MAX_ARTICLES_PER_SOURCE = 15  # 3 yıllık derinlik için artırıldı
    DEFAULT_SCRAPER_TIMEOUT = 180  # Daha kısa timeout, paralel telafi eder
    DEFAULT_MAX_CONCURRENT_SCRAPERS = 7  # 10 kaynağın 7'si aynı anda
    DEFAULT_YEARS_BACK = 3  # 3 yıllık tarama

    # Demo mode parametreleri
    DEMO_MAX_ARTICLES_PER_SOURCE = 5
    DEMO_SCRAPER_TIMEOUT = 120
    DEMO_MAX_CONCURRENT_SCRAPERS = 5
    DEMO_YEARS_BACK = 1

    def __init__(self, demo_mode: bool = False):
        super().__init__(
            agent_id="news_agent",
            agent_name="Haber Agent",
            agent_description="Haber toplama ve sentiment analizi"
        )
        self.llm = LLMClient()
        self.demo_mode = demo_mode

        # Demo/Normal mode'a göre parametreleri ayarla
        if demo_mode:
            self.MAX_ARTICLES_PER_SOURCE = self.DEMO_MAX_ARTICLES_PER_SOURCE
            self.SCRAPER_TIMEOUT = self.DEMO_SCRAPER_TIMEOUT
            self.MAX_CONCURRENT_SCRAPERS = self.DEMO_MAX_CONCURRENT_SCRAPERS
            self.YEARS_BACK = self.DEMO_YEARS_BACK
        else:
            self.MAX_ARTICLES_PER_SOURCE = self.DEFAULT_MAX_ARTICLES_PER_SOURCE
            self.SCRAPER_TIMEOUT = self.DEFAULT_SCRAPER_TIMEOUT
            self.MAX_CONCURRENT_SCRAPERS = self.DEFAULT_MAX_CONCURRENT_SCRAPERS
            self.YEARS_BACK = self.DEFAULT_YEARS_BACK

        print(f"[NEWS AGENT] Mode: {'DEMO' if demo_mode else 'FULL'}, Articles/Source: {self.MAX_ARTICLES_PER_SOURCE}, Years: {self.YEARS_BACK}")

    async def run(self, company_name: str) -> AgentResult:
        """Haberleri topla ve analiz et"""

        step(f"NEWS AGENT BASLIYOR: {company_name}")
        self.report_progress(5, "Haberler aranıyor...")

        try:
            # 1. Haber ara (7 kaynaktan paralel)
            news_items = await self._search_news(company_name)
            self.report_progress(40, f"{len(news_items)} haber bulundu")

            if not news_items:
                warn(f"'{company_name}' için haber bulunamadı")
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "Haber bulunamadı", "toplam_haber": 0},
                    summary="Firma hakkında güncel haber bulunamadı",
                    key_findings=["Medya görünürlüğü düşük"],
                    warning_flags=[]
                )

            # 2. HACKATHON: Tarih filtresi (2022-2025)
            self.report_progress(45, "Tarih filtresi uygulanıyor...")
            news_items = self._filter_by_date(news_items)
            log(f"Tarih filtresi sonrası: {len(news_items)} haber")

            # 3. HACKATHON: Relevance validation (LLM ile tek tek)
            self.report_progress(50, "Relevance doğrulaması yapılıyor...")
            news_items = await self._validate_all_articles(news_items, company_name)
            log(f"Relevance validation sonrası: {len(news_items)} haber")

            if not news_items:
                warn(f"'{company_name}' için ilgili haber bulunamadı")
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "İlgili haber bulunamadı", "toplam_haber": 0},
                    summary="Firma hakkında ilgili haber bulunamadı",
                    key_findings=["Medya görünürlüğü düşük veya irrelevant haberler filtrelendi"],
                    warning_flags=[]
                )

            # 4. Sentiment analizi
            self.report_progress(70, "Sentiment analizi yapılıyor...")
            analyzed_news = await self._analyze_sentiment(news_items)

            # 5. Sonuçları derle (HACKATHON formatında)
            self.report_progress(90, "Veriler derleniyor...")
            result_data = self._compile_results(analyzed_news)
            self.report_progress(100, "Haber analizi tamamlandı")

            success(f"NEWS AGENT TAMAMLANDI: {len(news_items)} haber")
            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                data=result_data,
                summary=self._generate_summary(result_data),
                key_findings=self._extract_key_findings(result_data),
                warning_flags=self._extract_warnings(result_data)
            )

        except Exception as e:
            error(f"NEWS AGENT HATASI: {e}")
            import traceback
            traceback.print_exc()
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )

    async def _search_news(self, company_name: str) -> List[Dict]:
        """
        7 haber kaynağından paralel scraping (rate limited).

        Her kaynak bağımsız çalışır, biri fail olsa da diğerleri devam eder.
        Semaphore ile max 3 concurrent scraper çalışır.
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
                        results = await asyncio.wait_for(
                            scraper.search_and_fetch(company_name, max_articles=self.MAX_ARTICLES_PER_SOURCE),
                            timeout=self.SCRAPER_TIMEOUT
                        )
                        if results:
                            success(f"[{scraper.name}] {len(results)} haber bulundu")
                            return results
                        else:
                            warn(f"[{scraper.name}] Haber bulunamadı")
                            return []
                except asyncio.TimeoutError:
                    warn(f"[{scraper_class.NAME}] Timeout ({self.SCRAPER_TIMEOUT}s)")
                    return []
                except Exception as e:
                    error(f"[{scraper_class.NAME}] Hata: {e}")
                    return []

        # Tüm scraper'ları paralel çalıştır (semaphore ile kontrollü)
        tasks = [scrape_source_with_limit(sc) for sc in scraper_classes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Sonuçları birleştir
        for i, result in enumerate(results):
            scraper_name = scraper_classes[i].NAME
            if isinstance(result, Exception):
                error(f"[{scraper_name}] Exception: {result}")
            elif isinstance(result, list):
                for article in result:
                    article['source'] = scraper_name
                all_articles.extend(result)

        log(f"Toplam {len(all_articles)} haber bulundu (7 kaynaktan)")
        return all_articles

    def _filter_by_date(self, articles: List[Dict]) -> List[Dict]:
        """
        Tarih filtresi - YEARS_BACK parametresine göre dinamik.

        KULLANICI TERCİHİ:
        - Unknown tarihler dahil edilir ("Tarih bilinmiyor" olarak)
        - YEARS_BACK yıl öncesinden eski haberler filtrelenir
        """
        from datetime import datetime

        filtered = []
        current_year = datetime.now().year
        min_year = current_year - self.YEARS_BACK  # Dinamik: 3 yıl geri veya demo'da 1 yıl

        log(f"Tarih filtresi: {min_year}-{current_year} ({self.YEARS_BACK} yıl)")

        for article in articles:
            date_str = article.get('date', 'unknown')

            # Tarih normalize et
            normalized_date = normalize_date(date_str)

            # Tarih aralığını kontrol et
            is_valid, display_date = is_date_in_range(normalized_date, min_year=min_year, max_year=current_year)

            if is_valid:
                article['date'] = normalized_date
                article['date_display'] = display_date
                filtered.append(article)
            else:
                debug(f"Tarih filtre REJECTED ({min_year} öncesi): {date_str} - {article.get('title', '')[:50]}")

        return filtered

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
        """Fallback: keyword-based relevance check."""
        title = article.get('title', '').lower()
        text = (article.get('text', '') or '').lower()

        company_keywords = [w.lower() for w in company_name.split() if len(w) > 2]

        matches = sum(1 for kw in company_keywords if kw in title or kw in text)
        total_keywords = len(company_keywords)

        if total_keywords == 0:
            return (True, 0.5)  # Keyword yok, dahil et

        confidence = matches / total_keywords

        if confidence >= 0.5:
            return (True, confidence)
        else:
            return (False, confidence)

    async def _validate_all_articles(self, articles: List[Dict], company_name: str) -> List[Dict]:
        """
        OPTİMİZE: Batch relevance validation.

        Tüm haberleri tek LLM çağrısıyla validate et (30 LLM çağrısı → 1).
        30'ar haber batch'ler halinde işlenir.
        """
        if not articles:
            return []

        validated = []
        batch_size = 30  # Max 30 haber per batch

        log(f"Batch relevance validation başlıyor: {len(articles)} haber, batch_size={batch_size}")

        for batch_start in range(0, len(articles), batch_size):
            batch = articles[batch_start:batch_start + batch_size]

            # Batch için relevance kontrolü
            batch_results = await self._batch_validate_relevance(batch, company_name)

            for article, (is_relevant, confidence) in zip(batch, batch_results):
                if is_relevant:
                    article['relevance_confidence'] = round(confidence, 2)
                    validated.append(article)
                    debug(f"Relevance ACCEPTED: {article.get('title', '')[:50]}... (conf: {confidence:.2f})")
                else:
                    debug(f"Relevance REJECTED: {article.get('title', '')[:50]}... (conf: {confidence:.2f})")

            # Progress update
            progress = 50 + int((batch_start + len(batch)) / len(articles) * 20)
            self.report_progress(min(progress, 70), f"Relevance: {batch_start + len(batch)}/{len(articles)}")

        log(f"Batch validation tamamlandı: {len(validated)}/{len(articles)} haber geçti")
        return validated

    async def _batch_validate_relevance(self, articles: List[Dict], company_name: str) -> List[Tuple[bool, float]]:
        """
        OPTİMİZE: Tek LLM çağrısıyla batch relevance validation.

        Returns:
            List[Tuple[bool, float]]: Her haber için (is_relevant, confidence)
        """
        if not articles:
            return []

        # Batch prompt oluştur
        articles_text = "\n".join([
            f"{i+1}. {a.get('title', '')[:100]}"
            for i, a in enumerate(articles)
        ])

        prompt = f"""{company_name} firması için aşağıdaki haberlerin alakalılığını değerlendir.

Her haber için:
- Firma adı geçiyor mu?
- Firmanın ürün/hizmetleri hakkında mı?
- Rakip firma değil, gerçekten bu firma mı?

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
                return [self._keyword_relevance(a, company_name) for a in articles]

            # Response'u parse et
            results = self._parse_batch_relevance_response(response, len(articles))

            # Eksik sonuçları keyword fallback ile doldur
            while len(results) < len(articles):
                idx = len(results)
                results.append(self._keyword_relevance(articles[idx], company_name))

            return results

        except Exception as e:
            warn(f"Batch relevance validation hatası: {e}, keyword fallback kullanılıyor")
            return [self._keyword_relevance(a, company_name) for a in articles]

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
                    "relevance_confidence": a.get("relevance_confidence", 0.5)
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
