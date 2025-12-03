# 🧠 Vector Database: Kurumsal Hafıza

> Qdrant ile Halüsinasyonsuz, Tutarlı AI Kararları
>
> "Sistem her kararı hatırlıyor, her pattern'i öğreniyor, her firmayı karşılaştırıyor."

---

## 📋 İçindekiler


- [Neden Vector DB?](#-neden-vector-db)
- [Mimari](#-mimari)
- [Collection Yapıları](#-collection-yapıları)
- [Embedding Stratejisi](#-embedding-stratejisi)
- [Kullanım Senaryoları](#-kullanım-senaryoları)
- [Query Örnekleri](#-query-örnekleri)
- [Entegrasyon Noktaları](#-entegrasyon-noktaları)
- [Kurulum](#-kurulum)

---

## 🎯 Neden Vector DB?

### Problem: Halüsinasyon

```
❌ LLM Tek Başına:
   "Bu firmada yönetici değişikliği riski var, 
    geçmişte benzer firmalar batmıştır."
    
   → Hangi firmalar? Ne zaman? Gerçek mi?
   → HALÜSINASYON RİSKİ
```

### Çözüm: Kurumsal Hafıza

```
✅ LLM + Qdrant:
   "Bu firmada yönetici değişikliği riski var.
    Geçen ay değerlendirdiğimiz XYZ Ltd'de benzer 
    durum vardı - 45 puan vermiştik, şartlı onay 
    çıkmıştı. (Rapor ID: abc-123)"
    
   → Gerçek referans, doğrulanabilir
   → SIFIR HALÜSINASYON
```

### Jüri Mesajı

> "Sistemimiz hayal ürünü referanslar vermiyor. Her iddia, veritabanındaki gerçek bir karara dayanıyor. Kurumsal hafıza sayesinde tutarlı ve denetlenebilir kararlar alıyoruz."

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                        VERİ AKIŞI                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐   │
│  │   Rapor     │     │   Embedding │     │     QDRANT      │   │
│  │ Tamamlandı  │────▶│   Service   │────▶│                 │   │
│  └─────────────┘     │(qwen3-emb)  │     │  ┌───────────┐  │   │
│                      └─────────────┘     │  │ companies │  │   │
│                                          │  ├───────────┤  │   │
│                                          │  │ patterns  │  │   │
│                                          │  ├───────────┤  │   │
│                                          │  │ decisions │  │   │
│                                          │  └───────────┘  │   │
│                                          └────────┬────────┘   │
│                                                   │             │
│  ┌─────────────┐     ┌─────────────┐              │             │
│  │ Yeni Rapor  │     │   Semantic  │◀─────────────┘             │
│  │ Başlatıldı  │────▶│   Search    │                            │
│  └─────────────┘     └──────┬──────┘                            │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  📋 CONTEXT ZENGİNLEŞTİRME                               │   │
│  │                                                          │   │
│  │  • Benzer firma: XYZ Ltd (skor: 42)                     │   │
│  │  • Benzer pattern: "Yönetici sirkülasyonu" (%72 risk)   │   │
│  │  • Council hafızası: "Mehmet Bey benzer durumda..."     │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│                      ┌─────────────┐                            │
│                      │   COUNCIL   │  ← Gerçek verilerle        │
│                      │  Toplantısı │    konuşuyor!              │
│                      └─────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Collection Yapıları

### 1. `companies` - Firma Profilleri

Her tamamlanan rapor için firma profili saklanır.

```python
# Collection Config
{
    "collection_name": "companies",
    "vectors": {
        "size": 1024,           # qwen3-embedding-8b output
        "distance": "Cosine"
    }
}

# Point Yapısı
{
    "id": "report-uuid",
    "vector": [0.123, -0.456, ...],  # Firma profil embedding
    "payload": {
        # Temel Bilgiler
        "report_id": "550e8400-e29b-41d4-a716-446655440000",
        "company_name": "ABC Teknoloji A.Ş.",
        "company_tax_no": "1234567890",
        
        # Sonuçlar
        "final_score": 33,
        "risk_level": "orta_dusuk",
        "decision": "sartli_onay",
        "consensus": 0.85,
        
        # Firma Özellikleri (filtreleme için)
        "sector": "teknoloji",
        "city": "istanbul",
        "sermaye": 5000000,
        "kurulus_yili": 2018,
        "ortak_sayisi": 3,
        "calisan_sayisi": null,
        
        # Risk Faktörleri (embedding'e dahil)
        "risk_factors": [
            "yonetici_degisikligi",
            "sermaye_artisi",
            "vergi_yapilandirmasi"
        ],
        
        # Pozitif Faktörler
        "positive_factors": [
            "sermaye_artisi",
            "istihdam_artisi",
            "ihale_temiz"
        ],
        
        # Karar Detayları
        "conditions": ["6 aylık izleme", "bildirim covenant"],
        "dissent_note": "Risk analisti başlangıçta...",
        
        # Metadata
        "created_at": "2024-12-03T14:30:00Z",
        "version": 1
    }
}
```

**Embedding Oluşturma:**

```python
def create_company_embedding(report: Report) -> List[float]:
    """
    Firma profil metni oluştur ve embedding'e çevir.
    """
    profile_text = f"""
    Firma: {report.company_name}
    Sektör: {report.sector or 'bilinmiyor'}
    Sermaye: {report.sermaye} TL
    Kuruluş: {report.kurulus_yili}
    
    Risk Faktörleri: {', '.join(report.risk_factors)}
    Pozitif Faktörler: {', '.join(report.positive_factors)}
    
    Final Skor: {report.final_score}/100
    Karar: {report.decision}
    
    Özet: {report.decision_summary}
    """
    
    return embedding_service.embed(profile_text)
```

---

### 2. `patterns` - Risk Pattern'ları

Tekrar eden risk pattern'larını saklar.

```python
# Collection Config
{
    "collection_name": "patterns",
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    }
}

# Point Yapısı
{
    "id": "pattern-uuid",
    "vector": [0.123, -0.456, ...],  # Pattern embedding
    "payload": {
        # Pattern Tanımı
        "pattern_id": "PTN-001",
        "pattern_name": "Yönetici Sirkülasyonu Riski",
        "pattern_description": "Kısa sürede çok sayıda yönetici değişikliği",
        
        # Pattern Kriterleri
        "criteria": {
            "yonetici_degisikligi_sayisi": {"min": 3},
            "sure_ay": {"max": 12}
        },
        
        # İstatistikler
        "occurrence_count": 15,          # Kaç kez görüldü
        "avg_risk_score": 58.5,          # Ortalama risk skoru
        "high_risk_rate": 0.72,          # Yüksek risk oranı
        "rejection_rate": 0.28,          # Red oranı
        
        # Örnek Kararlar
        "sample_decisions": [
            {
                "report_id": "uuid-1",
                "company_name": "XYZ Ltd",
                "score": 65,
                "decision": "sartli_onay"
            },
            {
                "report_id": "uuid-2", 
                "company_name": "DEF A.Ş.",
                "score": 72,
                "decision": "red"
            }
        ],
        
        # Önerilen Aksiyonlar
        "recommended_conditions": [
            "6 aylık izleme periyodu",
            "Yönetim değişikliği bildirim covenant'ı"
        ],
        
        # Metadata
        "created_at": "2024-12-01T00:00:00Z",
        "updated_at": "2024-12-03T14:30:00Z",
        "is_active": true
    }
}
```

**Hazır Pattern'lar (Seed Data):**

```python
INITIAL_PATTERNS = [
    {
        "pattern_name": "Yönetici Sirkülasyonu Riski",
        "pattern_description": "12 ay içinde 3+ yönetici/müdür değişikliği",
        "criteria": {"yonetici_degisikligi": {"min": 3, "period_months": 12}},
        "avg_risk_score": 60,
        "high_risk_rate": 0.72
    },
    {
        "pattern_name": "Kurucu Çıkışı",
        "pattern_description": "Kurucu ortağın pay satışı veya tamamen çıkışı",
        "criteria": {"kurucu_pay_satisi": True},
        "avg_risk_score": 55,
        "high_risk_rate": 0.65
    },
    {
        "pattern_name": "Sermaye Erimesi",
        "pattern_description": "Sermaye azaltımı veya önemli pay devri",
        "criteria": {"sermaye_degisim": {"direction": "decrease"}},
        "avg_risk_score": 70,
        "high_risk_rate": 0.80
    },
    {
        "pattern_name": "Adres İstikrarsızlığı",
        "pattern_description": "Kısa sürede çoklu adres değişikliği",
        "criteria": {"adres_degisikligi": {"min": 2, "period_months": 12}},
        "avg_risk_score": 45,
        "high_risk_rate": 0.40
    },
    {
        "pattern_name": "Vergi Yapılandırması",
        "pattern_description": "Vergi borcu yapılandırması geçmişi",
        "criteria": {"vergi_yapilandirmasi": True},
        "avg_risk_score": 50,
        "high_risk_rate": 0.55
    },
    {
        "pattern_name": "Büyüme Sinyali",
        "pattern_description": "Sermaye artışı + istihdam artışı kombinasyonu",
        "criteria": {"sermaye_artisi": True, "istihdam_artisi": True},
        "avg_risk_score": 25,
        "high_risk_rate": 0.15
    },
    {
        "pattern_name": "İhale Yasağı Geçmişi",
        "pattern_description": "Geçmişte ihale yasağı almış firma",
        "criteria": {"ihale_yasagi_gecmis": True},
        "avg_risk_score": 65,
        "high_risk_rate": 0.70
    },
    {
        "pattern_name": "Negatif Medya Trendi",
        "pattern_description": "Son dönemde artan olumsuz haberler",
        "criteria": {"negatif_haber_trend": "increasing"},
        "avg_risk_score": 55,
        "high_risk_rate": 0.60
    }
]
```

---

### 3. `council_decisions` - Council Hafızası

Her Council üyesinin geçmiş kararları ve gerekçeleri.

```python
# Collection Config
{
    "collection_name": "council_decisions",
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    }
}

# Point Yapısı
{
    "id": "decision-uuid",
    "vector": [0.123, -0.456, ...],  # Karar context embedding
    "payload": {
        # İlişkiler
        "report_id": "550e8400-e29b-41d4-a716-446655440000",
        "company_name": "ABC Teknoloji A.Ş.",
        
        # Council Üyesi
        "member_id": "risk_analyst",
        "member_name": "Mehmet Bey",
        
        # Karar
        "initial_score": 65,
        "final_score": 45,
        "was_revised": true,
        
        # Gerekçe (embedding'in ana kaynağı)
        "rationale": "8 ayda 3 yönetici değişikliği ciddi risk. Ancak tartışmada sermaye artışı ve yatırımcı girişi pozitif değerlendirildi. İzleme şartıyla skoru revize ediyorum.",
        
        # Anahtar Noktalar
        "key_concerns": [
            "yonetici_sirkülasyonu",
            "pay_devri"
        ],
        "key_positives": [
            "sermaye_artisi",
            "yatirimci_girisi"
        ],
        
        # Bağlam
        "context_factors": {
            "sector": "teknoloji",
            "sermaye": 5000000,
            "yonetici_degisikligi_sayisi": 3
        },
        
        # Metadata
        "created_at": "2024-12-03T15:00:00Z"
    }
}
```

**Embedding Oluşturma:**

```python
def create_decision_embedding(decision: CouncilMemberDecision) -> List[float]:
    """
    Council üyesi kararı için embedding.
    Benzer bağlamlarda nasıl karar verdiğini bulmak için kullanılır.
    """
    context_text = f"""
    Firma tipi: {decision.sector}, sermaye {decision.sermaye} TL
    
    Risk faktörleri: {', '.join(decision.key_concerns)}
    Pozitif faktörler: {', '.join(decision.key_positives)}
    
    {decision.member_name} değerlendirmesi:
    {decision.rationale}
    
    Skor: {decision.final_score}/100
    """
    
    return embedding_service.embed(context_text)
```

---

## 🔤 Embedding Stratejisi

### Model

```yaml
Model: qwen3-embedding-8b
Dimension: 1024
Max Tokens: 8192
Endpoint: KKB Kloudeks API
```

### Batch İşleme

```python
class EmbeddingService:
    def __init__(self):
        self.model = "qwen3-embedding-8b"
        self.batch_size = 16
        
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding - rate limit friendly"""
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = await self.llm_client.embed(batch, model=self.model)
            results.extend(embeddings)
            await asyncio.sleep(0.1)  # Rate limit
        return results
    
    async def embed(self, text: str) -> List[float]:
        """Tek metin embedding"""
        result = await self.llm_client.embed([text], model=self.model)
        return result[0]
```

### Text Preprocessing

```python
def preprocess_for_embedding(text: str) -> str:
    """
    Embedding öncesi metin temizleme.
    """
    # Türkçe karakterleri koru
    text = text.strip()
    
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    
    # Çok uzunsa kes (model limiti)
    if len(text) > 6000:
        text = text[:6000] + "..."
    
    return text
```

---

## 🎬 Kullanım Senaryoları

### Senaryo 1: Benzer Firma Bulma

```
┌─────────────────────────────────────────────────────────────────┐
│  ZAMAN: Rapor başlatıldığında, agent'lar çalışmaya başlamadan  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT: Firma adı "ABC Teknoloji A.Ş."                         │
│                                                                 │
│  SÜREÇ:                                                         │
│  1. Firma adını embed et                                       │
│  2. companies collection'da ara                                │
│  3. Top 3 benzer firmayı getir                                 │
│  4. Context'e ekle                                             │
│                                                                 │
│  OUTPUT:                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Benzer Firmalar:                                        │  │
│  │                                                          │  │
│  │  1. XYZ Yazılım Ltd. (%87 benzerlik)                    │  │
│  │     Skor: 42 | Karar: Şartlı Onay                       │  │
│  │     Risk: Yönetici değişikliği                          │  │
│  │                                                          │  │
│  │  2. DEF Tech A.Ş. (%76 benzerlik)                       │  │
│  │     Skor: 28 | Karar: Onay                              │  │
│  │     Pozitif: Sermaye artışı                             │  │
│  │                                                          │  │
│  │  3. GHI Digital (%71 benzerlik)                         │  │
│  │     Skor: 58 | Karar: Şartlı Onay                       │  │
│  │     Risk: Adres değişikliği                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  KULLANIM: Council prompt'una eklenir                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Senaryo 2: Risk Pattern Eşleştirme

```
┌─────────────────────────────────────────────────────────────────┐
│  ZAMAN: Agent verileri toplandıktan sonra, Council öncesi      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT: Agent sonuçlarından çıkarılan faktörler                │
│  - yonetici_degisikligi: 3 (son 8 ay)                          │
│  - sermaye_artisi: true                                        │
│  - vergi_yapilandirmasi: true (geçmişte)                       │
│                                                                 │
│  SÜREÇ:                                                         │
│  1. Faktörleri pattern text'ine çevir                          │
│  2. patterns collection'da ara                                 │
│  3. Eşleşen pattern'ları getir                                 │
│  4. İstatistikleri hazırla                                     │
│                                                                 │
│  OUTPUT:                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Eşleşen Pattern'lar:                                    │  │
│  │                                                          │  │
│  │  ⚠️ "Yönetici Sirkülasyonu Riski" (%92 eşleşme)         │  │
│  │     Görülme: 15 firmada                                  │  │
│  │     Ortalama skor: 58.5                                  │  │
│  │     Yüksek risk oranı: %72                               │  │
│  │     Önerilen: 6 aylık izleme                             │  │
│  │                                                          │  │
│  │  ℹ️ "Vergi Yapılandırması" (%78 eşleşme)                │  │
│  │     Görülme: 23 firmada                                  │  │
│  │     Ortalama skor: 50                                    │  │
│  │     Yüksek risk oranı: %55                               │  │
│  │     Not: Tamamlanmışsa risk azalır                       │  │
│  │                                                          │  │
│  │  ✅ "Büyüme Sinyali" (%65 eşleşme)                       │  │
│  │     Görülme: 31 firmada                                  │  │
│  │     Ortalama skor: 25                                    │  │
│  │     Düşük risk oranı: %85                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  KULLANIM: Her Council üyesine pattern context'i verilir       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Senaryo 3: Council Tutarlılık Kontrolü

```
┌─────────────────────────────────────────────────────────────────┐
│  ZAMAN: Council üyesi konuşmadan hemen önce                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT: Mevcut firma bağlamı + Council üyesi ID                │
│                                                                 │
│  SÜREÇ:                                                         │
│  1. Mevcut bağlamı embed et                                    │
│  2. council_decisions'da bu üyenin kararlarını ara             │
│  3. Benzer bağlamdaki kararları getir                          │
│  4. Tutarlılık için prompt'a ekle                              │
│                                                                 │
│  OUTPUT (Mehmet Bey için):                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Geçmiş Benzer Kararların:                               │  │
│  │                                                          │  │
│  │  📋 XYZ Yazılım Ltd. (2 hafta önce)                      │  │
│  │     Bağlam: Teknoloji, 3 yönetici değişikliği            │  │
│  │     Senin skoran: 45                                     │  │
│  │     Gerekçen: "Yönetici değişikliği endişe verici        │  │
│  │     ama yatırımcı girişi dengeliyor"                     │  │
│  │                                                          │  │
│  │  📋 DEF Tech A.Ş. (1 ay önce)                            │  │
│  │     Bağlam: Teknoloji, 2 yönetici değişikliği            │  │
│  │     Senin skoran: 35                                     │  │
│  │     Gerekçen: "Değişiklikler planlı görünüyor"           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  KULLANIM: Üyenin system prompt'una eklenir                    │
│  AMAÇ: Benzer durumlarda tutarlı skor vermesini sağla          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Query Örnekleri

### Python Client

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

client = QdrantClient(host="localhost", port=6333)
```

### 1. Benzer Firma Arama

```python
async def find_similar_companies(
    company_embedding: List[float],
    limit: int = 3,
    min_score: float = 0.7
) -> List[dict]:
    """
    Benzer firmaları bul.
    """
    results = client.search(
        collection_name="companies",
        query_vector=company_embedding,
        limit=limit,
        score_threshold=min_score
    )
    
    return [
        {
            "company_name": r.payload["company_name"],
            "similarity": r.score,
            "final_score": r.payload["final_score"],
            "decision": r.payload["decision"],
            "risk_factors": r.payload["risk_factors"],
            "report_id": r.payload["report_id"]
        }
        for r in results
    ]
```

### 2. Pattern Eşleştirme

```python
async def match_risk_patterns(
    factors_embedding: List[float],
    limit: int = 5
) -> List[dict]:
    """
    Risk faktörlerine uyan pattern'ları bul.
    """
    results = client.search(
        collection_name="patterns",
        query_vector=factors_embedding,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="is_active",
                    match=MatchValue(value=True)
                )
            ]
        )
    )
    
    return [
        {
            "pattern_name": r.payload["pattern_name"],
            "match_score": r.score,
            "avg_risk_score": r.payload["avg_risk_score"],
            "high_risk_rate": r.payload["high_risk_rate"],
            "occurrence_count": r.payload["occurrence_count"],
            "recommended_conditions": r.payload["recommended_conditions"]
        }
        for r in results
    ]
```

### 3. Council Üyesi Geçmiş Kararları

```python
async def get_member_past_decisions(
    context_embedding: List[float],
    member_id: str,
    limit: int = 3
) -> List[dict]:
    """
    Council üyesinin benzer bağlamdaki geçmiş kararlarını bul.
    """
    results = client.search(
        collection_name="council_decisions",
        query_vector=context_embedding,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="member_id",
                    match=MatchValue(value=member_id)
                )
            ]
        )
    )
    
    return [
        {
            "company_name": r.payload["company_name"],
            "similarity": r.score,
            "initial_score": r.payload["initial_score"],
            "final_score": r.payload["final_score"],
            "rationale": r.payload["rationale"],
            "key_concerns": r.payload["key_concerns"]
        }
        for r in results
    ]
```

### 4. Filtrelenmiş Arama (Sektör + Risk Level)

```python
async def find_similar_in_sector(
    company_embedding: List[float],
    sector: str,
    min_risk_score: int = 50
) -> List[dict]:
    """
    Aynı sektörde yüksek riskli benzer firmaları bul.
    """
    results = client.search(
        collection_name="companies",
        query_vector=company_embedding,
        limit=5,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="sector",
                    match=MatchValue(value=sector)
                ),
                FieldCondition(
                    key="final_score",
                    range=Range(gte=min_risk_score)
                )
            ]
        )
    )
    
    return results
```

---

## 🔗 Entegrasyon Noktaları

### 1. Rapor Başlatıldığında

```python
# orchestrator.py

async def start_report(company_name: str) -> str:
    report_id = create_report(company_name)
    
    # Benzer firma ara (async, agent'larla paralel)
    similar_companies = await vector_service.find_similar_companies(
        company_name=company_name
    )
    
    # Context'e kaydet
    await context_store.set(report_id, "similar_companies", similar_companies)
    
    # Agent'ları başlat
    await start_agents(report_id, company_name)
    
    return report_id
```

### 2. Agent'lar Tamamlandığında

```python
# orchestrator.py

async def on_agents_complete(report_id: str, results: dict):
    # Risk faktörlerini çıkar
    risk_factors = extract_risk_factors(results)
    
    # Pattern eşleştir
    matched_patterns = await vector_service.match_patterns(risk_factors)
    
    # Context'e kaydet
    await context_store.set(report_id, "matched_patterns", matched_patterns)
    
    # Council'ı başlat
    await start_council(report_id)
```

### 3. Council Üyesi Konuşmadan Önce

```python
# council_service.py

async def prepare_member_context(
    report_id: str,
    member_id: str,
    current_context: dict
) -> dict:
    # Üyenin geçmiş kararlarını getir
    past_decisions = await vector_service.get_member_past_decisions(
        context=current_context,
        member_id=member_id
    )
    
    # Benzer firma ve pattern bilgilerini al
    similar_companies = await context_store.get(report_id, "similar_companies")
    matched_patterns = await context_store.get(report_id, "matched_patterns")
    
    return {
        "past_decisions": past_decisions,
        "similar_companies": similar_companies,
        "matched_patterns": matched_patterns
    }
```

### 4. Rapor Tamamlandığında

```python
# orchestrator.py

async def on_report_complete(report_id: str):
    report = await get_report(report_id)
    
    # Firma profilini kaydet
    await vector_service.upsert_company(report)
    
    # Council kararlarını kaydet
    for member_decision in report.council_decision.member_decisions:
        await vector_service.upsert_council_decision(member_decision)
    
    # Pattern istatistiklerini güncelle
    await vector_service.update_pattern_stats(report)
```

---

## 📊 Council Prompt Örneği

```python
RISK_ANALYST_PROMPT_WITH_CONTEXT = """
Sen Mehmet Bey'sin - 25 yıllık deneyimli bir Risk Analisti.

## Mevcut Firma
{company_name}
Sektör: {sector}
Sermaye: {sermaye} TL

## Benzer Firmalar (Kurumsal Hafıza)
{similar_companies_context}

## Eşleşen Risk Pattern'ları
{matched_patterns_context}

## Senin Geçmiş Benzer Kararların
{past_decisions_context}

## Agent Verileri
{agent_data}

---

Değerlendirmeni yap. Geçmiş kararlarınla tutarlı ol.
Benzer firmalara ve pattern'lara referans verebilirsin - bunlar gerçek veriler.

Örnek: "XYZ Ltd'de benzer yönetici değişikliği vardı, orada 45 puan vermiştim..."
"""
```

---

## 🚀 Kurulum

### Docker Compose

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

volumes:
  qdrant_data:
```

### Collection Oluşturma

```python
# scripts/init_qdrant.py

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(host="localhost", port=6333)

# Companies collection
client.create_collection(
    collection_name="companies",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)

# Patterns collection
client.create_collection(
    collection_name="patterns",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)

# Council decisions collection
client.create_collection(
    collection_name="council_decisions",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)

print("✅ Collections created!")
```

### Seed Data (Pattern'lar)

```python
# scripts/seed_patterns.py

async def seed_patterns():
    for pattern in INITIAL_PATTERNS:
        embedding = await embedding_service.embed(
            f"{pattern['pattern_name']}: {pattern['pattern_description']}"
        )
        
        client.upsert(
            collection_name="patterns",
            points=[{
                "id": str(uuid4()),
                "vector": embedding,
                "payload": pattern
            }]
        )
    
    print(f"✅ {len(INITIAL_PATTERNS)} patterns seeded!")
```

---

## 📈 MVP Sonrası Geliştirmeler

| Özellik | Açıklama |
|---------|----------|
| **Otomatik Pattern Öğrenme** | Yeni kararlardan otomatik pattern çıkarma |
| **Anomali Tespiti** | Geçmişten çok farklı kararları işaretle |
| **Sektör Benchmark** | Sektör bazlı ortalama risk skorları |
| **Trend Analizi** | Firma risk trendini zamanla takip |
| **Cluster Görselleştirme** | Benzer firmaları haritada göster |

---

<div align="center">

**🧠 Kurumsal Hafıza: Gerçek Veriler, Sıfır Halüsinasyon**

"Her karar hatırlanır, her pattern öğrenilir, her firma karşılaştırılır."

**Son Güncelleme:** 3 Aralık 2024

**Owner:** Yamaç

</div>
