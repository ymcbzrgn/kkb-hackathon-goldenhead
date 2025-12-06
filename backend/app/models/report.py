"""
Report Model
Ana rapor tablosu
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.core.database import Base


class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    DUSUK = "dusuk"
    ORTA_DUSUK = "orta_dusuk"
    ORTA = "orta"
    ORTA_YUKSEK = "orta_yuksek"
    YUKSEK = "yuksek"


class Decision(str, Enum):
    ONAY = "onay"
    SARTLI_ONAY = "sartli_onay"
    RED = "red"
    INCELEME_GEREK = "inceleme_gerek"


class Report(Base):
    """
    Ana rapor tablosu.
    Firma istihbarat raporlarını saklar.
    """
    __tablename__ = "reports"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Firma Bilgileri
    company_name = Column(String(500), nullable=False, index=True)
    company_tax_no = Column(String(20), index=True)
    company_trade_name = Column(String(500))
    company_address = Column(Text)
    company_city = Column(String(100))
    company_district = Column(String(100))

    # Versiyon & Kategori
    version = Column(Integer, default=1)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    priority = Column(String(20), default="normal")

    # Durum
    status = Column(String(20), nullable=False, default=ReportStatus.PENDING.value, index=True)
    status_message = Column(Text)
    progress = Column(Integer, default=0)

    # Sonuçlar
    final_score = Column(Integer)
    risk_level = Column(String(20))
    decision = Column(String(30))
    decision_summary = Column(Text)

    # Süre Bilgileri
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Notlar
    internal_notes = Column(Text)
    external_notes = Column(Text)

    # Metadata (esnek alan)
    meta_data = Column("metadata", JSONB, default={})

    # Reserved Kolonlar
    reserved_text_1 = Column(Text)
    reserved_text_2 = Column(Text)
    reserved_text_3 = Column(Text)
    reserved_int_1 = Column(Integer)
    reserved_int_2 = Column(Integer)
    reserved_bool_1 = Column(String(5))  # boolean as string
    reserved_json = Column(JSONB)

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    agent_results = relationship("AgentResult", back_populates="report", cascade="all, delete-orphan")
    council_decision = relationship("CouncilDecision", back_populates="report", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Report(id={self.id}, company={self.company_name}, status={self.status})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_name": self.company_name,
            "company_tax_no": self.company_tax_no,
            "status": self.status,
            "final_score": self.final_score,
            "risk_level": self.risk_level,
            "decision": self.decision,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds
        }
