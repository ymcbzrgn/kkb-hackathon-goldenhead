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
    NOT: Bu model DB schema'sına UYGUN!
    """
    __tablename__ = "agent_results"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # İlişki
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)

    # Agent Bilgileri - DB'ye UYGUN İSİMLER
    agent_id = Column(String(50), nullable=False)  # tsg_agent, ihale_agent, news_agent
    agent_name = Column(String(100))  # TSG Agent, İhale Agent, News Agent

    # Durum
    status = Column(String(20), nullable=False, default="pending")

    # Veriler - TEK KOLON (DB'de 'data' olarak)
    data = Column(JSONB)

    # Özet
    summary = Column(Text)
    # NOTE: default=list yerine default=None kullanıldı (SQLAlchemy mutable default anti-pattern)
    key_findings = Column(JSONB, default=None, nullable=True)
    warning_flags = Column(JSONB, default=None, nullable=True)

    # Performans
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Error (DB'de var)
    error_message = Column(Text)

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    report = relationship("Report", back_populates="agent_results")

    def __repr__(self):
        return f"<AgentResult(report_id={self.report_id}, agent={self.agent_id}, status={self.status})>"


class CouncilDecision(Base):
    """
    Komite kararları tablosu.
    6 kişilik komite toplantısının sonuçlarını saklar.
    NOT: Bu model DB schema'sına UYGUN!
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
    consensus = Column(Float)  # 0.00 - 1.00 (numeric in DB)

    # Karar Detayları
    # NOTE: default=list yerine default=None kullanıldı (SQLAlchemy mutable default anti-pattern)
    conditions = Column(JSONB, default=None, nullable=True)
    summary = Column(Text)  # DB'de var

    # Bireysel Skorlar
    initial_scores = Column(JSONB)
    final_scores = Column(JSONB)

    # Transcript
    transcript = Column(JSONB)

    # Süre
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    report = relationship("Report", back_populates="council_decision")

    def __repr__(self):
        return f"<CouncilDecision(report_id={self.report_id}, score={self.final_score}, decision={self.decision})>"
