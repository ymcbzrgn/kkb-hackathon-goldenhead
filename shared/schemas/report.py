"""
Report Schemas
Rapor ile ilgili Pydantic modelleri
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReportStatus(str, Enum):
    """Rapor durumu"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    """Risk seviyesi"""
    DUSUK = "dusuk"
    ORTA_DUSUK = "orta_dusuk"
    ORTA = "orta"
    ORTA_YUKSEK = "orta_yuksek"
    YUKSEK = "yuksek"


class Decision(str, Enum):
    """Komite kararı"""
    ONAY = "onay"
    SARTLI_ONAY = "sartli_onay"
    RED = "red"
    INCELEME_GEREK = "inceleme_gerek"


# Request Schemas
class ReportCreate(BaseModel):
    """Rapor oluşturma isteği"""
    company_name: str = Field(..., min_length=2, max_length=200)
    company_tax_no: Optional[str] = Field(None, pattern=r"^\d{10,11}$")

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "ABC Teknoloji A.Ş.",
                "company_tax_no": "1234567890"
            }
        }


# Response Schemas
class ReportListItem(BaseModel):
    """Rapor listesi öğesi"""
    id: str
    company_name: str
    company_tax_no: Optional[str]
    status: ReportStatus
    final_score: Optional[int] = Field(None, ge=0, le=100)
    risk_level: Optional[RiskLevel]
    decision: Optional[Decision]
    created_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    class Config:
        from_attributes = True


class AgentResultSummary(BaseModel):
    """Agent sonuç özeti"""
    agent_id: str
    status: str
    key_findings: List[str] = []
    warning_flags: List[str] = []
    summary: Optional[str]


class CouncilSummary(BaseModel):
    """Komite kararı özeti"""
    final_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    decision: Decision
    consensus: float = Field(..., ge=0, le=1)
    conditions: List[str] = []


class ReportDetail(BaseModel):
    """Rapor detayı"""
    id: str
    company_name: str
    company_tax_no: Optional[str]
    status: ReportStatus
    created_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    # Agent sonuçları
    tsg_result: Optional[Dict[str, Any]]
    ihale_result: Optional[Dict[str, Any]]
    news_result: Optional[Dict[str, Any]]

    # Komite kararı
    council_decision: Optional[CouncilSummary]

    # Tam transcript (opsiyonel)
    transcript: Optional[List[Dict[str, Any]]]

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Tek rapor yanıtı"""
    success: bool
    data: Optional[ReportListItem]
    error: Optional[Dict[str, Any]]


class ReportDetailResponse(BaseModel):
    """Rapor detay yanıtı"""
    success: bool
    data: Optional[ReportDetail]
    error: Optional[Dict[str, Any]]


class ReportListResponse(BaseModel):
    """Rapor listesi yanıtı"""
    success: bool
    data: List[ReportListItem]
    pagination: Dict[str, int]
    error: Optional[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """Hata yanıtı"""
    success: bool = False
    error: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Firma adı gereklidir"
                }
            }
        }
