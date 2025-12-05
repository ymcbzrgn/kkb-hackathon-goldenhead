"""
WebSocket Schemas
WebSocket event'leri için Pydantic modelleri
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class WebSocketEventType(str, Enum):
    """WebSocket event tipleri"""
    # Connection
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Job lifecycle
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"

    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # Council events
    COUNCIL_STARTED = "council_started"
    COUNCIL_PHASE_CHANGED = "council_phase_changed"
    COUNCIL_SPEAKER_CHANGED = "council_speaker_changed"
    COUNCIL_SPEECH = "council_speech"
    COUNCIL_SCORE_GIVEN = "council_score_given"
    COUNCIL_SCORE_REVISION = "council_score_revision"
    COUNCIL_DECISION = "council_decision"


# Connection Payloads
class ConnectedPayload(BaseModel):
    """Bağlantı kuruldu"""
    report_id: str
    message: str = "Connected successfully"


# Job Payloads
class JobStartedPayload(BaseModel):
    """İş başladı"""
    report_id: str
    company_name: str
    estimated_duration_seconds: int = 2400  # 40 dakika


class JobCompletedPayload(BaseModel):
    """İş tamamlandı"""
    report_id: str
    duration_seconds: int
    final_score: int = Field(..., ge=0, le=100)
    risk_level: str
    decision: str


class JobFailedPayload(BaseModel):
    """İş başarısız"""
    report_id: str
    error_code: str
    error_message: str


# Agent Payloads
class AgentStartedPayload(BaseModel):
    """Agent başladı"""
    agent_id: str
    agent_name: str
    agent_description: Optional[str]


class AgentProgressPayload(BaseModel):
    """Agent ilerleme"""
    agent_id: str
    progress: int = Field(..., ge=0, le=100)
    message: str


class AgentCompletedPayload(BaseModel):
    """Agent tamamlandı"""
    agent_id: str
    duration_seconds: int
    summary: Optional[Dict[str, Any]]


class AgentFailedPayload(BaseModel):
    """Agent başarısız"""
    agent_id: str
    error_code: str
    error_message: str
    will_retry: bool = False


# Council Payloads
class CouncilStartedPayload(BaseModel):
    """Toplantı başladı"""
    total_phases: int = 8
    members: List[Dict[str, str]]


class CouncilPhaseChangedPayload(BaseModel):
    """Aşama değişti"""
    phase: int
    phase_name: str
    title: str


class CouncilSpeakerChangedPayload(BaseModel):
    """Konuşmacı değişti"""
    speaker_id: str
    speaker_name: str
    speaker_role: str
    speaker_emoji: str


class CouncilSpeechPayload(BaseModel):
    """Konuşma chunk'ı"""
    speaker_id: str
    chunk: str
    is_final: bool = False


class CouncilScoreGivenPayload(BaseModel):
    """Skor verildi"""
    member_id: str
    score: int = Field(..., ge=0, le=100)


class CouncilScoreRevisionPayload(BaseModel):
    """Skor revize edildi"""
    member_id: str
    old_score: int
    new_score: int
    reason: Optional[str]


class CouncilDecisionPayload(BaseModel):
    """Final karar"""
    final_score: int = Field(..., ge=0, le=100)
    risk_level: str
    decision: str
    consensus: float = Field(..., ge=0, le=1)


# Generic WebSocket Message
class WebSocketMessage(BaseModel):
    """WebSocket mesajı"""
    event: WebSocketEventType
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event": "agent_progress",
                "payload": {
                    "agent_id": "tsg_agent",
                    "progress": 50,
                    "message": "PDF'ler analiz ediliyor..."
                },
                "timestamp": "2024-12-06T10:30:00Z"
            }
        }
