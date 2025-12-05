"""
News Agent - Haber Toplama ve Sentiment Analizi
Firma hakkındaki haberleri toplar ve analiz eder
"""
import asyncio
from typing import Optional, List, Dict
from app.agents.base_agent import BaseAgent, AgentResult
from app.llm.client import LLMClient


class NewsAgent(BaseAgent):
    """
    Haber Agent'ı.

    Görevleri:
    - Haber sitelerinde firma ara
    - Son 12 ayın haberlerini topla
    - Her haber için sentiment analizi yap
    - Trend analizi yap
    """

    def __init__(self):
        super().__init__(
            agent_id="news_agent",
            agent_name="Haber Agent",
            agent_description="Haber toplama ve sentiment analizi"
        )
        self.llm = LLMClient()

    async def run(self, company_name: str) -> AgentResult:
        """Haberleri topla ve analiz et"""

        self.report_progress(10, "Haberler aranıyor...")

        try:
            # 1. Haber ara
            news_items = await self._search_news(company_name)
            self.report_progress(40, f"{len(news_items)} haber bulundu")

            if not news_items:
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data={"message": "Haber bulunamadı", "toplam_haber": 0},
                    summary="Firma hakkında güncel haber bulunamadı",
                    key_findings=["Medya görünürlüğü düşük"],
                    warning_flags=[]
                )

            # 2. Sentiment analizi
            self.report_progress(60, "Sentiment analizi yapılıyor...")
            analyzed_news = await self._analyze_sentiment(news_items)

            # 3. Sonuçları derle
            self.report_progress(90, "Veriler derleniyor...")
            result_data = self._compile_results(analyzed_news)
            self.report_progress(100, "Haber analizi tamamlandı")

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                data=result_data,
                summary=self._generate_summary(result_data),
                key_findings=self._extract_key_findings(result_data),
                warning_flags=self._extract_warnings(result_data)
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )

    async def _search_news(self, company_name: str) -> List[Dict]:
        """Haber ara"""
        # TODO: Gerçek haber scraping implementasyonu

        await asyncio.sleep(1)  # Simüle gecikme

        # Mock news data
        return [
            {
                "baslik": f"{company_name} 50 kişilik istihdam sağlayacak",
                "kaynak": "ekonomi.com",
                "tarih": "2024-10-15",
                "url": "https://example.com/1"
            },
            {
                "baslik": f"{company_name} yeni yatırım aldı",
                "kaynak": "teknoloji.com",
                "tarih": "2024-09-20",
                "url": "https://example.com/2"
            },
            {
                "baslik": f"{company_name} genel müdürü istifa etti",
                "kaynak": "finans.com",
                "tarih": "2024-08-10",
                "url": "https://example.com/3"
            },
            {
                "baslik": f"{company_name} vergi yapılandırması yaptı",
                "kaynak": "ekonomi.com",
                "tarih": "2023-09-20",
                "url": "https://example.com/4"
            }
        ]

    async def _analyze_sentiment(self, news_items: List[Dict]) -> List[Dict]:
        """Sentiment analizi yap"""
        # TODO: LLM ile gerçek sentiment analizi

        analyzed = []
        for i, item in enumerate(news_items):
            await asyncio.sleep(0.2)  # Simüle gecikme

            # Mock sentiment (basit keyword matching)
            baslik_lower = item["baslik"].lower()
            if any(word in baslik_lower for word in ["istihdam", "yatırım", "büyüme", "başarı"]):
                sentiment = "pozitif"
            elif any(word in baslik_lower for word in ["istifa", "zarar", "kriz", "yapılandırma"]):
                sentiment = "negatif"
            else:
                sentiment = "notr"

            analyzed.append({
                **item,
                "sentiment": sentiment
            })

            self.report_progress(
                60 + int((i + 1) / len(news_items) * 30),
                f"{i + 1}/{len(news_items)} haber analiz edildi"
            )

        return analyzed

    def _compile_results(self, analyzed_news: List[Dict]) -> Dict:
        """Sonuçları derle"""
        total = len(analyzed_news)
        pozitif = sum(1 for n in analyzed_news if n["sentiment"] == "pozitif")
        negatif = sum(1 for n in analyzed_news if n["sentiment"] == "negatif")
        notr = total - pozitif - negatif

        sentiment_score = (pozitif - negatif) / total if total > 0 else 0

        # Trend analizi (basit)
        recent_news = analyzed_news[:5]  # Son 5 haber
        recent_pozitif = sum(1 for n in recent_news if n["sentiment"] == "pozitif")
        recent_negatif = sum(1 for n in recent_news if n["sentiment"] == "negatif")

        if recent_pozitif > recent_negatif:
            trend = "yukari"
        elif recent_negatif > recent_pozitif:
            trend = "asagi"
        else:
            trend = "stabil"

        return {
            "toplam_haber": total,
            "pozitif": pozitif,
            "negatif": negatif,
            "notr": notr,
            "sentiment_score": round(sentiment_score, 2),
            "trend": trend,
            "onemli_haberler": analyzed_news[:5]  # En son 5 haber
        }

    def _generate_summary(self, data: Dict) -> str:
        """Özet oluştur"""
        total = data["toplam_haber"]
        pozitif_oran = (data["pozitif"] / total * 100) if total > 0 else 0
        trend_str = {"yukari": "yukarı yönlü", "asagi": "aşağı yönlü", "stabil": "stabil"}.get(data["trend"], "belirsiz")

        return f"{total} haber analiz edildi. %{pozitif_oran:.0f} pozitif. Medya trendi {trend_str}."

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Önemli bulguları çıkar"""
        findings = []

        if data["sentiment_score"] > 0.3:
            findings.append("Medya algısı olumlu")
        elif data["sentiment_score"] < -0.3:
            findings.append("Medya algısı olumsuz")

        if data["trend"] == "yukari":
            findings.append("Son dönem haberleri olumlu")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarıları çıkar"""
        warnings = []

        if data["negatif"] > data["pozitif"]:
            warnings.append("Negatif haberler baskın")

        if data["trend"] == "asagi":
            warnings.append("Olumsuz medya trendi")

        return warnings
