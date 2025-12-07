"""
Ihale Agent Package - Resmi Gazete Yasaklama Karari Kontrolu

Bu modul, Resmi Gazete'den ihale yasaklama kararlarini
tarar ve firma bazinda kontrol yapar.

KAYNAK: resmigazete.gov.tr -> Cesitli Ilanlar -> Yasaklama Kararlari

Bilesenler:
- IhaleAgent: Ana agent sinifi
- ResmiGazeteScraper: Playwright ile web scraping
- IhalePDFReader: PyMuPDF + Tesseract OCR ile PDF okuma
- IhaleCompanyMatcher: LLM ile firma eslestirme

Kullanim:
    from app.agents.ihale import IhaleAgent

    agent = IhaleAgent()
    result = await agent.execute(
        company_name="ABC INSAAT A.S.",
        vergi_no="1234567890",
        search_days=90
    )
"""

from app.agents.ihale.agent import IhaleAgent
from app.agents.ihale.scraper import ResmiGazeteScraper
from app.agents.ihale.pdf_reader import IhalePDFReader
from app.agents.ihale.company_matcher import IhaleCompanyMatcher

__all__ = [
    "IhaleAgent",
    "ResmiGazeteScraper",
    "IhalePDFReader",
    "IhaleCompanyMatcher",
]
