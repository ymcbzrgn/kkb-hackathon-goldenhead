"""
Ihale Agent - Resmi Gazete Yasaklama Karari Kontrolu

Bu dosya geriye donuk uyumluluk icin korunuyor.
Yeni kod icin app.agents.ihale.IhaleAgent kullanin.

KAYNAK: resmigazete.gov.tr -> Cesitli Ilanlar -> Yasaklama Kararlari
(EKAP DEGIL! EKAP yanlis kaynakti.)
"""
from typing import Optional
from app.agents.ihale import IhaleAgent as _IhaleAgent
from app.agents.base_agent import AgentResult


# Re-export for backwards compatibility
IhaleAgent = _IhaleAgent


class YasakBilgisi:
    """Yasak bilgisi yapisi (legacy)"""

    def __init__(
        self,
        sebep: str,
        baslangic: str,
        bitis: str,
        kurum: str,
        aciklama: Optional[str] = None
    ):
        self.sebep = sebep
        self.baslangic = baslangic
        self.bitis = bitis
        self.kurum = kurum
        self.aciklama = aciklama

    def to_dict(self) -> dict:
        return {
            "sebep": self.sebep,
            "baslangic": self.baslangic,
            "bitis": self.bitis,
            "kurum": self.kurum,
            "aciklama": self.aciklama
        }


__all__ = ["IhaleAgent", "YasakBilgisi"]
