"""
News Semantic Search - Qdrant Vector DB Entegrasyonu

Haberleri vektorize ederek semantic search imkani saglar.
- Qdrant vector DB ile yuksek performansli arama
- LLM ile embedding olusturma
- Benzer haberleri bulma
- Firma ile ilgili haberleri filtreleme
"""
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.llm.client import LLMClient
from app.agents.news.logger import log, success, error, warn, debug


class NewsSemanticSearch:
    """
    Haber Semantic Search - Qdrant entegrasyonu.

    Ozellikler:
    - Haberleri vektorize et (LLM embedding)
    - Qdrant'a indexle
    - Semantic search ile benzer haberleri bul
    - Firma ile ilgili haberleri filtrele

    Kullanim:
        search = NewsSemanticSearch()
        await search.initialize()

        # Haber indexle
        await search.index_article(article)

        # Benzer haberleri bul
        similar = await search.find_similar("Turk Hava Yollari", top_k=20)
    """

    COLLECTION_NAME = "news_articles"
    VECTOR_SIZE = 1536  # OpenAI/KKB embedding boyutu

    def __init__(self):
        self._client = None
        self._llm = LLMClient()
        self._initialized = False

        # Config'den ayarlari al
        news_config = settings.profile_config.news
        self._enabled = news_config.enable_semantic_search
        self._top_k = news_config.semantic_top_k

        log(f"SemanticSearch: enabled={self._enabled}, top_k={self._top_k}")

    async def initialize(self) -> bool:
        """Qdrant baglantisini kur ve collection olustur."""
        if not self._enabled:
            warn("Semantic search devre disi (enable_semantic_search=False)")
            return False

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            # Qdrant baglantisi
            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )

            # Collection var mi kontrol et
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                # Collection olustur
                log(f"Qdrant collection olusturuluyor: {self.COLLECTION_NAME}")
                self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                success(f"Collection olusturuldu: {self.COLLECTION_NAME}")
            else:
                debug(f"Collection mevcut: {self.COLLECTION_NAME}")

            self._initialized = True
            success("Qdrant baglantisi kuruldu")
            return True

        except ImportError:
            warn("qdrant-client kurulu degil: pip install qdrant-client")
            return False
        except Exception as e:
            error(f"Qdrant baglantisi kurulamadi: {e}")
            return False

    async def index_article(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Tek bir haberi Qdrant'a indexle.

        Args:
            article: Haber verisi (title, text, url, date, source, ...)

        Returns:
            str: Olusuturulan point ID veya None
        """
        if not self._initialized:
            if not await self.initialize():
                return None

        try:
            from qdrant_client.http.models import PointStruct

            # Unique ID olustur (URL hash)
            url = article.get('url', '')
            point_id = self._generate_point_id(url)

            # Embedding icin text olustur
            title = article.get('title', article.get('baslik', ''))
            text = article.get('text', article.get('metin', ''))[:500]  # Ilk 500 karakter
            embedding_text = f"{title}. {text}"

            # Embedding al (LLM)
            embedding = await self._get_embedding(embedding_text)
            if not embedding:
                warn(f"Embedding olusturulamadi: {title[:50]}...")
                return None

            # Payload hazirla
            payload = {
                "title": title,
                "text": text[:1000],  # Max 1000 karakter
                "url": url,
                "date": article.get('date', article.get('tarih', '')),
                "source": article.get('source', article.get('kaynak', '')),
                "sentiment": article.get('sentiment', ''),
                "indexed_at": datetime.now().isoformat()
            }

            # Qdrant'a ekle
            self._client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            debug(f"Haber indexlendi: {title[:50]}... (ID: {point_id})")
            return str(point_id)

        except Exception as e:
            error(f"Haber indexleme hatasi: {e}")
            return None

    async def index_articles(self, articles: List[Dict[str, Any]]) -> int:
        """
        Birden fazla haberi batch olarak indexle.

        Args:
            articles: Haber listesi

        Returns:
            int: Basarili indexlenen haber sayisi
        """
        if not articles:
            return 0

        indexed_count = 0
        for article in articles:
            result = await self.index_article(article)
            if result:
                indexed_count += 1

        log(f"{indexed_count}/{len(articles)} haber indexlendi")
        return indexed_count

    async def find_similar(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_source: Optional[str] = None,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search ile benzer haberleri bul.

        Args:
            query: Arama sorgusu (firma adi, konu, vb.)
            top_k: Donduruluecek max sonuc sayisi (None ise config'den)
            filter_source: Sadece belirli kaynaktan haber getir
            min_score: Minimum benzerlik skoru (0-1)

        Returns:
            List[Dict]: Benzer haberler (score ile birlikte)
        """
        if not self._initialized:
            if not await self.initialize():
                return []

        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue

            # Query embedding'i al
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                warn(f"Query embedding olusturulamadi: {query}")
                return []

            # Top-k belirle
            k = top_k or self._top_k

            # Filter olustur
            search_filter = None
            if filter_source:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=filter_source)
                        )
                    ]
                )

            # Semantic search
            results = self._client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=k,
                score_threshold=min_score
            )

            # Sonuclari formatla
            similar_articles = []
            for hit in results:
                article = hit.payload
                article['similarity_score'] = round(hit.score, 3)
                article['point_id'] = hit.id
                similar_articles.append(article)

            log(f"Semantic search: '{query[:30]}...' -> {len(similar_articles)} sonuc")
            return similar_articles

        except Exception as e:
            error(f"Semantic search hatasi: {e}")
            return []

    async def find_company_news(
        self,
        company_name: str,
        alternative_names: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Firma ile ilgili haberleri semantic search ile bul.

        Birden fazla firma ismi ile arama yapabilir.

        Args:
            company_name: Ana firma adi
            alternative_names: Alternatif firma isimleri
            top_k: Max sonuc sayisi

        Returns:
            List[Dict]: Firma ile ilgili haberler
        """
        all_names = [company_name]
        if alternative_names:
            all_names.extend(alternative_names)

        # Tum isimler icin arama yap ve birlestir
        all_results = []
        seen_urls = set()

        for name in all_names:
            results = await self.find_similar(name, top_k=top_k)
            for article in results:
                url = article.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(article)

        # Score'a gore sirala
        all_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)

        # Top-k ile sinirla
        k = top_k or self._top_k
        return all_results[:k]

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """LLM ile text embedding olustur."""
        try:
            # LLM embed_single metodunu kullan
            embedding = await self._llm.embed_single(text)
            return embedding
        except Exception as e:
            warn(f"Embedding hatasi: {e}")
            return None

    def _generate_point_id(self, url: str) -> int:
        """URL'den unique point ID olustur (Qdrant int ID istiyor)."""
        if not url:
            url = str(datetime.now().timestamp())
        # MD5 hash'in ilk 16 karakterini int'e cevir
        hash_hex = hashlib.md5(url.encode()).hexdigest()[:16]
        return int(hash_hex, 16) % (2**63 - 1)  # Positive int64

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Collection istatistiklerini getir."""
        if not self._initialized:
            if not await self.initialize():
                return {"error": "Qdrant baglantisi kurulamadi"}

        try:
            info = self._client.get_collection(self.COLLECTION_NAME)
            return {
                "collection_name": self.COLLECTION_NAME,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            return {"error": str(e)}

    async def clear_collection(self) -> bool:
        """Collection'daki tum verileri sil."""
        if not self._initialized:
            if not await self.initialize():
                return False

        try:
            self._client.delete_collection(self.COLLECTION_NAME)
            log(f"Collection silindi: {self.COLLECTION_NAME}")
            # Yeniden olustur
            await self.initialize()
            return True
        except Exception as e:
            error(f"Collection silme hatasi: {e}")
            return False


# Test
async def test_semantic_search():
    """Semantic search test fonksiyonu."""
    print("\n" + "="*60)
    print("Semantic Search Test")
    print("="*60)

    search = NewsSemanticSearch()
    initialized = await search.initialize()

    if not initialized:
        print("Qdrant baglantisi kurulamadi!")
        return

    # Test haberi indexle
    test_article = {
        "title": "Turk Hava Yollari yolcu rekoru kirdi",
        "text": "THY 2024 yilinda 90 milyon yolcu tasiyarak yeni bir rekor kirdi.",
        "url": "https://test.com/thy-rekor",
        "date": "2024-12-10",
        "source": "Test Source",
        "sentiment": "olumlu"
    }

    result = await search.index_article(test_article)
    print(f"Index sonucu: {result}")

    # Arama yap
    similar = await search.find_similar("THY yolcu", top_k=5)
    print(f"\nBulunan benzer haberler: {len(similar)}")
    for article in similar:
        print(f"  - {article.get('title')} (score: {article.get('similarity_score')})")

    # Collection stats
    stats = await search.get_collection_stats()
    print(f"\nCollection stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_semantic_search())
