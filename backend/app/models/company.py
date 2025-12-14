"""
Company Model
Firma bilgileri (cache amaçlı)
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Company(Base):
    """
    Firma cache tablosu.
    Daha önce sorgulanan firmaların bilgilerini saklar.
    NOT: Bu model DB schema'sına UYGUN!
    """
    __tablename__ = "companies"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Temel Bilgiler
    name = Column(String(255), nullable=False, index=True)
    tax_no = Column(String(20), unique=True, index=True)
    trade_registry_no = Column(String(50))  # DB'de var

    # Adres
    address = Column(Text)
    city = Column(String(100))

    # Detaylar
    sector = Column(String(200))

    # Cache Verileri
    cached_data = Column(JSONB)  # DB'de var

    # Rapor İlişkisi
    last_report_id = Column(UUID(as_uuid=True))  # DB'de var
    total_reports = Column(Integer)  # DB'de var

    # Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Company(tax_no={self.tax_no}, name={self.name})>"


class Category(Base):
    """
    Rapor kategorileri.
    """
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    color = Column(String(7), default="#6B7280")
    icon = Column(String(50))
    parent_id = Column(UUID(as_uuid=True))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    meta_data = Column("metadata", JSONB, default=dict)  # Mutable default fix
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
