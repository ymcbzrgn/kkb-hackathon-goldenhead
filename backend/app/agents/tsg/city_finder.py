"""
TSG City Finder - WebSearch ile firma şehri bulma
Halüsinasyon korumalı!

Strateji:
1. Google'da firma merkezi ara
2. LLM ile sonuçları yorumla (SADECE sonuçlardaki bilgiyi kullan)
3. 81 il listesinden doğrula
4. Bulunamazsa İstanbul fallback
"""
import asyncio
import urllib.parse
from typing import Optional, List
from app.llm.client import LLMClient
from app.agents.tsg.logger import log, step, success, warn, error


class TSGCityFinder:
    """Firma merkezini WebSearch ile bul - Halüsinasyon korumalı!"""

    # Türkiye'nin 81 ili (TSG dropdown formatında)
    VALID_CITIES = [
        "ADANA", "ADIYAMAN", "AFYONKARAHİSAR", "AĞRI", "AKSARAY", "AMASYA",
        "ANKARA", "ANTALYA", "ARDAHAN", "ARTVİN", "AYDIN", "BALIKESİR",
        "BARTIN", "BATMAN", "BAYBURT", "BİLECİK", "BİNGÖL", "BİTLİS",
        "BOLU", "BURDUR", "BURSA", "ÇANAKKALE", "ÇANKIRI", "ÇORUM",
        "DENİZLİ", "DİYARBAKIR", "DÜZCE", "EDİRNE", "ELAZIĞ", "ERZİNCAN",
        "ERZURUM", "ESKİŞEHİR", "GAZİANTEP", "GİRESUN", "GÜMÜŞHANE",
        "HAKKARİ", "HATAY", "IĞDIR", "ISPARTA", "İSTANBUL", "İZMİR",
        "KAHRAMANMARAŞ", "KARABÜK", "KARAMAN", "KARS", "KASTAMONU",
        "KAYSERİ", "KIRIKKALE", "KIRKLARELİ", "KIRŞEHİR", "KİLİS",
        "KOCAELİ", "KONYA", "KÜTAHYA", "MALATYA", "MANİSA", "MARDİN",
        "MERSİN", "MUĞLA", "MUŞ", "NEVŞEHİR", "NİĞDE", "ORDU", "OSMANİYE",
        "RİZE", "SAKARYA", "SAMSUN", "SİİRT", "SİNOP", "SİVAS", "ŞANLIURFA",
        "ŞIRNAK", "TEKİRDAĞ", "TOKAT", "TRABZON", "TUNCELİ", "UŞAK",
        "VAN", "YALOVA", "YOZGAT", "ZONGULDAK"
    ]

    # Büyük şirketlerin bilinen merkezleri (halüsinasyon önleme için cache)
    KNOWN_COMPANIES = {
        "TURKCELL": "İSTANBUL",
        "VODAFONE": "İSTANBUL",
        "TÜRK TELEKOM": "ANKARA",
        "THY": "İSTANBUL",
        "TÜRK HAVA YOLLARI": "İSTANBUL",
        "GARANTI": "İSTANBUL",
        "AKBANK": "İSTANBUL",
        "İŞ BANKASI": "İSTANBUL",
        "YAPI KREDİ": "İSTANBUL",
        "KOÇ HOLDİNG": "İSTANBUL",
        "SABANCI": "İSTANBUL",
        "ARÇELIK": "İSTANBUL",
        "FORD OTOSAN": "KOCAELİ",
        "TOFAŞ": "BURSA",
        "VESTEL": "MANİSA",
        "ÜLKER": "İSTANBUL",
        "BİM": "İSTANBUL",
        "MİGROS": "İSTANBUL",
        "ŞOK": "İSTANBUL",
        "LC WAİKİKİ": "İSTANBUL",
        "ZORLU": "İSTANBUL",
        "ECZACIBAŞI": "İSTANBUL",
        "TÜPRAŞ": "KOCAELİ",
        "PETKİM": "İZMİR",
        "ENERJISA": "İSTANBUL",
        "ASELSAN": "ANKARA",
        "HAVELSAN": "ANKARA",
        "TAI": "ANKARA",
        "ROKETSAN": "ANKARA",
        "TUSAŞ": "ANKARA",
    }

    def __init__(self):
        self.llm = LLMClient()

    async def find_city(self, company_name: str) -> str:
        """
        Firma merkezini bul.

        Returns:
            str: Şehir adı (TSG dropdown formatında, örn: "İSTANBUL")
        """
        step(f"ŞEHİR ARANIYOR: {company_name}")

        # 1. Önce bilinen şirketler cache'ine bak
        city = self._check_known_companies(company_name)
        if city:
            success(f"Bilinen şirket: {city}")
            return city

        # 2. WebSearch ile ara
        search_results = await self._web_search(company_name)

        if search_results:
            log(f"WebSearch sonuçları: {len(search_results)} snippet")

            # 3. LLM ile yorumla (halüsinasyon korumalı)
            city = await self._extract_city_from_results(company_name, search_results)
            if city:
                success(f"WebSearch ile bulundu: {city}")
                return city
        else:
            warn("WebSearch sonuç bulamadı")

        # 4. Fallback: İstanbul (Türkiye'nin ticari merkezi)
        warn("Şehir bulunamadı, İSTANBUL varsayılıyor")
        return "İSTANBUL"

    def _check_known_companies(self, company_name: str) -> Optional[str]:
        """Bilinen büyük şirketlerin merkezlerini kontrol et."""
        name_upper = company_name.upper()

        # Tam eşleşme
        if name_upper in self.KNOWN_COMPANIES:
            return self.KNOWN_COMPANIES[name_upper]

        # Kısmi eşleşme
        for known_name, city in self.KNOWN_COMPANIES.items():
            if known_name in name_upper or name_upper in known_name:
                return city

        return None

    async def _web_search(self, company_name: str) -> List[str]:
        """
        Google ile arama yap ve sonuçları döndür.

        Playwright kullanarak Google'da arama yapar.
        """
        # Arama sorgusu: Firma merkezi hangi şehir
        queries = [
            f"{company_name} şirket merkezi hangi şehir türkiye",
            f"{company_name} genel müdürlük adresi",
            f"{company_name} headquarters turkey city",
        ]

        results = []

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await context.new_page()

                for query in queries[:2]:  # İlk 2 sorguyu dene
                    try:
                        encoded_query = urllib.parse.quote(query)
                        search_url = f"https://www.google.com/search?q={encoded_query}&hl=tr"

                        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(2)

                        # Google snippet'larını topla
                        # Ana sonuç snippet'ları
                        selectors = [
                            ".VwiC3b",  # Ana snippet
                            ".hgKElc",  # Öne çıkan snippet
                            ".ILfuVd",  # Bilgi kutusu
                            "[data-attrid='description']",  # Açıklama
                            ".kno-rdesc span",  # Knowledge panel
                        ]

                        for selector in selectors:
                            try:
                                elements = await page.query_selector_all(selector)
                                for elem in elements[:3]:
                                    text = await elem.text_content()
                                    if text and len(text) > 20:
                                        results.append(text.strip())
                            except:
                                continue

                        # Yeterli sonuç varsa dur
                        if len(results) >= 5:
                            break

                    except Exception as e:
                        warn(f"Arama hatası ({query[:30]}...): {e}")
                        continue

                await browser.close()

        except ImportError:
            error("Playwright yüklü değil!")
        except Exception as e:
            error(f"WebSearch hatası: {e}")

        return results[:10]  # Max 10 sonuç

    async def _extract_city_from_results(
        self,
        company_name: str,
        search_results: List[str]
    ) -> Optional[str]:
        """
        LLM ile arama sonuçlarından şehir çıkar.

        KRİTİK: Halüsinasyon koruması aktif!
        - SADECE arama sonuçlarındaki bilgiyi kullan
        - Emin değilse "BİLİNMİYOR" de
        """

        # Sonuçları birleştir
        results_text = "\n".join(f"- {r}" for r in search_results)

        prompt = f"""Sen bir Türkiye şirket merkezi tespit uzmanısın.

GÖREV: "{company_name}" şirketinin Türkiye'deki MERKEZ ŞEHRİNİ bul.

WEB ARAMA SONUÇLARI:
{results_text}

KRİTİK KURALLAR:
1. SADECE yukarıdaki arama sonuçlarındaki bilgiyi kullan
2. Emin değilsen "BİLİNMİYOR" yaz
3. ASLA halüsinasyon yapma - sonuçlarda açıkça yazmıyorsa bilmiyorsun!
4. Şube veya ofis değil, MERKEZ/GENEL MÜDÜRLÜK şehrini bul
5. Sadece şehir adı yaz (örn: İSTANBUL, ANKARA, İZMİR)

TÜRKİYE ŞEHİRLERİ: Adana, Ankara, Antalya, Bursa, Denizli, Diyarbakır,
Eskişehir, Gaziantep, İstanbul, İzmir, Kayseri, Kocaeli, Konya,
Malatya, Manisa, Mersin, Samsun, Trabzon, Van, vb.

CEVAP (SADECE şehir adı veya BİLİNMİYOR):"""

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-oss-120b",
                temperature=0.0,  # Sıfır yaratıcılık - sadece gerçekleri söyle
                max_tokens=50
            )

            # Cevabı temizle
            city = response.strip().upper()
            city = city.replace(".", "").replace(",", "").strip()

            # "BİLİNMİYOR" kontrolü
            if "BİLİNMİYOR" in city or "BİLİNMİ" in city or "UNKNOWN" in city:
                warn("LLM şehri bulamadı (halüsinasyon koruması aktif)")
                return None

            # Geçerli Türkiye şehri mi kontrol et
            validated = self._validate_city(city)
            if validated:
                return validated

            warn(f"Geçersiz şehir yanıtı: {city}")
            return None

        except Exception as e:
            error(f"LLM şehir çıkarma hatası: {e}")
            return None

    def _validate_city(self, city: str) -> Optional[str]:
        """
        Şehir adını doğrula ve TSG formatına çevir.

        Returns:
            str: Geçerli şehir adı veya None
        """
        if not city:
            return None

        city = city.upper().strip()

        # Tam eşleşme
        if city in self.VALID_CITIES:
            return city

        # Türkçe karakter varyasyonları
        variations = {
            "ISTANBUL": "İSTANBUL",
            "IZMIR": "İZMİR",
            "ISPARTA": "ISPARTA",
            "IGDIR": "IĞDIR",
            "SIVAS": "SİVAS",
            "SINOP": "SİNOP",
            "SIIRT": "SİİRT",
            "SANLIURFA": "ŞANLIURFA",
            "SIRNAK": "ŞIRNAK",
            "CANKIRI": "ÇANKIRI",
            "CANAKKALE": "ÇANAKKALE",
            "CORUM": "ÇORUM",
            "GUMUSHANE": "GÜMÜŞHANE",
            "KUTAHYA": "KÜTAHYA",
            "MUGLA": "MUĞLA",
            "MUS": "MUŞ",
            "NEVSEHIR": "NEVŞEHİR",
            "NIGDE": "NİĞDE",
            "KIRIKKALE": "KIRIKKALE",
            "KIRKLARELI": "KIRKLARELİ",
            "KIRSEHIR": "KIRŞEHİR",
            "KILIS": "KİLİS",
            "AFYONKARAHISAR": "AFYONKARAHİSAR",
            "AGRI": "AĞRI",
            "BILECIK": "BİLECİK",
            "BINGOL": "BİNGÖL",
            "BITLIS": "BİTLİS",
            "DIYARBAKIR": "DİYARBAKIR",
            "ELAZIG": "ELAZIĞ",
            "ESKISEHIR": "ESKİŞEHİR",
            "GIRESUN": "GİRESUN",
            "HAKKARI": "HAKKARİ",
            "KAHRAMANMARAS": "KAHRAMANMARAŞ",
            "TEKIRDAG": "TEKİRDAĞ",
        }

        if city in variations:
            return variations[city]

        # Kısmi eşleşme (şehir adı içinde geçiyorsa)
        for valid_city in self.VALID_CITIES:
            # Tam kelime eşleşmesi
            if city == valid_city.replace("İ", "I").replace("Ş", "S").replace("Ğ", "G").replace("Ü", "U").replace("Ö", "O").replace("Ç", "C"):
                return valid_city
            # Kısmi eşleşme
            if len(city) >= 4 and (city in valid_city or valid_city in city):
                return valid_city

        return None


# Test için
async def test_city_finder():
    """City finder test fonksiyonu."""
    finder = TSGCityFinder()

    test_companies = [
        "Turkcell",
        "Vodafone Net",
        "Ford Otosan",
        "Vestel Elektronik",
        "Aselsan",
        "Bilinmeyen Şirket AŞ",
    ]

    print("\n" + "="*60)
    print("TSG City Finder Test")
    print("="*60)

    for company in test_companies:
        city = await finder.find_city(company)
        print(f"\n{company}: {city}")


if __name__ == "__main__":
    asyncio.run(test_city_finder())
