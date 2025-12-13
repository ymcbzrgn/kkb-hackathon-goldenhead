"""
Report Generator Service
Agent verilerini birleştirip yapılandırılmış istihbarat raporu üreten servis.
LLM kullanılmaz - Rule-based + Şablon yaklaşımı.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional


class ReportGenerator:
    """
    İstihbarat Raporu Üretici.

    Agent verilerini alır, rule-based risk skoru hesaplar,
    yapılandırılmış rapor formatında çıktı üretir.
    """

    def calculate_risk_score(
        self,
        tsg_data: Optional[Dict],
        ihale_data: Optional[Dict],
        news_data: Optional[Dict]
    ) -> int:
        """
        Rule-based risk skoru hesapla.

        Başlangıç: 50 (nötr)
        Düşük = 0-30, Orta = 31-55, Yüksek = 56-75, Kritik = 76-100

        Args:
            tsg_data: TSG Agent verisi
            ihale_data: İhale Agent verisi
            news_data: News Agent verisi

        Returns:
            int: Risk skoru (0-100)
        """
        score = 50  # Başlangıç noktası

        # ═══════════════════════════════════════
        # TSG FAKTÖRLERİ (±15 puan)
        # ═══════════════════════════════════════
        if tsg_data:
            veri = tsg_data.get("tsg_sonuc", {}).get("yapilandirilmis_veri", {})

            # Eksik kritik alan kontrolü
            kritik_alanlar = ["Firma Unvani", "Sermaye", "Mersis Numarasi"]
            eksik = sum(1 for alan in kritik_alanlar if not veri.get(alan))
            score += eksik * 5  # Her eksik kritik alan +5

            # Yönetici bilgisi
            if not veri.get("Yoneticiler"):
                score += 5  # Yönetici bilgisi yok
        else:
            score += 15  # TSG verisi hiç yok = ciddi risk

        # ═══════════════════════════════════════
        # İHALE FAKTÖRLERİ (±35 puan) - EN KRİTİK!
        # ═══════════════════════════════════════
        if ihale_data:
            # ONEMLI: yasak_durumu veya yasakli_mi = aktif yasak var mi
            # eslesen_karar = BU FIRMAYA AIT yasaklama sayisi
            # bulunan_toplam_yasaklama / toplam_karar = Resmi Gazete'deki GENEL yasaklama (firmaya ait DEGIL!)
            aktif_yasak = ihale_data.get("yasak_durumu", ihale_data.get("yasakli_mi", False))
            firmaya_ait_yasak = ihale_data.get("eslesen_karar", 0)

            if aktif_yasak:
                score += 35  # AKTİF YASAK = BÜYÜK RİSK!
            elif firmaya_ait_yasak > 0:
                score += 15  # Bu firmaya ait geçmiş yasak var
            else:
                score -= 10  # Temiz sicil = bonus

        # ═══════════════════════════════════════
        # HABER FAKTÖRLERİ (±20 puan)
        # ═══════════════════════════════════════
        if news_data:
            ozet = news_data.get("ozet", {})

            # Sentiment skoru (-1.0 to +1.0)
            sentiment = ozet.get("sentiment_score", 0)
            score -= int(sentiment * 15)  # Olumlu: -15, Olumsuz: +15

            # Trend
            trend = ozet.get("trend", "notr")
            if trend == "negatif":
                score += 10
            elif trend == "pozitif":
                score -= 5

            # Haber sayısı (az haber = belirsizlik)
            toplam = ozet.get("toplam", 0)
            if toplam < 3:
                score += 5  # Az haber = belirsizlik riski

        # Sınırla (0-100)
        return max(0, min(100, score))

    def determine_decision(
        self,
        risk_score: int,
        ihale_data: Optional[Dict]
    ) -> Dict[str, str]:
        """
        Risk skoruna göre karar önerisi belirle.

        Args:
            risk_score: Hesaplanmış risk skoru (0-100)
            ihale_data: İhale verisi (yasak kontrolü için)

        Returns:
            dict: karar, risk_seviyesi, aciklama
        """
        # Aktif yasak varsa direkt RED
        if ihale_data and ihale_data.get("yasak_durumu"):
            return {
                "karar": "RED",
                "risk_seviyesi": "kritik",
                "aciklama": "Firma aktif ihale yasagi altinda."
            }

        if risk_score <= 30:
            return {
                "karar": "ONAY",
                "risk_seviyesi": "dusuk",
                "aciklama": "Dusuk riskli firma, islem onaylanabilir."
            }
        elif risk_score <= 55:
            return {
                "karar": "SARTLI_ONAY",
                "risk_seviyesi": "orta",
                "aciklama": "Orta riskli firma, ek teminat veya sartlar degerlendirilmeli."
            }
        elif risk_score <= 75:
            return {
                "karar": "INCELEME",
                "risk_seviyesi": "yuksek",
                "aciklama": "Yuksek riskli firma, detayli inceleme gerekli."
            }
        else:
            return {
                "karar": "RED",
                "risk_seviyesi": "kritik",
                "aciklama": "Kritik risk seviyesi, islem onerilmez."
            }

    def _calculate_risk_factors(
        self,
        tsg_data: Optional[Dict],
        ihale_data: Optional[Dict],
        news_data: Optional[Dict]
    ) -> List[Dict[str, str]]:
        """
        Risk faktörlerini listele.

        Args:
            tsg_data: TSG verisi
            ihale_data: İhale verisi
            news_data: Haber verisi

        Returns:
            list: Risk faktörleri listesi
        """
        factors = []

        # TSG faktörleri
        if not tsg_data:
            factors.append({"tip": "uyari", "mesaj": "TSG verisi bulunamadi"})
        else:
            veri = tsg_data.get("tsg_sonuc", {}).get("yapilandirilmis_veri", {})
            if not veri.get("Sermaye"):
                factors.append({"tip": "uyari", "mesaj": "Sermaye bilgisi eksik"})
            if not veri.get("Yoneticiler"):
                factors.append({"tip": "uyari", "mesaj": "Yonetici bilgisi eksik"})

        # İhale faktörleri
        # ONEMLI: eslesen_karar = BU FIRMAYA AIT yasaklama sayisi
        # bulunan_toplam_yasaklama = Resmi Gazete'deki GENEL yasaklama (firmaya ait DEGIL!)
        if ihale_data:
            aktif_yasak = ihale_data.get("yasak_durumu", ihale_data.get("yasakli_mi", False))
            firmaya_ait_yasak = ihale_data.get("eslesen_karar", 0)

            if aktif_yasak:
                yasaklayan = ihale_data.get("yasaklayan_kurum", "Bilinmiyor")
                factors.append({
                    "tip": "kritik",
                    "mesaj": f"AKTIF IHALE YASAGI - {yasaklayan}"
                })
            elif firmaya_ait_yasak > 0:
                factors.append({
                    "tip": "uyari",
                    "mesaj": f"Bu firmaya ait gecmiste {firmaya_ait_yasak} yasaklama kaydi"
                })

        # Haber faktörleri
        if news_data:
            sentiment = news_data.get("ozet", {}).get("sentiment_score", 0)
            if sentiment < -0.3:
                factors.append({
                    "tip": "uyari",
                    "mesaj": f"Olumsuz medya algisi (skor: {sentiment:.2f})"
                })
            elif sentiment > 0.3:
                factors.append({
                    "tip": "olumlu",
                    "mesaj": f"Olumlu medya algisi (skor: {sentiment:.2f})"
                })

            if news_data.get("ozet", {}).get("trend") == "negatif":
                factors.append({
                    "tip": "uyari",
                    "mesaj": "Son donem haberleri olumsuz trend gosteriyor"
                })

        return factors

    def generate(
        self,
        company_name: str,
        tsg_data: Optional[Dict],
        ihale_data: Optional[Dict],
        news_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Yapılandırılmış istihbarat raporu üret.

        Args:
            company_name: Firma adı
            tsg_data: TSG Agent verisi
            ihale_data: İhale Agent verisi
            news_data: News Agent verisi

        Returns:
            dict: Yapılandırılmış istihbarat raporu
        """
        # Risk skoru hesapla
        risk_score = self.calculate_risk_score(tsg_data, ihale_data, news_data)

        # Karar belirle
        decision = self.determine_decision(risk_score, ihale_data)

        # Risk faktörlerini hesapla
        risk_factors = self._calculate_risk_factors(tsg_data, ihale_data, news_data)

        # Rapor oluştur
        report = {
            "rapor_meta": {
                "firma_adi": company_name,
                "olusturma_tarihi": datetime.utcnow().isoformat(),
                "rapor_versiyonu": "1.0"
            },

            "risk_ozeti": {
                "risk_skoru": risk_score,
                "risk_seviyesi": decision["risk_seviyesi"],
                "karar_onerisi": decision["karar"],
                "karar_aciklamasi": decision["aciklama"]
            },

            "firma_bilgileri": self._extract_firma_bilgileri(tsg_data),

            "ihale_durumu": self._extract_ihale_durumu(ihale_data),

            "medya_analizi": self._extract_medya_analizi(news_data),

            "risk_faktorleri": risk_factors
        }

        return report

    def _extract_firma_bilgileri(self, tsg_data: Optional[Dict]) -> Optional[Dict]:
        """TSG verisinden firma bilgilerini çıkar."""
        if not tsg_data:
            return None

        veri = tsg_data.get("tsg_sonuc", {}).get("yapilandirilmis_veri", {})

        return {
            "unvan": veri.get("Firma Unvani"),
            "mersis_no": veri.get("Mersis Numarasi"),
            "sermaye": veri.get("Sermaye"),
            "kurulus_tarihi": veri.get("Kurulus_Tarihi"),
            "faaliyet_alani": veri.get("Faaliyet_Konusu"),
            "yoneticiler": veri.get("Yoneticiler", []),
            "veri_kaynagi": "Turkiye Ticaret Sicili Gazetesi"
        }

    def _extract_ihale_durumu(self, ihale_data: Optional[Dict]) -> Optional[Dict]:
        """İhale verisinden ihale durumunu çıkar."""
        if not ihale_data:
            return None

        # ONEMLI: eslesen_karar = BU FIRMAYA AIT yasaklama sayisi
        # bulunan_toplam_yasaklama = Resmi Gazete'deki GENEL yasaklama (firmaya ait DEGIL!)
        return {
            "yasak_var_mi": ihale_data.get("yasak_durumu", ihale_data.get("yasakli_mi", False)),
            "firmaya_ait_yasak_sayisi": ihale_data.get("eslesen_karar", 0),
            "taranan_toplam_karar": ihale_data.get("bulunan_toplam_yasaklama", ihale_data.get("toplam_karar", 0)),
            "risk_degerlendirmesi": ihale_data.get("risk_degerlendirmesi", "bilinmiyor"),
            "yasaklayan_kurum": ihale_data.get("yasaklayan_kurum"),
            "yasak_suresi": ihale_data.get("yasak_suresi"),
            "resmi_gazete": ihale_data.get("resmi_gazete"),
            "veri_kaynagi": "Resmi Gazete"
        }

    def _extract_medya_analizi(self, news_data: Optional[Dict]) -> Optional[Dict]:
        """Haber verisinden medya analizini çıkar."""
        if not news_data:
            return None

        ozet = news_data.get("ozet", {})
        haberler = news_data.get("haberler", [])

        return {
            "toplam_haber": ozet.get("toplam", 0),
            "olumlu_haber": ozet.get("olumlu", 0),
            "olumsuz_haber": ozet.get("olumsuz", 0),
            "sentiment_skoru": ozet.get("sentiment_score", 0),
            "trend": ozet.get("trend", "notr"),
            "kaynak_sayisi": len(news_data.get("kaynak_dagilimi", {})),
            "son_haberler": [
                {
                    "baslik": h.get("baslik"),
                    "kaynak": h.get("kaynak"),
                    "sentiment": h.get("sentiment"),
                    "tarih": h.get("tarih"),
                    "screenshot_path": h.get("screenshot_path")
                }
                for h in haberler[:5]
            ],
            "veri_kaynagi": "10 Guvenilir Haber Kaynagi"
        }
