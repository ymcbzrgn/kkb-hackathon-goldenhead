"""
News Article Extraction - LLM ile haber parse
Halusinasyon onleme odakli, TSG/Ihale pattern

Ozellikler:
1. System + User prompt ayrimi (token tasarrufu)
2. Structured JSON output (validation ile)
3. Halusinasyon kontrolleri
4. Temperature=0.1 (deterministik)
5. Türkçe tarih format desteği (HACKATHON)
"""
import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from app.llm.client import LLMClient
from app.agents.news.logger import log, success, error, warn, debug


# ============================================
# TÜRKÇE TARİH NORMALİZASYONU (HACKATHON)
# ============================================
TURKISH_MONTHS = {
    'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4,
    'mayıs': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8,
    'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12,
    # ASCII alternatifleri
    'subat': 2, 'mayis': 5, 'agustos': 8, 'eylul': 9, 'kasim': 11, 'aralik': 12
}

DATE_PATTERNS = [
    # ISO format: 2025-12-08
    (r'(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
    # Türkçe format: 08.12.2025
    (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
    # Slash format: 08/12/2025
    (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
    # Türkçe ay adı: 8 Aralık 2025 veya 08 Aralık 2025
    (r'(\d{1,2})\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|subat|mayis|agustos|eylul|kasim|aralik)\s+(\d{4})',
     lambda m: f"{m.group(3)}-{str(TURKISH_MONTHS.get(m.group(2).lower(), 1)).zfill(2)}-{m.group(1).zfill(2)}"),
]


def normalize_date(date_str: str) -> str:
    """
    Farklı tarih formatlarını YYYY-MM-DD formatına normalize et.

    HACKATHON GEREKSİNİMİ: Tarih filtresi için tutarlı format gerekli.

    Args:
        date_str: Ham tarih string'i (herhangi bir formatta)

    Returns:
        YYYY-MM-DD formatında tarih veya "unknown"
    """
    if not date_str or date_str == "unknown":
        return "unknown"

    date_str_lower = date_str.lower().strip()

    # Her pattern'i dene
    for pattern, converter in DATE_PATTERNS:
        match = re.search(pattern, date_str_lower, re.IGNORECASE)
        if match:
            try:
                normalized = converter(match)
                # Validation: Geçerli tarih mi?
                datetime.strptime(normalized, "%Y-%m-%d")
                return normalized
            except (ValueError, IndexError):
                continue

    # Hiçbir pattern eşleşmedi
    return "unknown"


def is_date_in_range(date_str: str, min_year: int = 2022, max_year: int = 2025) -> Tuple[bool, str]:
    """
    Tarihin belirtilen aralıkta olup olmadığını kontrol et.

    HACKATHON GEREKSİNİMİ: Son 3 yıl (2022-2025) haberleri.

    Args:
        date_str: YYYY-MM-DD formatında tarih veya "unknown"
        min_year: Minimum yıl (dahil)
        max_year: Maximum yıl (dahil)

    Returns:
        Tuple[bool, str]: (is_in_range, display_date)
        - Unknown tarihler: (True, "Tarih bilinmiyor") - Dahil edilir (kullanıcı tercihi)
        - Aralıkta: (True, date_str)
        - Aralık dışı: (False, date_str)
    """
    if date_str == "unknown" or not date_str:
        return (True, "Tarih bilinmiyor")  # KULLANICI TERCİHİ: Unknown dahil et

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.year

        if min_year <= year <= max_year:
            return (True, date_str)
        else:
            return (False, date_str)  # Aralık dışı, filtrelenecek

    except ValueError:
        return (True, "Tarih bilinmiyor")  # Parse edilemedi, dahil et


# ============================================
# SYSTEM PROMPT (Sabit - Cache'lenir)
# ============================================
NEWS_EXTRACTION_SYSTEM_PROMPT = """Sen bir haber sayfasi parse uzmanisin.

ROL: Verilen HTML/text'ten haber bilgilerini SADECE METIN ICINDE ACIKCA YAZANLARI cikart.

ZORUNLU ALANLAR (4 tane):
1. title: Haber basligi (string)
2. text: Ana haber metni - TAM ve TEMIZ (reklam/menu/footer EXCLUDE)
3. date: Yayin tarihi (YYYY-MM-DD formatinda)
4. image_url: Ana haber gorseli URL'i (tam URL, src degeri)

KRITIK KURALLAR (HALUSINASYON ONLEME):
- ASLA tahmin yapma, varsayimda bulunma!
- SADECE metinde ACIKCA yazan bilgileri cikar
- Tarih bulamazsan "unknown" don
- Gorsel bulamazsan null don
- Haber metni icinde reklam/menu/footer OLMAMALI (sadece haber)
- Title cok kisa ise (< 10 karakter) "unknown" don
- Text cok kisa ise (< 50 karakter) "insufficient" don

CIKTI FORMATI:
SADECE JSON don, hicbir aciklama yapma!

{
    "title": "..." veya "unknown",
    "text": "..." veya "insufficient",
    "date": "YYYY-MM-DD" veya "unknown",
    "image_url": "https://..." veya null
}"""


# ============================================
# USER PROMPT TEMPLATE (Dinamik)
# ============================================
NEWS_EXTRACTION_USER_PROMPT_TEMPLATE = """HABER SAYFASI ICERIGINI PARSE ET:

URL: {url}
KAYNAK: {source}

HTML (ilk 15000 karakter):
{html_content}

TEMIZ METIN (ilk 10000 karakter):
{text_content}

Yukaridaki haber sayfasini analiz et ve JSON formatinda don.
SADECE metinde acikca yazan bilgileri cikar!"""


class NewsExtractor:
    """
    LLM ile haber extraction.
    
    TSG/Ihale pattern:
    - System prompt sabit (cache)
    - User prompt dinamik
    - Temperature 0.1 (deterministik)
    - JSON validation
    - Halusinasyon kontrolleri
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    async def extract_article(
        self,
        url: str,
        html_content: str,
        text_content: str,
        source_name: str = "Unknown"
    ) -> Optional[Dict]:
        """
        Haber sayfasini LLM ile parse et.
        
        Args:
            url: Haber URL'i
            html_content: HTML icerik
            text_content: Temiz text icerik
            source_name: Kaynak adi (debug icin)
        
        Returns:
            Dict veya None (basarisiz durumda)
        """
        try:
            log(f"LLM extraction basliyor: {source_name}")

            # User prompt hazirla
            user_prompt = NEWS_EXTRACTION_USER_PROMPT_TEMPLATE.format(
                url=url,
                source=source_name,
                html_content=html_content[:15000],  # Limit
                text_content=text_content[:10000]   # Limit
            )

            # HACKATHON: LLM retry mekanizmasi (max 3 deneme + delay)
            article = None
            response = ""
            for attempt in range(3):
                try:
                    # Retry'lar arası delay (rate limit için)
                    if attempt > 0:
                        import asyncio
                        await asyncio.sleep(1.0)  # 1 saniye bekle

                    # LLM cagir (TSG pattern)
                    response = await self.llm.chat(
                        messages=[
                            {"role": "system", "content": NEWS_EXTRACTION_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        model="gpt-oss-120b",
                        temperature=0.1,  # Deterministik
                        max_tokens=2048
                    )

                    # Boş response kontrolü
                    if not response or not response.strip():
                        if attempt < 2:
                            warn(f"LLM boş response, retry {attempt + 1}/3... ({source_name})")
                            continue  # Tekrar dene
                        else:
                            error(f"LLM 3 kez boş response döndü ({source_name})")
                            return None

                    # JSON parse
                    article = json.loads(response)
                    break  # Başarılı, döngüden çık

                except json.JSONDecodeError as e:
                    if attempt < 2:
                        warn(f"JSON parse error, retry {attempt + 1}/3... ({source_name})")
                        continue  # Tekrar dene
                    else:
                        error(f"LLM response invalid JSON ({source_name}): {e}")
                        debug(f"LLM response: {response[:500] if response else 'EMPTY'}")
                        return None

            if not article:
                return None

            # Validation (halusinasyon kontrolu!)
            if not self._validate_article(article, url):
                warn(f"LLM extraction validation FAILED: {source_name}")
                return None

            success(f"LLM extraction OK: {source_name}")
            return article

        except Exception as e:
            error(f"LLM extraction error ({source_name}): {e}")
            return None
    
    def _validate_article(self, article: Dict, url: str) -> bool:
        """
        LLM ciktisini validate et (halusinasyon kontrolu).
        
        Kontroller:
        1. Gerekli alanlar var mi?
        2. Title anlamli mi? (unknown degil, > 10 karakter)
        3. Text yeterli mi? (insufficient degil, > 50 karakter)
        4. Date formati dogru mu? (YYYY-MM-DD veya unknown)
        5. Image URL gecerli mi? (https:// ile basliyor veya null)
        """
        # 1. Gerekli alanlar
        required_fields = ["title", "text", "date", "image_url"]
        for field in required_fields:
            if field not in article:
                warn(f"Validation FAIL: Missing field '{field}'")
                return False
        
        # 2. Title kontrolu
        title = article.get("title", "")
        if title == "unknown":
            warn(f"Validation FAIL: Title is 'unknown'")
            return False
        if len(title) < 10:
            warn(f"Validation FAIL: Title too short ({len(title)} chars)")
            return False
        
        # 3. Text kontrolu
        text = article.get("text", "")
        if text == "insufficient":
            warn(f"Validation FAIL: Text is 'insufficient'")
            return False
        if len(text) < 50:
            warn(f"Validation FAIL: Text too short ({len(text)} chars)")
            return False
        
        # 4. Date kontrolu (YYYY-MM-DD veya unknown)
        # HACKATHON: Tarih normalizasyonu
        date = article.get("date", "")
        if date and date != "unknown":
            # Türkçe formatları normalize et
            normalized_date = normalize_date(date)
            article["date"] = normalized_date
            debug(f"Tarih normalize edildi: '{date}' -> '{normalized_date}'")
        
        # 5. Image URL kontrolu
        image_url = article.get("image_url")
        if image_url is not None:
            if not isinstance(image_url, str):
                warn(f"Validation FAIL: Image URL not string")
                article["image_url"] = None
            elif not image_url.startswith("http"):
                warn(f"Validation FAIL: Invalid image URL '{image_url}'")
                article["image_url"] = None
        
        # Validation passed!
        debug(f"Validation OK: title={len(title)} chars, text={len(text)} chars")
        return True
    
    def _is_valid_date(self, date_str: str) -> bool:
        """YYYY-MM-DD format kontrolu."""
        try:
            from datetime import datetime
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False


# Singleton instance
_extractor = None

def get_extractor() -> NewsExtractor:
    """Global NewsExtractor instance al (singleton)."""
    global _extractor
    if _extractor is None:
        _extractor = NewsExtractor()
    return _extractor


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        extractor = NewsExtractor()
        
        # Mock data
        html = """
        <html>
        <head><title>Test Haber - ABC A.Ş. Sermaye Artırdı</title></head>
        <body>
            <h1>ABC A.Ş. Sermaye Artırdı</h1>
            <time>2024-11-15</time>
            <article>
                ABC A.Ş., olağanüstü genel kurulda sermayesini 100 milyon TL'ye 
                yükseltme kararı aldı. Şirket yetkilileri büyüme hedeflerini 
                desteklemek için sermaye artışına gittiklerini açıkladı.
            </article>
            <img src="https://example.com/abc-photo.jpg" />
        </body>
        </html>
        """
        
        text = "ABC A.Ş. Sermaye Artırdı. ABC A.Ş., sermayesini 100 milyon TL'ye yükseltti."
        
        result = await extractor.extract_article(
            url="https://example.com/abc-haberi",
            html_content=html,
            text_content=text,
            source_name="Test Source"
        )
        
        print("Result:", json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
