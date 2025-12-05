"""
Council Service
6 kişilik AI kredi komitesi toplantısı
"""
import asyncio
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


class CouncilService:
    """
    Kredi Komitesi Servisi.

    Görevleri:
    1. Toplantıyı başlat
    2. Her üyenin sunumunu al (LLM ile)
    3. Tartışma turunu yönet
    4. Final kararı oluştur
    5. WebSocket üzerinden streaming yap
    """

    def __init__(self):
        self.llm = LLMClient()
        self.members = COUNCIL_MEMBERS
        self.phases = MEETING_PHASES

    async def run_meeting(
        self,
        company_name: str,
        agent_data: Dict[str, Any],
        ws_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Tam komite toplantısını çalıştır.

        Args:
            company_name: Firma adı
            agent_data: Agent'lardan gelen veriler (tsg, ihale, news)
            ws_callback: WebSocket callback fonksiyonu

        Returns:
            dict: Council kararı ve transcript
        """
        transcript: List[Dict] = []
        scores: Dict[str, int] = {}
        start_time = datetime.utcnow()

        # Toplantı başladı event'i
        if ws_callback:
            await ws_callback("council_started", {
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
        context = self._prepare_context(company_name, agent_data)

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

    def _prepare_context(self, company_name: str, agent_data: Dict) -> Dict:
        """Toplantı context'i hazırla"""
        return {
            "company_name": company_name,
            "tsg_data": agent_data.get("tsg"),
            "ihale_data": agent_data.get("ihale"),
            "news_data": agent_data.get("news"),
            "timestamp": datetime.utcnow().isoformat()
        }

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

        # Phase değişti event'i
        if ws_callback:
            await ws_callback("council_phase_changed", {
                "phase": phase["phase"],
                "phase_name": phase["name"],
                "title": phase["title"]
            })

        # Konuşmacı değişti event'i
        if ws_callback:
            await ws_callback("council_speaker_changed", {
                "speaker_id": member.id,
                "speaker_name": member.name,
                "speaker_role": member.role,
                "speaker_emoji": member.emoji
            })

        # System prompt al
        system_prompt = get_system_prompt(speaker_id)

        # User prompt hazırla
        user_prompt = self._build_user_prompt(phase, context, scores)

        # LLM'den yanıt al (streaming)
        full_response = ""
        async for chunk in self.llm.chat_stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="gpt-oss-120b"
        ):
            full_response += chunk
            if ws_callback:
                await ws_callback("council_speech", {
                    "speaker_id": member.id,
                    "chunk": chunk,
                    "is_final": False
                })

        # Final chunk
        if ws_callback:
            await ws_callback("council_speech", {
                "speaker_id": member.id,
                "chunk": "",
                "is_final": True
            })

        # Skor çıkar (eğer sunum aşamasıysa)
        if phase["name"].endswith("_presentation"):
            score = self._extract_score(full_response, member)
            scores[speaker_id] = score

            if ws_callback:
                await ws_callback("council_score_given", {
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

        if ws_callback:
            await ws_callback("council_phase_changed", {
                "phase": phase["phase"],
                "phase_name": phase["name"],
                "title": phase["title"]
            })

        # En farklı görüşe sahip iki üyeyi bul
        if len(scores) >= 2:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1])
            lowest = sorted_scores[0]
            highest = sorted_scores[-1]

            # Tartışma sadece yeterli fark varsa
            if highest[1] - lowest[1] >= 15:
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

        if ws_callback:
            await ws_callback("council_speaker_changed", {
                "speaker_id": member.id,
                "speaker_name": member.name,
                "speaker_role": member.role,
                "speaker_emoji": member.emoji
            })

        system_prompt = get_system_prompt(speaker_id)
        user_prompt = f"""
Tartışma aşamasındasınız. {target.name} ({target.role}) sizden farklı düşünüyor.

Sizin skorunuz: {scores.get(speaker_id, 50)}
{target.name}'ın skoru: {scores.get(target_id, 50)}

Kısa ve öz bir şekilde (2-3 cümle) görüşünüzü savunun veya uzlaşma arayın.
"""

        full_response = ""
        async for chunk in self.llm.chat_stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="gpt-oss-120b"
        ):
            full_response += chunk
            if ws_callback:
                await ws_callback("council_speech", {
                    "speaker_id": member.id,
                    "chunk": chunk,
                    "is_final": False
                })

        if ws_callback:
            await ws_callback("council_speech", {
                "speaker_id": member.id,
                "chunk": "",
                "is_final": True
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

        if ws_callback:
            await ws_callback("council_phase_changed", {
                "phase": phase["phase"],
                "phase_name": phase["name"],
                "title": phase["title"]
            })

        if ws_callback:
            await ws_callback("council_speaker_changed", {
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

        # Moderatör özeti
        system_prompt = get_system_prompt("moderator")
        user_prompt = f"""
Toplantıyı özetleyin ve kararı açıklayın.

Üye skorları: {scores}
Final skor: {final_score}
Risk seviyesi: {risk_level}
Karar: {decision}
Konsensüs: %{consensus * 100:.0f}

Kısa bir özet yapın (3-4 cümle).
"""

        full_response = ""
        async for chunk in self.llm.chat_stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="gpt-oss-120b"
        ):
            full_response += chunk
            if ws_callback:
                await ws_callback("council_speech", {
                    "speaker_id": moderator.id,
                    "chunk": chunk,
                    "is_final": False
                })

        if ws_callback:
            await ws_callback("council_speech", {
                "speaker_id": moderator.id,
                "chunk": "",
                "is_final": True
            })

        transcript.append({
            "phase": 8,
            "speaker_id": moderator.id,
            "speaker_name": moderator.name,
            "content": full_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Council decision event'i
        if ws_callback:
            await ws_callback("council_decision", {
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
        """User prompt oluştur"""
        company_name = context["company_name"]

        if phase["name"] == "opening":
            return f"""
Bugünkü toplantıda {company_name} firmasını değerlendireceğiz.

TSG Verileri: {context.get('tsg_data', 'Veri yok')}
İhale Verileri: {context.get('ihale_data', 'Veri yok')}
Haber Verileri: {context.get('news_data', 'Veri yok')}

Lütfen toplantıyı açın ve gündemi belirleyin. (2-3 cümle)
"""

        elif phase["name"].endswith("_presentation"):
            return f"""
{company_name} firmasını değerlendiriyorsunuz.

TSG Verileri: {context.get('tsg_data', 'Veri yok')}
İhale Verileri: {context.get('ihale_data', 'Veri yok')}
Haber Verileri: {context.get('news_data', 'Veri yok')}

Lütfen uzmanlık alanınıza göre değerlendirmenizi yapın.
- Kısa analiz (3-4 cümle)
- Risk skoru verin (0-100, 0=risk yok, 100=çok riskli)
- Gerekçenizi belirtin

Format: [SKOR: XX] şeklinde skoru belirtin.
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
        # İhale yasağı varsa otomatik red
        ihale_data = context.get("ihale_data", {})
        if isinstance(ihale_data, dict) and ihale_data.get("yasak_durumu"):
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
