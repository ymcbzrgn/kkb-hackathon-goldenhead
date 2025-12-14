"""
News Agent K8s Adapter - Kubernetes News Orchestrator'ı çağırır.

Bu adapter mevcut sisteme entegre olur ve K8s'deki news-orchestrator
service'ini HTTP ile çağırır.

Toggle: USE_K8S_NEWS_AGENT=true environment variable ile aktif edilir.

Avantajlar:
- 10 kaynak paralel (10 pod)
- ~1 dakika toplam süre (mevcut ~27-30dk yerine)
- Rollback: USE_K8S_NEWS_AGENT=false ile mevcut sisteme dönüş
"""
import asyncio
import os
from typing import Optional, List, Dict
import httpx

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.progress_simulator import ProgressSimulator, SimulatorConfig


# K8s News Orchestrator URL
# BUG FIX: Default 8080 -> 8082 (port-forward local development için)
NEWS_ORCHESTRATOR_URL = os.getenv(
    "NEWS_ORCHESTRATOR_URL",
    "http://localhost:8082"  # K8s içinde: http://news-orchestrator.news-agent:8080
)

# Timeout (saniye) - 10 dakika hard limit (TSG/İhale ile aynı)
K8S_TIMEOUT = int(os.getenv("K8S_NEWS_TIMEOUT", "600"))


class NewsAgentK8s(BaseAgent):
    """
    Kubernetes News Agent Adapter.

    K8s'deki news-orchestrator service'ini çağırarak
    10 kaynaktan paralel haber toplar.
    """

    def __init__(self):
        super().__init__(
            agent_id="news_agent",
            agent_name="Haber Agent (K8s)",
            agent_description="10 kaynaktan paralel haber toplama (Kubernetes)"
        )
        self.report_id: Optional[str] = None

    def set_report_id(self, report_id: str):
        """Report ID'yi set et (progress tracking için)."""
        self.report_id = report_id

    async def run(self, company_name: str, alternative_names: List[str] = None) -> AgentResult:
        """
        K8s News Orchestrator'ı çağır.

        Args:
            company_name: Firma adı
            alternative_names: Alternatif firma isimleri (TSG'den gelen resmi ünvan vb.)

        Returns:
            AgentResult: Mevcut news_agent.py ile uyumlu format
        """
        # Tüm isimleri birleştir
        all_names = [company_name]
        if alternative_names:
            all_names.extend(alternative_names)

        self.report_progress(5, f"K8s News Orchestrator'a baglaniliyor... ({len(all_names)} isim)")

        try:
            # Progress simulator - K8s beklerken gercekci ilerleme goster
            simulator = ProgressSimulator(
                progress_callback=self.report_progress,
                config=SimulatorConfig(
                    start_progress=10,
                    max_progress=85,
                    initial_speed=3.0,
                    decay_rate=0.92,
                    tick_interval=2.0
                ),
                messages=[
                    "10 kaynak paralel taraniyor...",
                    "Haberler toplanıyor...",
                    "Sentiment analizi yapiliyor...",
                    "Sonuclar birlestiriliyor...",
                    "Dogrulama yapiliyor...",
                ]
            )

            async with httpx.AsyncClient(timeout=K8S_TIMEOUT) as client:
                # Simulasyonu arka planda baslat
                sim_task = asyncio.create_task(simulator.start())

                try:
                    # K8s News Orchestrator'ı çağır
                    # Quick Mode: 5 haber/kaynak (hackathon için optimize)
                    response = await client.post(
                        f"{NEWS_ORCHESTRATOR_URL}/api/news/search",
                        json={
                            "company_name": company_name,
                            "alternative_names": alternative_names or [],  # TSG'den gelen alternatif isimler
                            "max_articles_per_source": 5,  # 3 → 5 (Quick Mode)
                            "timeout_seconds": 60,
                            "report_id": self.report_id
                        }
                    )
                finally:
                    # HTTP tamamlaninca simulasyonu durdur
                    simulator.stop()
                    await sim_task

                if response.status_code != 200:
                    raise Exception(f"Orchestrator HTTP {response.status_code}: {response.text[:200]}")

                result = response.json()

                self.report_progress(90, f"{result['total_articles']} haber toplandi")

                # Sonuçları mevcut format'a dönüştür
                articles = result.get("articles", [])
                analysis = result.get("analysis", {})

                # HACKATHON formatına dönüştür
                haberler = []
                for article in articles:
                    haberler.append({
                        "id": article.get("id", ""),
                        "baslik": article.get("title", ""),
                        "kaynak": article.get("source", ""),
                        "tarih": article.get("date", "Tarih bilinmiyor"),
                        "url": article.get("url", ""),
                        "metin": article.get("text", "")[:2000] if article.get("text") else "",
                        "sentiment": article.get("sentiment", "olumsuz"),
                        "screenshot_path": article.get("screenshot_path"),
                        "relevance_confidence": article.get("relevance_score", 0.5)
                    })

                # Özet hesapla
                total = len(haberler)
                olumlu = sum(1 for h in haberler if h.get("sentiment") == "olumlu")
                olumsuz = total - olumlu

                sentiment_score = (olumlu - olumsuz) / total if total > 0 else 0

                # Trend analizi
                recent = haberler[:5]
                recent_olumlu = sum(1 for h in recent if h.get("sentiment") == "olumlu")
                recent_olumsuz = len(recent) - recent_olumlu

                if recent_olumlu > recent_olumsuz:
                    trend = "pozitif"
                elif recent_olumsuz > recent_olumlu:
                    trend = "negatif"
                else:
                    trend = "notr"

                # Kaynak dağılımı
                kaynak_dagilimi = {}
                for h in haberler:
                    kaynak = h.get("kaynak", "Unknown")
                    if kaynak not in kaynak_dagilimi:
                        kaynak_dagilimi[kaynak] = {"total": 0, "olumlu": 0, "olumsuz": 0}
                    kaynak_dagilimi[kaynak]["total"] += 1
                    kaynak_dagilimi[kaynak][h.get("sentiment", "olumsuz")] += 1

                # Result data
                result_data = {
                    "haberler": haberler,
                    "ozet": {
                        "toplam": total,
                        "olumlu": olumlu,
                        "olumsuz": olumsuz,
                        "sentiment_score": round(sentiment_score, 2),
                        "trend": trend
                    },
                    "toplam_haber": total,
                    "kaynak_dagilimi": kaynak_dagilimi,
                    # K8s metrics
                    "k8s_metrics": {
                        "sources_completed": result.get("sources_completed", 0),
                        "sources_failed": result.get("sources_failed", 0),
                        "duration_seconds": result.get("duration_seconds", 0)
                    }
                }

                self.report_progress(100, "Haber analizi tamamlandı")

                # Summary oluştur
                summary = self._generate_summary(result_data)
                key_findings = self._extract_key_findings(result_data)
                warnings = self._extract_warnings(result_data)

                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    data=result_data,
                    summary=summary,
                    key_findings=key_findings,
                    warning_flags=warnings
                )

        except httpx.TimeoutException:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=f"K8s News Orchestrator timeout ({K8S_TIMEOUT}s)"
            )
        except httpx.ConnectError as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=f"K8s News Orchestrator bağlantı hatası: {e}"
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )

    def _generate_summary(self, data: Dict) -> str:
        """Özet oluştur."""
        total = data.get("toplam_haber", 0)
        if total == 0:
            return "Firma hakkında haber bulunamadı."

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
        k8s = data.get("k8s_metrics", {})
        duration = k8s.get("duration_seconds", 0)

        return (
            f"{total} haber ({kaynak_sayisi} kaynaktan) analiz edildi. "
            f"Olumlu: %{olumlu_oran:.0f}, Olumsuz: %{olumsuz_oran:.0f}. "
            f"Medya trendi {trend_str}. "
            f"(K8s: {duration:.1f}s)"
        )

    def _extract_key_findings(self, data: Dict) -> List[str]:
        """Önemli bulguları çıkar."""
        findings = []

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

        kaynak_sayisi = len(data.get("kaynak_dagilimi", {}))
        if kaynak_sayisi >= 5:
            findings.append(f"Yüksek medya görünürlüğü ({kaynak_sayisi} kaynak)")
        elif kaynak_sayisi >= 3:
            findings.append(f"Orta medya görünürlüğü ({kaynak_sayisi} kaynak)")
        elif kaynak_sayisi >= 1:
            findings.append(f"Düşük medya görünürlüğü ({kaynak_sayisi} kaynak)")

        # K8s metrics
        k8s = data.get("k8s_metrics", {})
        if k8s.get("sources_failed", 0) > 3:
            findings.append(f"K8s: {k8s['sources_failed']}/10 kaynak başarısız")

        return findings

    def _extract_warnings(self, data: Dict) -> List[str]:
        """Uyarıları çıkar."""
        warnings = []

        ozet = data.get("ozet", {})
        olumlu = ozet.get("olumlu", 0)
        olumsuz = ozet.get("olumsuz", 0)
        trend = ozet.get("trend", "notr")
        total = data.get("toplam_haber", 0)

        if olumsuz > olumlu:
            warnings.append("Olumsuz haberler baskın")

        if trend == "negatif":
            warnings.append("Olumsuz medya trendi")

        if total > 0 and (olumsuz / total) > 0.5:
            warnings.append("Çoğunluk olumsuz haberler")

        # K8s warnings
        k8s = data.get("k8s_metrics", {})
        if k8s.get("sources_failed", 0) > 5:
            warnings.append(f"K8s: Çoğu kaynak başarısız ({k8s['sources_failed']}/10)")

        return warnings


# Test
if __name__ == "__main__":
    async def test():
        agent = NewsAgentK8s()

        def progress_callback(progress_info):
            print(f"[{progress_info.progress:3d}%] {progress_info.message}")

        agent.set_progress_callback(progress_callback)

        print("\n" + "="*60)
        print("NEWS AGENT K8S TEST")
        print("="*60 + "\n")

        result = await agent.run("ASELSAN")

        print("\n" + "="*60)
        print("SONUÇ")
        print("="*60)
        print(f"Status: {result.status}")
        print(f"Summary: {result.summary}")
        print(f"Key Findings: {result.key_findings}")
        print(f"Warnings: {result.warning_flags}")

        if result.data:
            k8s = result.data.get("k8s_metrics", {})
            print(f"\nK8s Metrics:")
            print(f"  Duration: {k8s.get('duration_seconds', 0)}s")
            print(f"  Sources OK: {k8s.get('sources_completed', 0)}/10")
            print(f"  Sources Failed: {k8s.get('sources_failed', 0)}/10")

    asyncio.run(test())
