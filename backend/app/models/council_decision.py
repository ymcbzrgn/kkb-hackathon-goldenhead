"""
Council Decision & Agent Result Models
Komite kararları ve agent sonuçları
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.core.database import Base


class AgentType(str, Enum):
    TSG = "tsg_agent"
    IHALE = "ihale_agent"
    NEWS = "news_agent"


class AgentResult(Base):
    """
    Agent sonuçları tablosu.
    Her agent'ın topladığı verileri saklar.
    """
    __tablename__ = "agent_results"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # İlişki
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)

    # Agent Bilgileri
    agent_type = Column(String(30), nullable=False)
    agent_version = Column(String(20), default="1.0")

    # Durum
    status = Column(String(20), nullable=False, default="pending")
    status_message = Column(Text)
    progress = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)

    # Veriler
    raw_data = Column(JSONB)  # Ham scrape verisi
    processed_data = Column(JSONB)  # İşlenmiş veri

    # Özet
    summary = Column(Text)
    key_findings = Column(JSONB, default=[])
    warning_flags = Column(JSONB, default=[])

    # Performans
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Kaynak Bilgileri
    source_urls = Column(JSONB, default=[])
    source_count = Column(Integer)

    # Metadata
    metadata = Column(JSONB, default={})

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationship
    report = relationship("Report", back_populates="agent_results")

    def __repr__(self):
        return f"<AgentResult(report_id={self.report_id}, agent={self.agent_type}, status={self.status})>"


class CouncilDecision(Base):
    """
    Komite kararları tablosu.
    6 kişilik komite toplantısının sonuçlarını saklar.
    """
    __tablename__ = "council_decisions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # İlişki (1:1)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Skorlar
    final_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    decision = Column(String(30), nullable=False)
    consensus = Column(Float)  # 0.00 - 1.00
    score_variance = Column(Float)

    # Bireysel Skorlar
    initial_scores = Column(JSONB, nullable=False)
    final_scores = Column(JSONB, nullable=False)

    # Revizyon Bilgileri
    revisions = Column(JSONB, default=[])

    # Karar Detayları
    conditions = Column(JSONB, default=[])
    dissent_note = Column(Text)
    decision_rationale = Column(Text)

    # Transcript
    transcript = Column(JSONB, nullable=False)

    # Süre
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Faz Bilgileri
    phases_completed = Column(JSONB, default={})

    # Metadata
    metadata = Column(JSONB, default={})

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationship
    report = relationship("Report", back_populates="council_decision")

    def __repr__(self):
        return f"<CouncilDecision(report_id={self.report_id}, score={self.final_score}, decision={self.decision})>"
