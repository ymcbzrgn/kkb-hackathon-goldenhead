"""
Agent Schemas
Agent ile ilgili Pydantic modelleri
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Agent tipleri"""
    TSG = "tsg_agent"
    IHALE = "ihale_agent"
    NEWS = "news_agent"


class AgentStatus(str, Enum):
    """Agent durumu"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# TSG Agent Data Schemas
class OrtakBilgisi(BaseModel):
    """Ortak bilgisi"""
    ad: str
    pay_orani: float = Field(..., ge=0, le=100)
    tip: Optional[str] = None  # "gercek_kisi" | "tuzel_kisi"


class YoneticiDegisikligi(BaseModel):
    """Yönetici değişikliği"""
    tarih: str
    eski: Optional[str]
    yeni: str
    gorev: str


class SermayeDegisikligi(BaseModel):
    """Sermaye değişikliği"""
    tarih: str
    eski: int
    yeni: int
    para_birimi: str = "TRY"


class TsgData(BaseModel):
    """TSG Agent sonuç verisi"""
    kurulus_tarihi: Optional[str]
    sermaye: Optional[int]
    sermaye_para_birimi: str = "TRY"
    adres: Optional[str]
    faaliyet_konusu: Optional[str]
    ortaklar: List[OrtakBilgisi] = []
    yonetim_kurulu: List[Dict[str, str]] = []
    sermaye_degisiklikleri: List[SermayeDegisikligi] = []
    yonetici_degisiklikleri: List[YoneticiDegisikligi] = []
    tsg_ilan_sayisi: int = 0


# İhale Agent Data Schemas
class YasakBilgisi(BaseModel):
    """Yasak bilgisi"""
    sebep: str
    baslangic: str
    bitis: str
    kurum: str
    aciklama: Optional[str]


class IhaleData(BaseModel):
    """İhale Agent sonuç verisi"""
    yasak_durumu: bool = False
    aktif_yasak: Optional[YasakBilgisi]
    gecmis_yasaklar: List[YasakBilgisi] = []
    kontrol_tarihi: str
    kaynak: str = "EKAP"


# News Agent Data Schemas
class HaberBilgisi(BaseModel):
    """Haber bilgisi"""
    baslik: str
    kaynak: str
    tarih: str
    url: Optional[str]
    sentiment: Optional[str]  # "pozitif" | "negatif" | "notr"


class NewsData(BaseModel):
    """News Agent sonuç verisi"""
    toplam_haber: int = 0
    pozitif: int = 0
    negatif: int = 0
    notr: int = 0
    sentiment_score: float = Field(0, ge=-1, le=1)
    trend: str = "stabil"  # "yukari" | "asagi" | "stabil"
    onemli_haberler: List[HaberBilgisi] = []


# Generic Agent Result Schema
class AgentResultSchema(BaseModel):
    """Agent sonucu"""
    agent_id: str
    status: AgentStatus
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    duration_seconds: int = 0
    summary: Optional[str]
    key_findings: List[str] = []
    warning_flags: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentProgress(BaseModel):
    """Agent ilerleme bilgisi"""
    agent_id: str
    progress: int = Field(..., ge=0, le=100)
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
