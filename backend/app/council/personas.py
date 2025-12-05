"""
Council Personas
Komite üyelerinin karakter tanımları
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class CouncilMember:
    """Komite üyesi tanımı"""
    id: str
    name: str
    role: str
    emoji: str
    character: str
    experience_years: int
    score_tendency: Optional[Tuple[int, int]]  # (min, max) skor eğilimi
    expertise: list[str]
    speaking_style: str


COUNCIL_MEMBERS = {
    "risk_analyst": CouncilMember(
        id="risk_analyst",
        name="Mehmet Bey",
        role="Baş Risk Analisti",
        emoji="🔴",
        character="Temkinli, şüpheci, detaycı. Her riskin altını kazır.",
        experience_years=25,
        score_tendency=(50, 70),
        expertise=["kredi riski", "finansal analiz", "temerrüt tahminleme"],
        speaking_style="Resmi, ihtiyatlı, rakamlarla konuşur"
    ),

    "business_analyst": CouncilMember(
        id="business_analyst",
        name="Ayşe Hanım",
        role="İş Geliştirme Müdürü",
        emoji="🟢",
        character="Fırsatçı, iyimser, büyüme odaklı. Potansiyeli görür.",
        experience_years=15,
        score_tendency=(20, 35),
        expertise=["iş geliştirme", "pazar analizi", "müşteri ilişkileri"],
        speaking_style="Enerjik, ikna edici, fırsat odaklı"
    ),

    "legal_expert": CouncilMember(
        id="legal_expert",
        name="Av. Zeynep Hanım",
        role="Hukuk Müşaviri",
        emoji="⚖️",
        character="Tarafsız, belgeci, kurallara bağlı. Mevzuata hakimdir.",
        experience_years=20,
        score_tendency=(30, 50),
        expertise=["şirketler hukuku", "ticaret hukuku", "regülasyon"],
        speaking_style="Akademik, referans veren, dengeli"
    ),

    "media_analyst": CouncilMember(
        id="media_analyst",
        name="Deniz Bey",
        role="İtibar Analisti",
        emoji="📰",
        character="Algı odaklı, sosyal medya takipçisi, itibar uzmanı.",
        experience_years=12,
        score_tendency=(25, 45),
        expertise=["medya analizi", "itibar yönetimi", "kriz iletişimi"],
        speaking_style="Güncel, trend takipçisi, kamuoyu odaklı"
    ),

    "sector_expert": CouncilMember(
        id="sector_expert",
        name="Prof. Dr. Ali Bey",
        role="Sektör Uzmanı",
        emoji="📊",
        character="Makro bakışlı, akademik, sektör dinamiklerini bilir.",
        experience_years=30,
        score_tendency=(30, 45),
        expertise=["sektör analizi", "makroekonomi", "rekabet analizi"],
        speaking_style="Akademik, karşılaştırmalı, veri odaklı"
    ),

    "moderator": CouncilMember(
        id="moderator",
        name="Genel Müdür Yardımcısı",
        role="Komite Başkanı",
        emoji="👨‍⚖️",
        character="Sentezci, karar odaklı, dengeleyici. Son sözü söyler.",
        experience_years=35,
        score_tendency=None,  # Moderatör skor vermez, sentez yapar
        expertise=["yönetim", "strateji", "karar alma"],
        speaking_style="Özet yapan, yönlendiren, kararlı"
    ),
}


# Toplantı aşamaları
MEETING_PHASES = [
    {
        "phase": 1,
        "name": "opening",
        "title": "Açılış",
        "speaker": "moderator",
        "description": "Toplantıyı açar, gündemi belirler"
    },
    {
        "phase": 2,
        "name": "risk_presentation",
        "title": "Risk Değerlendirmesi",
        "speaker": "risk_analyst",
        "description": "Finansal riskleri sunar"
    },
    {
        "phase": 3,
        "name": "business_presentation",
        "title": "İş Potansiyeli",
        "speaker": "business_analyst",
        "description": "İş fırsatlarını sunar"
    },
    {
        "phase": 4,
        "name": "legal_presentation",
        "title": "Hukuki Değerlendirme",
        "speaker": "legal_expert",
        "description": "Hukuki durumu değerlendirir"
    },
    {
        "phase": 5,
        "name": "media_presentation",
        "title": "Medya Analizi",
        "speaker": "media_analyst",
        "description": "Medya algısını sunar"
    },
    {
        "phase": 6,
        "name": "sector_presentation",
        "title": "Sektör Değerlendirmesi",
        "speaker": "sector_expert",
        "description": "Sektör perspektifini sunar"
    },
    {
        "phase": 7,
        "name": "discussion",
        "title": "Tartışma",
        "speaker": None,  # Birden fazla konuşmacı
        "description": "Farklı görüşler tartışılır"
    },
    {
        "phase": 8,
        "name": "decision",
        "title": "Karar",
        "speaker": "moderator",
        "description": "Final karar açıklanır"
    },
]


def get_member(member_id: str) -> Optional[CouncilMember]:
    """Üye bilgisini getir"""
    return COUNCIL_MEMBERS.get(member_id)


def get_presentation_order() -> list[str]:
    """Sunum sırasını getir (moderatör hariç)"""
    return ["risk_analyst", "business_analyst", "legal_expert", "media_analyst", "sector_expert"]


def calculate_weighted_score(scores: dict[str, int]) -> float:
    """
    Ağırlıklı skor hesapla.
    Risk Analisti ve Hukuk Müşaviri daha yüksek ağırlığa sahip.
    """
    weights = {
        "risk_analyst": 0.30,      # En yüksek ağırlık
        "business_analyst": 0.15,
        "legal_expert": 0.25,      # Yüksek ağırlık
        "media_analyst": 0.15,
        "sector_expert": 0.15,
    }

    total_weight = 0
    weighted_sum = 0

    for member_id, score in scores.items():
        if member_id in weights:
            weighted_sum += score * weights[member_id]
            total_weight += weights[member_id]

    return weighted_sum / total_weight if total_weight > 0 else 50
