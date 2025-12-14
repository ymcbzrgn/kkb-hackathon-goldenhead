"""
Council Service
6 kişilik AI kredi komitesi toplantısı
"""
import asyncio
import os
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime

from app.llm.client import LLMClient
from app.council.personas import (
    COUNCIL_MEMBERS,
    MEETING_PHASES,
    get_member,
    get_presentation_order,
    calculate_weighted_score,
)
from app.council.prompts import get_system_prompt


# Demo Mode - 10 dakikalık kısaltılmış pipeline (env'den default alınır, per-request override edilebilir)
DEFAULT_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
print(f"[COUNCIL] Default Demo Mode: {'ENABLED - Kısaltılmış toplantı' if DEFAULT_DEMO_MODE else 'DISABLED - Tam toplantı'}")

# Council speech pacing - insan okuma hizinda streaming
# Not: Bu değerler DEFAULT_DEMO_MODE için, per-request demo_mode için __init__'de ayarlanır
SPEECH_CHUNK_DELAY_MS_DEMO = 15  # Demo mode - 3x yavaş (2 dk toplantı için)
SPEECH_CHUNK_DELAY_MS_NORMAL = 30  # Normal mode
SPEECH_MIN_BUFFER_SIZE_DEMO = 8  # Demo mode - daha sık emit
SPEECH_MIN_BUFFER_SIZE_NORMAL = 6
SPEECH_MAX_BUFFER_TIME_DEMO = 0.04  # Demo mode - daha uzun buffer
SPEECH_MAX_BUFFER_TIME_NORMAL = 0.08


class CouncilService:
    """
    Kredi Komitesi Servisi.

    Görevleri:
    1. Toplantıyı başlat
    2. Her üyenin sunumunu al (LLM ile)
    3. Tartışma turunu yönet
    4. Final kararı oluştur
    5. WebSocket üzerinden streaming yap (Redis Pub/Sub ile)
    """

    def __init__(self, report_id: str = None, demo_mode: Optional[bool] = None):
        self.report_id = report_id
        self.demo_mode = demo_mode if demo_mode is not None else DEFAULT_DEMO_MODE
        self.llm = LLMClient()
        self.members = COUNCIL_MEMBERS
        self.phases = MEETING_PHASES

        # Demo/Normal mode'a göre speech pacing ayarla
        if self.demo_mode:
            self.speech_chunk_delay_ms = SPEECH_CHUNK_DELAY_MS_DEMO
            self.speech_min_buffer_size = SPEECH_MIN_BUFFER_SIZE_DEMO
            self.speech_max_buffer_time = SPEECH_MAX_BUFFER_TIME_DEMO
        else:
            self.speech_chunk_delay_ms = SPEECH_CHUNK_DELAY_MS_NORMAL
            self.speech_min_buffer_size = SPEECH_MIN_BUFFER_SIZE_NORMAL
            self.speech_max_buffer_time = SPEECH_MAX_BUFFER_TIME_NORMAL

        # Speech timeout: demo modda 30s, normal modda 90s per speech
        self.speech_timeout = 30 if self.demo_mode else 90

        print(f"[COUNCIL] Report {report_id}: Demo Mode = {self.demo_mode}, Speech Timeout = {self.speech_timeout}s")

    @staticmethod
    def _sanitize_input(text: str) -> str:
        """
        Prompt injection koruması - kullanıcı girdilerini temizle.
        LLM prompt'larına gönderilecek metinleri sanitize eder.
        """
        if not text:
            return ""

        # Tehlikeli karakterleri ve pattern'leri temizle
        sanitized = text

        # Prompt injection pattern'leri
        dangerous_patterns = [
            "```",           # Kod blokları
            "###",           # Markdown başlıklar (prompt bölümleri gibi görünebilir)
            "SYSTEM:",       # Sistem prompt enjeksiyonu
            "USER:",         # Kullanıcı prompt enjeksiyonu
            "ASSISTANT:",    # Asistan prompt enjeksiyonu
            "Ignore previous",  # Prompt override denemeleri
            "Disregard",
            "Forget everything",
        ]

        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, "")

        # Maksimum uzunluk sınırla (çok uzun girdiler prompt'u bozabilir)
        max_length = 500
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        # Ekstra boşlukları temizle
        sanitized = " ".join(sanitized.split())

        return sanitized.strip()

    async def _stream_speech_with_pacing(self, member_id: str, llm_stream) -> str:
        """
        Konusmayi insan okuma hizinda stream et.
        LLM chunk'larini buffer'layip duzgun araliklarda gonderir.
        Timeout ile koruma altında.
        """
        try:
            return await asyncio.wait_for(
                self._stream_speech_internal(member_id, llm_stream),
                timeout=self.speech_timeout
            )
        except asyncio.TimeoutError:
            print(f"[COUNCIL] Speech timeout ({self.speech_timeout}s) for {member_id}")
            # Async generator'ı düzgün kapat (memory leak önleme)
            try:
                await llm_stream.aclose()
            except Exception as close_err:
                print(f"[COUNCIL] Error closing llm_stream: {close_err}")
            return f"[Konuşma {self.speech_timeout} saniye içinde tamamlanamadı]"

    async def _stream_speech_internal(self, member_id: str, llm_stream) -> str:
        """Internal streaming - timeout wrapper tarafından çağrılır."""
        response_chunks: list[str] = []  # Use list for O(1) append, join at end
        buffer = ""
        last_emit_time = asyncio.get_event_loop().time()

        async for chunk in llm_stream:
            response_chunks.append(chunk)
            buffer += chunk

            now = asyncio.get_event_loop().time()
            elapsed = now - last_emit_time

            # Buffer'i gonder: ya zaman doldu ya da yeterli karakter birikti
            if elapsed >= self.speech_max_buffer_time or len(buffer) >= self.speech_min_buffer_size:
                self._publish_event("council_speech", {
                    "speaker_id": member_id,
                    "chunk": buffer,
                    "is_complete": False
                })
                buffer = ""
                last_emit_time = now
                # Kucuk bir delay ekle - typing efekti icin
                await asyncio.sleep(self.speech_chunk_delay_ms / 1000.0)

        # Kalan buffer'i gonder
        if buffer:
            self._publish_event("council_speech", {
                "speaker_id": member_id,
                "chunk": buffer,
                "is_complete": False
            })

        return "".join(response_chunks)

    def _publish_event(self, event_type: str, payload: dict):
        """Redis Pub/Sub üzerinden event gönder"""
        if self.report_id:
            from app.services.redis_pubsub import publish_agent_event
            publish_agent_event(self.report_id, event_type, payload)

    async def run_meeting(
        self,
        company_name: str,
        agent_data: Dict[str, Any],
        intelligence_report: Optional[Dict[str, Any]] = None,
        ws_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Tam komite toplantısını çalıştır.

        Args:
            company_name: Firma adı
            agent_data: Agent'lardan gelen veriler (tsg, ihale, news)
            intelligence_report: Rule-based istihbarat raporu
            ws_callback: WebSocket callback fonksiyonu

        Returns:
            dict: Council kararı ve transcript
        """
        # Demo mode: kısaltılmış toplantı
        if self.demo_mode:
            return await self._run_demo_meeting(
                company_name=company_name,
                agent_data=agent_data,
                intelligence_report=intelligence_report,
                ws_callback=ws_callback
            )

        transcript: List[Dict] = []
        scores: Dict[str, int] = {}
        start_time = datetime.utcnow()

        # Toplantı başladı event'i (Redis Pub/Sub)
        self._publish_event("council_started", {
            "total_phases": len(self.phases),
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "emoji": m.emoji
                }
                for m in self.members.values()
            ]
        })

        # Context hazırla
        context = self._prepare_context(company_name, agent_data, intelligence_report)

        # ============================================
        # AŞAMA 1: Açılış (Moderatör)
        # ============================================
        await self._run_phase(
            phase=self.phases[0],
            context=context,
            scores=scores,
            transcript=transcript,
            ws_callback=ws_callback
        )

        # ============================================
        # AŞAMA 2-6: Sunumlar
        # ============================================
        for phase in self.phases[1:6]:
            await self._run_phase(
                phase=phase,
                context=context,
                scores=scores,
                transcript=transcript,
                ws_callback=ws_callback
            )

        # ============================================
        # AŞAMA 7: Tartışma
        # ============================================
        await self._run_discussion(
            context=context,
            scores=scores,
            transcript=transcript,
            ws_callback=ws_callback
        )

        # ============================================
        # AŞAMA 8: Final Karar
        # ============================================
        final_decision = await self._run_final_decision(
            context=context,
            scores=scores,
            transcript=transcript,
            ws_callback=ws_callback
        )

        # Süre hesapla
        end_time = datetime.utcnow()
        duration = int((end_time - start_time).total_seconds())

        return {
            "final_score": final_decision["final_score"],
            "risk_level": final_decision["risk_level"],
            "decision": final_decision["decision"],
            "consensus": final_decision["consensus"],
            "conditions": final_decision.get("conditions", []),
            "summary": final_decision["summary"],
            "scores": {
                "initial": scores,
                "final": final_decision.get("final_scores", scores)
            },
            "transcript": transcript,
            "duration_seconds": duration
        }

    async def _run_demo_meeting(
        self,
        company_name: str,
        agent_data: Dict[str, Any],
        intelligence_report: Optional[Dict[str, Any]] = None,
        ws_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        DEMO MODE: Kısaltılmış komite toplantısı (~5 dakika).

        Tüm üyeler konuşur ama kısa tutulur:
        1. Moderatör açılış
        2. Her üye kısa görüş ve skor
        3. Final karar
        """
        print(f"[COUNCIL] DEMO MODE: Kısaltılmış toplantı başlıyor - {company_name}")

        transcript: List[Dict] = []
        scores: Dict[str, int] = {}
        start_time = datetime.utcnow()

        # Context hazırla
        context = self._prepare_context(company_name, agent_data, intelligence_report)

        # Tüm üyeleri al
        presentation_order = get_presentation_order()  # 5 analist sırayla

        # Toplantı başladı event'i - tüm üyeler
        self._publish_event("council_started", {
            "total_phases": 7,  # Demo: açılış + 5 sunum + final
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "emoji": m.emoji
                }
                for m in self.members.values()
            ],
            "estimated_duration_seconds": 300  # ~5 dakika
        })

        # Formatlanmış veri hazırla
        formatted_data = self._format_agent_data(context)
        intel_summary = self._format_intelligence_summary(context.get("intelligence_report"))

        # ============================================
        # DEMO AŞAMA 1: Moderatör Açılış
        # ============================================
        moderator = get_member("moderator")

        self._publish_event("council_phase_changed", {
            "phase": 1,
            "phase_name": "demo_opening",
            "title": "Toplantı Açılışı"
        })

        self._publish_event("council_speaker_changed", {
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "speaker_role": moderator.role,
            "speaker_emoji": moderator.emoji
        })

        # Moderatör açılış prompt'u (company_name sanitize edildi - prompt injection koruması)
        safe_company_name = self._sanitize_input(company_name)
        opening_prompt = f"""
Bugün {safe_company_name} firmasını değerlendireceğiz.

{intel_summary}

Lütfen toplantıyı açın (2-3 cümle). Firma hakkında kısa bir ön bilgi verin ve üyelere söz verin.
"""

        opening_response = await self._stream_speech_with_pacing(
            moderator.id,
            self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": get_system_prompt("moderator")},
                    {"role": "user", "content": opening_prompt}
                ],
                model="gpt-oss-120b"
            )
        )

        self._publish_event("council_speech", {
            "speaker_id": moderator.id,
            "chunk": "",
            "is_complete": True
        })

        transcript.append({
            "phase": 1,
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "content": opening_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        # ============================================
        # DEMO AŞAMA 2-6: Her Üye Kısa Değerlendirme
        # ============================================
        import re

        for i, member_id in enumerate(presentation_order):
            phase_num = i + 2
            member = get_member(member_id)

            if not member:
                continue

            self._publish_event("council_phase_changed", {
                "phase": phase_num,
                "phase_name": f"demo_{member_id}_presentation",
                "title": f"{member.name} Değerlendirmesi"
            })

            self._publish_event("council_speaker_changed", {
                "speaker_id": member.id,
                "speaker_name": member.name,
                "speaker_role": member.role,
                "speaker_emoji": member.emoji
            })

            # Değerlendirme prompt'u (2 dk toplantı için optimize)
            # company_name sanitize edildi - prompt injection koruması
            member_prompt = f"""
{safe_company_name} firmasını uzmanlık alanınız ({member.role}) açısından değerlendirin.

=== VERİLER ===
{formatted_data}

GÖREV: Değerlendirme yapın:
- 3-4 cümle detaylı analiz (güçlü/zayıf yönler)
- Risk skoru (0-100, 0=güvenli, 100=riskli)
- Kısa gerekçe

SKOR FORMATI: [SKOR: XX]
"""

            member_response = await self._stream_speech_with_pacing(
                member.id,
                self.llm.chat_stream(
                    messages=[
                        {"role": "system", "content": get_system_prompt(member_id)},
                        {"role": "user", "content": member_prompt}
                    ],
                    model="gpt-oss-120b"
                )
            )

            self._publish_event("council_speech", {
                "speaker_id": member.id,
                "chunk": "",
                "is_complete": True
            })

            transcript.append({
                "phase": phase_num,
                "speaker_id": member.id,
                "speaker_name": member.name,
                "content": member_response,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Skor çıkar
            match = re.search(r'\[SKOR:\s*(\d+)\]', member_response)
            if match:
                score = int(match.group(1))
                score = max(0, min(100, score))
            else:
                # Fallback: member'ın eğilim aralığından orta değer
                if member.score_tendency:
                    score = (member.score_tendency[0] + member.score_tendency[1]) // 2
                else:
                    score = 50

            scores[member_id] = score

            self._publish_event("council_score_given", {
                "member_id": member.id,
                "score": score
            })

        # ============================================
        # DEMO AŞAMA 7: Final Karar
        # ============================================
        self._publish_event("council_phase_changed", {
            "phase": 7,
            "phase_name": "demo_decision",
            "title": "Final Karar"
        })

        self._publish_event("council_speaker_changed", {
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "speaker_role": moderator.role,
            "speaker_emoji": moderator.emoji
        })

        # Ağırlıklı skor hesapla
        weighted_score = calculate_weighted_score(scores)
        final_score = int(weighted_score)

        # Risk seviyesi ve karar belirle
        risk_level = self._determine_risk_level(final_score)
        decision = self._determine_decision(final_score, context)
        consensus = self._calculate_consensus(scores)

        # Moderatör final özet (company_name sanitize edildi)
        final_prompt = f"""
{safe_company_name} değerlendirmesi tamamlandı.

Üye skorları: {scores}
Ağırlıklı final skor: {final_score}
Risk seviyesi: {risk_level}
Karar: {decision}
Konsensüs: %{consensus * 100:.0f}

Özet yapın (3-4 cümle):
- Kararı ve gerekçesini açıklayın
- Varsa koşulları belirtin
- Sonraki adımları önerin
"""

        final_response = await self._stream_speech_with_pacing(
            moderator.id,
            self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": get_system_prompt("moderator")},
                    {"role": "user", "content": final_prompt}
                ],
                model="gpt-oss-120b"
            )
        )

        self._publish_event("council_speech", {
            "speaker_id": moderator.id,
            "chunk": "",
            "is_complete": True
        })

        transcript.append({
            "phase": 7,
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "content": final_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Council decision event'i
        self._publish_event("council_decision", {
            "final_score": final_score,
            "risk_level": risk_level,
            "decision": decision,
            "consensus": consensus
        })

        # Süre hesapla
        end_time = datetime.utcnow()
        duration = int((end_time - start_time).total_seconds())

        print(f"[COUNCIL] DEMO MODE: Toplantı tamamlandı - {duration}s, skor={final_score}, karar={decision}, konsensüs=%{consensus*100:.0f}")

        return {
            "final_score": final_score,
            "risk_level": risk_level,
            "decision": decision,
            "consensus": consensus,
            "conditions": [],
            "summary": final_response,
            "scores": {
                "initial": scores,
                "final": scores
            },
            "transcript": transcript,
            "duration_seconds": duration
        }

    def _prepare_context(
        self,
        company_name: str,
        agent_data: Dict,
        intelligence_report: Optional[Dict] = None
    ) -> Dict:
        """Toplantı context'i hazırla"""
        return {
            "company_name": company_name,
            "tsg_data": agent_data.get("tsg"),
            "ihale_data": agent_data.get("ihale"),
            "news_data": agent_data.get("news"),
            "intelligence_report": intelligence_report,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _format_agent_data(self, context: Dict) -> str:
        """Agent verilerini LLM için okunabilir formatta hazırla"""
        parts = []

        # TSG Verileri
        tsg_data = context.get("tsg_data")
        if tsg_data:
            tsg = tsg_data.get("tsg_sonuc", {}).get("yapilandirilmis_veri", {})
            yoneticiler = tsg.get("Yoneticiler", [])
            # Yöneticiler object array veya string array olabilir
            if yoneticiler and isinstance(yoneticiler[0], dict):
                yonetici_str = ", ".join([
                    f"{y.get('ad', '')} ({y.get('gorev', '')})"
                    for y in yoneticiler
                ])
            else:
                yonetici_str = ", ".join(yoneticiler) if yoneticiler else "Bilinmiyor"
            parts.append(f"""
TICARET SICIL BILGILERI:
- Firma Unvani: {tsg.get("Firma Unvani", "Bilinmiyor")}
- Sermaye: {tsg.get("Sermaye", "Bilinmiyor")}
- Mersis No: {tsg.get("Mersis Numarasi", "Bilinmiyor")}
- Kurulus Tarihi: {tsg.get("Kurulus_Tarihi", "Bilinmiyor")}
- Faaliyet Alani: {tsg.get("Faaliyet_Konusu", "Bilinmiyor")}
- Yoneticiler: {yonetici_str}""")
        else:
            parts.append("\nTICARET SICIL: Veri bulunamadi!")

        # Ihale Verileri (K8s agent ve local agent farklı format kullanıyor)
        ihale_data = context.get("ihale_data")
        if ihale_data:
            # Her iki formatı da destekle: yasakli_mi (K8s) veya yasak_durumu (local)
            yasak_durumu = ihale_data.get("yasakli_mi", ihale_data.get("yasak_durumu", False))
            yasak_str = "EVET - AKTIF YASAK!" if yasak_durumu else "Hayir"

            # Her iki formatı da destekle: toplam_karar (K8s) veya bulunan_toplam_yasaklama (local)
            toplam = ihale_data.get("toplam_karar", ihale_data.get("bulunan_toplam_yasaklama", 0))
            eslesen = ihale_data.get("eslesen_karar", 0)
            yasaklamalar = ihale_data.get("yasaklamalar", [])

            # Yasaklamalardan ek bilgi çıkar
            if yasaklamalar and len(yasaklamalar) > 0:
                ilk = yasaklamalar[0]
                yasaklayan_kurum = ilk.get("yasaklayan_kurum", "-")
                yasak_suresi = ilk.get("yasak_suresi", "-")
                risk = "YUKSEK" if eslesen > 0 else "DUSUK"
            else:
                yasaklayan_kurum = ihale_data.get("yasaklayan_kurum", "-")
                yasak_suresi = ihale_data.get("yasak_suresi", "-")
                risk = ihale_data.get("risk_degerlendirmesi", "Bilinmiyor")

            # ONEMLI: Toplam karar sayisi Resmi Gazete'deki GENEL yasaklamalari gosterir
            # Firma icin onemli olan "Eslesen Karar" dir - bu firmaya ait yasaklama sayisi
            yasaklama_bulundu = ihale_data.get("yasaklama_bulundu", False)
            yasaklama_notu = ihale_data.get("yasaklama_notu", "")

            if eslesen > 0:
                ihale_aciklama = f"BU FIRMAYA AIT {eslesen} YASAKLAMA KARARI BULUNDU!"
            elif yasaklama_bulundu or len(yasaklamalar) > 0:
                # Yasaklama kayıtları var ama firma eşleştirmesi yapılamadı
                ihale_aciklama = f"UYARI: {len(yasaklamalar)} adet yasaklama kaydı bulundu, ancak firma eşleştirmesi doğrulanamadı. Manuel inceleme önerilir!"
            else:
                ihale_aciklama = f"Bu firmaya ait yasaklama karari BULUNMADI. (Resmi Gazete'de toplam {toplam} karar tarandı, hicbiri bu firmaya ait degil)"

            # Yasaklama detaylarını göster (varsa)
            yasaklama_detay = ""
            if yasaklamalar and len(yasaklamalar) > 0:
                yasaklama_detay = "\n- BULUNAN YASAKLAMA KAYITLARI:"
                for i, y in enumerate(yasaklamalar[:5], 1):  # İlk 5 kayıt
                    tarih = y.get("tarih", y.get("tarih_iso", "?"))
                    conf = y.get("match_confidence", 0)
                    pdf_url = y.get("pdf_url", "")
                    yasaklama_detay += f"\n  {i}. Tarih: {tarih}, Confidence: {conf:.2f}"
                    if pdf_url:
                        yasaklama_detay += f", PDF: {pdf_url}"
                if len(yasaklamalar) > 5:
                    yasaklama_detay += f"\n  ... ve {len(yasaklamalar) - 5} kayıt daha"

            parts.append(f"""
IHALE DURUMU:
- Aktif Yasak: {yasak_str}
- Bu Firmaya Ait Yasaklama: {eslesen} adet
- Taranan Toplam Karar (Genel): {toplam} adet (DİKKAT: Bu sayi firmaya ait degil, Resmi Gazete'deki tum yasaklamalari gosterir)
- Sonuc: {ihale_aciklama}
- Risk Degerlendirmesi: {risk}
- Yasaklayan Kurum: {yasaklayan_kurum}
- Yasak Suresi: {yasak_suresi}{yasaklama_detay}""")
        else:
            parts.append("\nIHALE DURUMU: Veri bulunamadi!")

        # Haber Verileri
        news_data = context.get("news_data")
        if news_data:
            ozet = news_data.get("ozet", {})
            sentiment = ozet.get("sentiment_score", 0)
            sentiment_str = "Olumlu" if sentiment > 0.1 else ("Olumsuz" if sentiment < -0.1 else "Notr")
            parts.append(f"""
MEDYA ANALIZI:
- Toplam Haber: {ozet.get("toplam", 0)}
- Olumlu Haber: {ozet.get("olumlu", 0)}
- Olumsuz Haber: {ozet.get("olumsuz", 0)}
- Sentiment Skoru: {sentiment:.2f} ({sentiment_str})
- Trend: {ozet.get("trend", "Notr").upper()}""")
        else:
            parts.append("\nMEDYA ANALIZI: Veri bulunamadi!")

        return "\n".join(parts)

    def _format_intelligence_summary(self, intel: Optional[Dict]) -> str:
        """Ön analiz özetini formatla"""
        if not intel:
            return ""

        risk = intel.get("risk_ozeti", {})
        faktorler = intel.get("risk_faktorleri", [])

        faktor_str = ""
        if faktorler:
            faktor_lines = []
            for f in faktorler[:5]:
                tip = f.get("tip", "bilgi")
                mesaj = f.get("mesaj", "")
                icon = "!" if tip == "kritik" else ("?" if tip == "uyari" else "+")
                faktor_lines.append(f"  [{icon}] {mesaj}")
            faktor_str = "\n".join(faktor_lines)

        return f"""
ON ANALIZ SONUCU (Rule-Based):
- Risk Skoru: {risk.get("risk_skoru", "?")} / 100
- Risk Seviyesi: {risk.get("risk_seviyesi", "?").upper()}
- Karar Onerisi: {risk.get("karar_onerisi", "?")}
- Aciklama: {risk.get("karar_aciklamasi", "?")}

Risk Faktorleri:
{faktor_str if faktor_str else "  Onemli risk faktoru tespit edilmedi."}
"""

    async def _run_phase(
        self,
        phase: Dict,
        context: Dict,
        scores: Dict[str, int],
        transcript: List[Dict],
        ws_callback: Optional[Callable]
    ):
        """Tek bir aşamayı çalıştır"""
        speaker_id = phase["speaker"]
        member = get_member(speaker_id)

        if not member:
            return

        # Phase değişti event'i (Redis Pub/Sub)
        self._publish_event("council_phase_changed", {
            "phase": phase["phase"],
            "phase_name": phase["name"],
            "title": phase["title"]
        })

        # Konuşmacı değişti event'i (Redis Pub/Sub)
        self._publish_event("council_speaker_changed", {
            "speaker_id": member.id,
            "speaker_name": member.name,
            "speaker_role": member.role,
            "speaker_emoji": member.emoji
        })

        # System prompt al
        system_prompt = get_system_prompt(speaker_id)

        # User prompt hazırla
        user_prompt = self._build_user_prompt(phase, context, scores)

        # LLM'den yanıt al (streaming + pacing ile)
        full_response = await self._stream_speech_with_pacing(
            member.id,
            self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-oss-120b"
            )
        )

        # Final chunk (Redis Pub/Sub)
        self._publish_event("council_speech", {
            "speaker_id": member.id,
            "chunk": "",
            "is_complete": True
        })

        # Skor çıkar (eğer sunum aşamasıysa)
        if phase["name"].endswith("_presentation"):
            score = self._extract_score(full_response, member)
            scores[speaker_id] = score

            self._publish_event("council_score_given", {
                "member_id": member.id,
                "score": score
            })

        # Transcript'e ekle
        transcript.append({
            "phase": phase["phase"],
            "speaker_id": member.id,
            "speaker_name": member.name,
            "content": full_response,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _run_discussion(
        self,
        context: Dict,
        scores: Dict[str, int],
        transcript: List[Dict],
        ws_callback: Optional[Callable]
    ):
        """Tartışma turunu çalıştır"""
        phase = self.phases[6]  # discussion phase

        self._publish_event("council_phase_changed", {
            "phase": phase["phase"],
            "phase_name": phase["name"],
            "title": phase["title"]
        })

        # En farklı görüşe sahip iki üyeyi bul
        if len(scores) >= 2:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1])
            lowest = sorted_scores[0]
            highest = sorted_scores[-1]

            # Tartışma sadece yeterli fark varsa (10 puan)
            if highest[1] - lowest[1] >= 10:
                # Düşük skor veren savunuyor (iyimser görüş)
                await self._speak_in_discussion(
                    speaker_id=lowest[0],
                    context=context,
                    scores=scores,
                    target_id=highest[0],
                    transcript=transcript,
                    ws_callback=ws_callback
                )

                # Yüksek skor veren karşı argüman (temkinli görüş)
                await self._speak_in_discussion(
                    speaker_id=highest[0],
                    context=context,
                    scores=scores,
                    target_id=lowest[0],
                    transcript=transcript,
                    ws_callback=ws_callback
                )

    async def _speak_in_discussion(
        self,
        speaker_id: str,
        context: Dict,
        scores: Dict[str, int],
        target_id: str,
        transcript: List[Dict],
        ws_callback: Optional[Callable]
    ):
        """Tartışmada konuşma"""
        member = get_member(speaker_id)
        target = get_member(target_id)

        if not member or not target:
            return

        self._publish_event("council_speaker_changed", {
            "speaker_id": member.id,
            "speaker_name": member.name,
            "speaker_role": member.role,
            "speaker_emoji": member.emoji
        })

        system_prompt = get_system_prompt(speaker_id)
        # company_name sanitize edildi - prompt injection koruması
        company_name = self._sanitize_input(context["company_name"])
        user_prompt = f"""
{company_name} firması için tartışma aşamasındasınız. {target.name} ({target.role}) sizden farklı düşünüyor.

Sizin skorunuz: {scores.get(speaker_id, 50)}
{target.name}'ın skoru: {scores.get(target_id, 50)}

Kısa ve öz bir şekilde (2-3 cümle) görüşünüzü savunun veya uzlaşma arayın.
"""

        full_response = await self._stream_speech_with_pacing(
            member.id,
            self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-oss-120b"
            )
        )

        self._publish_event("council_speech", {
            "speaker_id": member.id,
            "chunk": "",
            "is_complete": True
        })

        transcript.append({
            "phase": 7,
            "speaker_id": member.id,
            "speaker_name": member.name,
            "content": full_response,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _run_final_decision(
        self,
        context: Dict,
        scores: Dict[str, int],
        transcript: List[Dict],
        ws_callback: Optional[Callable]
    ) -> Dict:
        """Final karar aşaması"""
        phase = self.phases[7]  # decision phase
        moderator = get_member("moderator")

        self._publish_event("council_phase_changed", {
            "phase": phase["phase"],
            "phase_name": phase["name"],
            "title": phase["title"]
        })

        self._publish_event("council_speaker_changed", {
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "speaker_role": moderator.role,
            "speaker_emoji": moderator.emoji
        })

        # Ağırlıklı skor hesapla
        weighted_score = calculate_weighted_score(scores)
        final_score = int(weighted_score)

        # Risk seviyesi belirle
        risk_level = self._determine_risk_level(final_score)

        # Karar belirle
        decision = self._determine_decision(final_score, context)

        # Konsensüs hesapla
        consensus = self._calculate_consensus(scores)

        # Moderatör özeti (company_name sanitize edildi - prompt injection koruması)
        system_prompt = get_system_prompt("moderator")
        company_name = self._sanitize_input(context["company_name"])
        user_prompt = f"""
{company_name} firmasının değerlendirmesini özetleyin ve kararı açıklayın.

Üye skorları: {scores}
Final skor: {final_score}
Risk seviyesi: {risk_level}
Karar: {decision}
Konsensüs: %{consensus * 100:.0f}

Kısa bir özet yapın (3-4 cümle).
"""

        full_response = await self._stream_speech_with_pacing(
            moderator.id,
            self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-oss-120b"
            )
        )

        self._publish_event("council_speech", {
            "speaker_id": moderator.id,
            "chunk": "",
            "is_complete": True
        })

        transcript.append({
            "phase": 8,
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "content": full_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Council decision event'i (Redis Pub/Sub)
        self._publish_event("council_decision", {
            "final_score": final_score,
            "risk_level": risk_level,
            "decision": decision,
            "consensus": consensus
        })

        return {
            "final_score": final_score,
            "risk_level": risk_level,
            "decision": decision,
            "consensus": consensus,
            "summary": full_response,
            "final_scores": scores
        }

    def _build_user_prompt(self, phase: Dict, context: Dict, scores: Dict) -> str:
        """User prompt oluştur - formatlanmış verilerle"""
        # company_name sanitize edildi - prompt injection koruması
        company_name = self._sanitize_input(context["company_name"])
        formatted_data = self._format_agent_data(context)
        intel_summary = self._format_intelligence_summary(context.get("intelligence_report"))

        if phase["name"] == "opening":
            return f"""
Bugunku toplantida {company_name} firmasini degerlendirecegiz.

{intel_summary}

=== FIRMA VERILERI ===
{formatted_data}

Lutfen toplantiyi acin ve gundemi belirleyin. (2-3 cumle)
"""

        elif phase["name"].endswith("_presentation"):
            return f"""
{company_name} firmasini degerlendiriyorsunuz.

=== FIRMA VERILERI ===
{formatted_data}

Lutfen uzmanlik alaniniza gore degerlendirmenizi yapin:
- Kisa analiz (3-4 cumle)
- Risk skoru verin (0-100, 0=risk yok, 100=cok riskli)
- Gerekce belirtin

ONEMLI: Skorunuzu [SKOR: XX] formatinda belirtin.
"""

        return ""

    def _extract_score(self, response: str, member) -> int:
        """Yanıttan skor çıkar"""
        import re

        # [SKOR: XX] pattern'i ara
        match = re.search(r'\[SKOR:\s*(\d+)\]', response)
        if match:
            score = int(match.group(1))
            return max(0, min(100, score))

        # Fallback: member'ın eğilim aralığından orta değer
        if member.score_tendency:
            return (member.score_tendency[0] + member.score_tendency[1]) // 2
        return 50

    def _determine_risk_level(self, score: int) -> str:
        """Skor'dan risk seviyesi belirle"""
        if score <= 20:
            return "dusuk"
        elif score <= 40:
            return "orta_dusuk"
        elif score <= 60:
            return "orta"
        elif score <= 80:
            return "orta_yuksek"
        else:
            return "yuksek"

    def _determine_decision(self, score: int, context: Dict) -> str:
        """Skor ve context'ten karar belirle"""
        # İhale yasağı varsa otomatik red (her iki formatı da destekle)
        ihale_data = context.get("ihale_data", {})
        if isinstance(ihale_data, dict):
            yasak_durumu = ihale_data.get("yasakli_mi", ihale_data.get("yasak_durumu", False))
            if yasak_durumu:
                return "red"

        if score <= 30:
            return "onay"
        elif score <= 50:
            return "sartli_onay"
        elif score <= 70:
            return "inceleme_gerek"
        else:
            return "red"

    def _calculate_consensus(self, scores: Dict[str, int]) -> float:
        """Konsensüs oranı hesapla"""
        if len(scores) < 2:
            return 1.0

        values = list(scores.values())
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        # Standart sapma düşükse yüksek konsensüs
        # Max std_dev 50 olabilir (0-100 aralığında)
        consensus = 1 - (std_dev / 50)
        return max(0, min(1, consensus))
