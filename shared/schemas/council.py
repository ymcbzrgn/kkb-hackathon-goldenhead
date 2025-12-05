"""
Council Schemas
Komite ile ilgili Pydantic modelleri
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CouncilPhase(str, Enum):
    """Toplantı aşamaları"""
    OPENING = "opening"
    RISK_PRESENTATION = "risk_presentation"
    BUSINESS_PRESENTATION = "business_presentation"
    LEGAL_PRESENTATION = "legal_presentation"
    MEDIA_PRESENTATION = "media_presentation"
    SECTOR_PRESENTATION = "sector_presentation"
    DISCUSSION = "discussion"
    DECISION = "decision"


class CouncilMemberSchema(BaseModel):
    """Komite üyesi"""
    id: str
    name: str
    role: str
    emoji: str
    character: Optional[str]
    expertise: List[str] = []


class TranscriptEntry(BaseModel):
    """Toplantı transcript girişi"""
    phase: int
    speaker_id: str
    speaker_name: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    score: Optional[int] = Field(None, ge=0, le=100)


class CouncilScores(BaseModel):
    """Komite skorları"""
    risk_analyst: Optional[int] = Field(None, ge=0, le=100)
    business_analyst: Optional[int] = Field(None, ge=0, le=100)
    legal_expert: Optional[int] = Field(None, ge=0, le=100)
    media_analyst: Optional[int] = Field(None, ge=0, le=100)
    sector_expert: Optional[int] = Field(None, ge=0, le=100)


class CouncilDecision(BaseModel):
    """Komite kararı"""
    final_score: int = Field(..., ge=0, le=100)
    risk_level: str  # "dusuk" | "orta_dusuk" | "orta" | "orta_yuksek" | "yuksek"
    decision: str  # "onay" | "sartli_onay" | "red" | "inceleme_gerek"
    consensus: float = Field(..., ge=0, le=1)
    conditions: List[str] = []
    summary: Optional[str]
    scores: Dict[str, CouncilScores]  # {"initial": {...}, "final": {...}}
    transcript: List[TranscriptEntry] = []
    duration_seconds: int = 0


class CouncilMeetingStart(BaseModel):
    """Toplantı başlangıç bilgisi"""
    company_name: str
    total_phases: int = 8
    members: List[CouncilMemberSchema]
    estimated_duration_seconds: int = 600


class CouncilPhaseChange(BaseModel):
    """Aşama değişikliği"""
    phase: int
    phase_name: str
    title: str


class CouncilSpeakerChange(BaseModel):
    """Konuşmacı değişikliği"""
    speaker_id: str
    speaker_name: str
    speaker_role: str
    speaker_emoji: str


class CouncilSpeech(BaseModel):
    """Konuşma chunk'ı"""
    speaker_id: str
    chunk: str
    is_final: bool = False


class CouncilScoreGiven(BaseModel):
    """Skor verildi"""
    member_id: str
    score: int = Field(..., ge=0, le=100)


class CouncilScoreRevision(BaseModel):
    """Skor revizyonu"""
    member_id: str
    old_score: int
    new_score: int
    reason: Optional[str]
