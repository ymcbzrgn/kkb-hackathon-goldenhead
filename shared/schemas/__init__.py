"""
Shared Schemas
Backend ve Frontend arasında paylaşılan Pydantic modelleri
"""
from shared.schemas.report import (
    ReportStatus,
    RiskLevel,
    Decision,
    ReportCreate,
    ReportListItem,
    ReportDetail,
    ReportResponse,
    ReportListResponse,
)
from shared.schemas.agent import (
    AgentType,
    AgentStatus,
    TsgData,
    IhaleData,
    NewsData,
    AgentResultSchema,
)
from shared.schemas.council import (
    CouncilMemberSchema,
    TranscriptEntry,
    CouncilScores,
    CouncilDecision,
)
from shared.schemas.websocket import (
    WebSocketEventType,
    WebSocketMessage,
    JobStartedPayload,
    AgentProgressPayload,
    CouncilSpeechPayload,
)

__all__ = [
    # Report
    "ReportStatus",
    "RiskLevel",
    "Decision",
    "ReportCreate",
    "ReportListItem",
    "ReportDetail",
    "ReportResponse",
    "ReportListResponse",
    # Agent
    "AgentType",
    "AgentStatus",
    "TsgData",
    "IhaleData",
    "NewsData",
    "AgentResultSchema",
    # Council
    "CouncilMemberSchema",
    "TranscriptEntry",
    "CouncilScores",
    "CouncilDecision",
    # WebSocket
    "WebSocketEventType",
    "WebSocketMessage",
    "JobStartedPayload",
    "AgentProgressPayload",
    "CouncilSpeechPayload",
]
