"""
Ihale Company Matcher - LLM ile Firma Eslestirme

TSG'den gelen firma bilgileriyle (Vergi No, Mersis No, Firma Adi)
Resmi Gazete'deki yasakli firmayi eslestirir.

Eslestirme Onceligi:
1. Vergi No -> %100 guvenilir
2. Firma Adi -> LLM ile dogrulama (temperature=0.0)

KRITIK: temperature=0.0 ile halusnasyon engelleniyor!
"""
from typing import Optional, Dict, Any, List
from app.llm.client import LLMClient
from app.agents.ihale.logger import log, step, success, warn, error


# ============================================
# SYSTEM PROMPT (Sabit - Token tasarrufu)
# ============================================
COMPANY_MATCH_SYSTEM_PROMPT = """Sen bir firma adi eslestirme uzmanisin.

GOREV: Iki firma adinin AYNI sirketi temsil edip etmedigini belirle.

ESLESTIRME KURALLARI:
- A.S. = Anonim Sirket = A.Ş. = AYNI
- LTD = Limited = Ltd. Sti. = LTD. STI. = AYNI
- Kucuk harfler, buyuk harfler = AYNI
- Tire, bosluk, nokta farklari = ONEMSIZ
- Kisaltmalar (INC, CORP, GIDA, INS, INSAAT) = KABUL ET
- Farkli sehir/sube = FARKLI sirket (ornegin ANKARA SUBE ≠ ISTANBUL SUBE)
- Tamamen farkli isimler = FARKLI

ONEMLI:
- "NEV BAHAR GIDA" ve "NEV BAHAR TOPTAN GIDA" = AYNI (ek kelimeler onemsiz)
- "ABC INSAAT" ve "ABC INSAAT TAAHHUT" = AYNI
- "XYZ HOLDING" ve "XYZ GIDA" = FARKLI (farkli sektorler)

CIKTI KURALI:
- SADECE "EVET" veya "HAYIR" yaz
- Baska bir sey yazma!
- Aciklama yapma!"""


class IhaleCompanyMatcher:
    """
    Ihale yasakli firma eslestirme - Halusnasyon korumali!

    TSG'den alinan firma bilgileriyle (Vergi No, Firma Adi)
    Resmi Gazete'deki yasakli firmayi eslestirir.
    """

    def __init__(self):
        self.llm = LLMClient()

    async def match_company(
        self,
        tsg_company: Dict[str, Any],
        yasakli_company: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        TSG'den gelen firma ile PDF'den cikan firmayi karsilastir.

        Args:
            tsg_company: TSG'den gelen firma bilgileri
                - firma_adi: str
                - vergi_no: str (opsiyonel)
                - mersis_no: str (opsiyonel)
            yasakli_company: PDF'den cikan yasakli firma bilgileri
                - adi: str
                - vergi_no: str (opsiyonel)
                - tc_kimlik: str (opsiyonel)

        Returns:
            Dict: Eslestirme sonucu
                - eslesme: bool
                - yontem: str (vergi_no, firma_adi_basit, firma_adi_llm)
                - guven: float (0.0 - 1.0)
                - aciklama: str
        """
        step("FIRMA ESLESTIRME")

        result = {
            "eslesme": False,
            "yontem": None,
            "guven": 0.0,
            "aciklama": None
        }

        tsg_firma = tsg_company.get("firma_adi", "")
        tsg_vergi = tsg_company.get("vergi_no", "")

        yasakli_firma = yasakli_company.get("adi", "")
        yasakli_vergi = yasakli_company.get("vergi_no", "")

        log(f"TSG Firma: {tsg_firma}")
        log(f"Yasakli Firma: {yasakli_firma}")

        # 1. Vergi No eslesmesi (en guvenilir)
        if tsg_vergi and yasakli_vergi:
            tsg_vergi_clean = self._clean_vergi_no(tsg_vergi)
            yasakli_vergi_clean = self._clean_vergi_no(yasakli_vergi)

            if tsg_vergi_clean == yasakli_vergi_clean:
                success("Vergi No eslesti!")
                return {
                    "eslesme": True,
                    "yontem": "vergi_no",
                    "guven": 1.0,
                    "aciklama": f"Vergi No eslesti: {tsg_vergi_clean}"
                }

        # 2. Basit firma adi eslesmesi
        if self._simple_match(tsg_firma, yasakli_firma):
            success("Basit firma adi eslesti!")
            return {
                "eslesme": True,
                "yontem": "firma_adi_basit",
                "guven": 0.85,
                "aciklama": "Firma adlari benzer"
            }

        # 3. LLM ile firma adi eslesmesi (temperature=0.0)
        if tsg_firma and yasakli_firma:
            llm_match = await self._llm_match(tsg_firma, yasakli_firma)

            if llm_match:
                success("LLM firma adi eslesti!")
                return {
                    "eslesme": True,
                    "yontem": "firma_adi_llm",
                    "guven": 0.75,
                    "aciklama": "LLM analizi: Ayni firma"
                }

        # Eslesmedi
        warn("Firma eslesmedi")
        return {
            "eslesme": False,
            "yontem": "none",
            "guven": 0.0,
            "aciklama": "Firma bilgileri uyusmuyor"
        }

    async def find_matching_yasaklama(
        self,
        tsg_company: Dict[str, Any],
        yasaklama_listesi: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        TSG firmasini yasaklama listesinde ara.

        Args:
            tsg_company: TSG'den gelen firma
            yasaklama_listesi: PDF'lerden cikan yasaklama kararlari listesi

        Returns:
            Dict: Eslesen yasaklama karari veya None
        """
        step(f"YASAKLAMA ARAMA: {tsg_company.get('firma_adi')}")
        log(f"Aranacak liste boyutu: {len(yasaklama_listesi)}")

        for yasaklama in yasaklama_listesi:
            yasakli_kisi = yasaklama.get("yapisal_veri", {}).get("yasakli_kisi", {})

            if not yasakli_kisi:
                continue

            match_result = await self.match_company(tsg_company, yasakli_kisi)

            if match_result["eslesme"]:
                success(f"Eslesen yasaklama bulundu! Yontem: {match_result['yontem']}")
                return {
                    **yasaklama,
                    "eslestirme": match_result
                }

        log("Eslesen yasaklama bulunamadi")
        return None

    async def _llm_match(self, firma1: str, firma2: str) -> bool:
        """
        LLM ile iki firma adinin ayni sirket olup olmadigini kontrol et.

        KRITIK: temperature=0.0 ile halusnasyon engelleniyor!

        Args:
            firma1: Birinci firma adi
            firma2: Ikinci firma adi

        Returns:
            bool: Ayni sirket ise True
        """
        log(f"LLM eslestirme: '{firma1}' vs '{firma2}'")

        try:
            user_prompt = f"Aranan: {firma1}\nBulunan: {firma2}"

            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": COMPANY_MATCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-oss-120b",
                temperature=0.0,  # SIFIR halusnasyon!
                max_tokens=10     # Sadece EVET/HAYIR
            )

            answer = response.strip().upper()
            log(f"LLM yaniti: {answer}")

            return "EVET" in answer

        except Exception as e:
            error(f"LLM eslestirme hatasi: {e}")
            # Hata durumunda basit eslestirmeye geri don
            return self._simple_match(firma1, firma2)

    def _clean_vergi_no(self, vergi_no: str) -> str:
        """Vergi numarasini temizle (sadece rakamlar)."""
        if not vergi_no:
            return ""
        return ''.join(c for c in str(vergi_no) if c.isdigit())

    def _normalize_company_name(self, name: str) -> str:
        """
        Firma adini normalize et (karsilastirma icin).

        - Buyuk harfe cevir
        - Turkce karakterleri duzelt
        - Gereksiz bosluklari sil
        - Yasal ekleri kaldir (A.S., LTD. vb)
        """
        if not name:
            return ""

        # Buyuk harf
        result = name.upper().strip()

        # Turkce karakter donusumleri
        replacements = {
            "İ": "I",
            "Ş": "S",
            "Ğ": "G",
            "Ü": "U",
            "Ö": "O",
            "Ç": "C",
            "ı": "I",
            "ş": "S",
            "ğ": "G",
            "ü": "U",
            "ö": "O",
            "ç": "C",
        }

        for tr_char, en_char in replacements.items():
            result = result.replace(tr_char, en_char)

        # Yasal ek/son ekleri kaldir
        suffixes = [
            " A.S.", " AS", " A.Ş.", " AŞ",
            " LTD.", " LTD", " LTD.STI.", " LTD STI",
            " LIMITED", " ANONIM SIRKETI", " ANONIM",
            " SIRKETI", " SIRKET", " INC", " CORP",
            " SAN.", " TIC.", " SANAYI", " TICARET",
            " VE", " TAAHHUT", " INSAAT", " GIDA",
        ]

        for suffix in suffixes:
            result = result.replace(suffix, "")

        # Coklu bosluklari tek bosluga indir
        result = ' '.join(result.split())

        return result.strip()

    def _simple_match(self, name1: str, name2: str) -> bool:
        """
        Multi-strategy firma adi eslestirmesi (LLM kullanmadan).

        Strategies:
        1. Exact normalized match -> True
        2. Contains match -> True
        3. Levenshtein ratio >= 70% -> True
        4. Jaccard similarity >= 40% -> True (eskisi %60)
        """
        if not name1 or not name2:
            return False

        # Normalize et
        n1 = self._normalize_company_name(name1)
        n2 = self._normalize_company_name(name2)

        # Strategy 1: Tam eslestirme
        if n1 == n2:
            return True

        # Strategy 2: Biri digerini icerir
        if n1 in n2 or n2 in n1:
            return True

        # Strategy 3: Levenshtein distance
        levenshtein_ratio = self._levenshtein_ratio(n1, n2)
        if levenshtein_ratio >= 0.7:  # %70 benzer
            return True

        # Strategy 4: Jaccard benzerlik (kelime kesisimi) - DÜŞÜRÜLMÜŞ THRESHOLD
        words1 = set(n1.split())
        words2 = set(n2.split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        similarity = len(intersection) / len(union)

        return similarity >= 0.4  # %40 benzerlik esigi (eskisi %60)

    def _levenshtein_ratio(self, s1: str, s2: str) -> float:
        """
        İki string arasındaki Levenshtein benzerlik oranı.

        Returns: 0.0 - 1.0 arası benzerlik oranı
        """
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)

        if max_len == 0:
            return 1.0

        # Levenshtein distance hesapla
        distance = self._levenshtein_distance(s1, s2)

        # Benzerlik oranı = 1 - (distance / max_len)
        return 1.0 - (distance / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        İki string arasındaki Levenshtein (edit) mesafesi.

        Dinamik programlama ile O(m*n) karmaşıklıkta hesaplar.
        """
        len1, len2 = len(s1), len(s2)

        # Matris oluştur
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # Base case
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        # Fill matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # silme
                        dp[i][j - 1],      # ekleme
                        dp[i - 1][j - 1]   # değiştirme
                    )

        return dp[len1][len2]


# Test
async def test_company_matcher():
    """Company Matcher test fonksiyonu."""
    print("\n" + "="*60)
    print("Ihale Company Matcher Test")
    print("="*60)

    matcher = IhaleCompanyMatcher()

    # Test 1: Vergi No eslesmesi
    print("\n1. Vergi No Eslesmesi:")
    result = await matcher.match_company(
        {"firma_adi": "ABC INSAAT A.S.", "vergi_no": "1234567890"},
        {"adi": "ABC INSAAT ANONIM SIRKETI", "vergi_no": "1234567890"}
    )
    print(f"   Eslesme: {result['eslesme']}, Yontem: {result['yontem']}, Guven: {result['guven']}")

    # Test 2: Basit firma adi eslesmesi
    print("\n2. Basit Firma Adi Eslesmesi:")
    result = await matcher.match_company(
        {"firma_adi": "NEV BAHAR GIDA LTD."},
        {"adi": "NEV BAHAR TOPTAN GIDA LIMITED SIRKETI"}
    )
    print(f"   Eslesme: {result['eslesme']}, Yontem: {result['yontem']}, Guven: {result['guven']}")

    # Test 3: Farkli firmalar
    print("\n3. Farkli Firmalar:")
    result = await matcher.match_company(
        {"firma_adi": "XYZ HOLDING A.S."},
        {"adi": "ABC GIDA SANAYI LTD."}
    )
    print(f"   Eslesme: {result['eslesme']}, Yontem: {result['yontem']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_company_matcher())
