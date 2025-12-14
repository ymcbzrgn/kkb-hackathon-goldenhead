"""
News Sources - Kaynak-spesifik scraper'lar

Her scraper BaseNewsScraper'dan türetilir ve kendi CSS selector'larını tanımlar.

10 GÜVENİLİR KAYNAK (HACKATHON):

Devlet Kaynakları:
- aa_scraper.py: Anadolu Ajansı (Resmi haber ajansı)
- trthaber_scraper.py: TRT Haber (Devlet kanalı)

Demirören Grubu:
- hurriyet_scraper.py: Hürriyet
- milliyet_scraper.py: Milliyet (70+ yıl)
- cnnturk_scraper.py: CNN Türk (Uluslararası)

Ekonomi/Finans:
- dunya_scraper.py: Dünya Gazetesi
- ekonomim_scraper.py: Ekonomim
- bigpara_scraper.py: Bigpara (Hürriyet Finans)

Diğer Güvenilir:
- ntv_scraper.py: NTV (Doğuş Grubu)
- sozcu_scraper.py: Sözcü
"""
from app.agents.news.sources.base_scraper import BaseNewsScraper

# Devlet Kaynakları
from app.agents.news.sources.aa_scraper import AANewsScraper
from app.agents.news.sources.trthaber_scraper import TRTHaberScraper

# Demirören Grubu
from app.agents.news.sources.hurriyet_scraper import HurriyetScraper
from app.agents.news.sources.milliyet_scraper import MilliyetScraper
from app.agents.news.sources.cnnturk_scraper import CNNTurkScraper

# Ekonomi/Finans
from app.agents.news.sources.dunya_scraper import DunyaScraper
from app.agents.news.sources.ekonomim_scraper import EkonomimScraper
from app.agents.news.sources.bigpara_scraper import BigparaScraper

# Diğer Güvenilir
from app.agents.news.sources.ntv_scraper import NTVScraper
from app.agents.news.sources.sozcu_scraper import SozcuScraper

# Google Search (Tarih Filtreli) - DEPRECATED: Timeout sorunları
from app.agents.news.sources.google_scraper import GoogleNewsScraper

# DuckDuckGo Search (Primary) - Hızlı, rate limiting yok
from app.agents.news.sources.duckduckgo_scraper import DuckDuckGoScraper


__all__ = [
    "BaseNewsScraper",
    # Devlet
    "AANewsScraper",
    "TRTHaberScraper",
    # Demirören
    "HurriyetScraper",
    "MilliyetScraper",
    "CNNTurkScraper",
    # Ekonomi/Finans
    "DunyaScraper",
    "EkonomimScraper",
    "BigparaScraper",
    # Diğer
    "NTVScraper",
    "SozcuScraper",
    # Search Engines
    "GoogleNewsScraper",  # DEPRECATED
    "DuckDuckGoScraper",  # PRIMARY
]


def get_all_scrapers():
    """
    Tüm scraper sınıflarını döndür (10 KAYNAK).

    HACKATHON: Paralel çalışır, 20-30 haber beklenir!
    """
    return [
        # Devlet (En güvenilir)
        AANewsScraper,
        TRTHaberScraper,
        # Demirören Grubu (Geniş kapsam)
        HurriyetScraper,
        MilliyetScraper,
        CNNTurkScraper,
        # Ekonomi/Finans (Şirket haberleri)
        DunyaScraper,
        EkonomimScraper,
        BigparaScraper,
        # Diğer Güvenilir
        NTVScraper,
        SozcuScraper,
    ]


def get_state_scrapers():
    """Devlet kaynaklarını döndür (resmi açıklamalar)."""
    return [
        AANewsScraper,
        TRTHaberScraper,
    ]


def get_finance_scrapers():
    """Ekonomi/Finans kaynaklarını döndür."""
    return [
        DunyaScraper,
        EkonomimScraper,
        BigparaScraper,
    ]


def get_mainstream_scrapers():
    """Ana akım medya kaynaklarını döndür."""
    return [
        HurriyetScraper,
        MilliyetScraper,
        CNNTurkScraper,
        NTVScraper,
        SozcuScraper,
    ]


def get_google_scraper():
    """Google Search scraper'ı döndür (DEPRECATED - timeout sorunları)."""
    return GoogleNewsScraper


def get_duckduckgo_scraper():
    """DuckDuckGo Search scraper'ı döndür (PRIMARY - hızlı, rate limiting yok)."""
    return DuckDuckGoScraper


def get_search_scraper():
    """Primary search engine döndür (DuckDuckGo)."""
    return DuckDuckGoScraper
