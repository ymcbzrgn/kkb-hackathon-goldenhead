# 🗄️ Database Şeması

> Esnek, Migration-Friendly Veritabanı Tasarımı
>
> ⚠️ **Bu şema MVP ve sonrası için tasarlandı.** Reserved kolonlar ve JSONB alanları sayesinde production'da migration yapmadan yeni özellikler eklenebilir.

---

## 📋 İçindekiler

- [Tasarım Prensipleri](#-tasarım-prensipleri)
- [ER Diyagramı](#-er-diyagramı)
- [Tablolar](#-tablolar)
- [Index'ler](#-indexler)
- [Enum Değerleri](#-enum-değerleri)
- [Örnek Sorgular](#-örnek-sorgular)
- [Migration Notları](#-migration-notları)
- [Bartın İçin Kurulum](#-bartın-için-kurulum)

---

## 🎯 Tasarım Prensipleri

### 1. JSONB Her Yerde
```
Sabit yapı    → Kolon olarak (company_name, status)
Değişken yapı → JSONB olarak (agent verileri, transcript)
```

### 2. Reserved Kolonlar
Her tabloda kullanılmayan ama ileride lazım olabilecek kolonlar:
```
reserved_text_1, reserved_text_2, reserved_text_3  → TEXT
reserved_int_1, reserved_int_2                     → INTEGER
reserved_bool_1                                    → BOOLEAN
reserved_json                                      → JSONB
```

### 3. Soft Delete
```
deleted_at TIMESTAMP → NULL ise aktif, dolu ise silinmiş
```

### 4. Audit Fields
```
created_at TIMESTAMP → Oluşturulma zamanı
updated_at TIMESTAMP → Son güncelleme zamanı
```

### 5. Versiyonlama
```
Aynı firma için birden fazla rapor → version numarası ile takip
```

---

## 📊 ER Diyagramı

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │   categories    │         │          reports            │   │
│  │─────────────────│         │─────────────────────────────│   │
│  │ id (PK)         │◄───────┐│ id (PK)                     │   │
│  │ name            │        ││ company_name                │   │
│  │ color           │        ││ company_tax_no              │   │
│  │ description     │        ││ category_id (FK) ───────────┘   │
│  └─────────────────┘        ││ version                     │   │
│                             ││ status                      │   │
│                             ││ ...                         │   │
│                             │└──────────────┬──────────────┘   │
│                             │               │                  │
│                             │               │ 1:N              │
│                             │               │                  │
│               ┌─────────────┴───────────────┼──────────────┐   │
│               │                             │              │   │
│               ▼                             ▼              ▼   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────┐
│  │   agent_results     │  │ council_decisions   │  │    tags       │
│  │─────────────────────│  │─────────────────────│  │───────────────│
│  │ id (PK)             │  │ id (PK)             │  │ id (PK)       │
│  │ report_id (FK)      │  │ report_id (FK)      │  │ report_id(FK) │
│  │ agent_type          │  │ final_score         │  │ tag_name      │
│  │ raw_data (JSONB)    │  │ transcript (JSONB)  │  │               │
│  │ ...                 │  │ ...                 │  │               │
│  └─────────────────────┘  └─────────────────────┘  └───────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Tablolar

### 1. `reports` - Ana Rapor Tablosu

```sql
CREATE TABLE reports (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Firma Bilgileri
    company_name        VARCHAR(500) NOT NULL,
    company_tax_no      VARCHAR(20),
    company_trade_name  VARCHAR(500),              -- Ticari unvan (farklıysa)
    company_address     TEXT,
    company_city        VARCHAR(100),
    company_district    VARCHAR(100),
    
    -- Versiyon & Kategori
    version             INTEGER DEFAULT 1,          -- Aynı firma için versiyon
    category_id         UUID REFERENCES categories(id),
    priority            VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    
    -- Durum
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    status_message      TEXT,                       -- Hata mesajı veya durum açıklaması
    progress            INTEGER DEFAULT 0,          -- 0-100 ilerleme yüzdesi
    
    -- Sonuçlar
    final_score         INTEGER,                    -- 0-100
    risk_level          VARCHAR(20),                -- dusuk, orta_dusuk, orta, orta_yuksek, yuksek
    decision            VARCHAR(30),                -- onay, sartli_onay, red, inceleme_gerek
    decision_summary    TEXT,                       -- Kısa karar özeti
    
    -- Süre Bilgileri
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    duration_seconds    INTEGER,
    
    -- Notlar
    internal_notes      TEXT,                       -- İç notlar
    external_notes      TEXT,                       -- Dış notlar / müşteriye gösterilebilir
    
    -- Metadata (esnek alan)
    metadata            JSONB DEFAULT '{}',
    /*
        metadata örnek içerik:
        {
            "source": "web",
            "requested_by": "Ali Veli",
            "department": "Kredi",
            "reference_no": "KRD-2024-001",
            "custom_fields": { ... }
        }
    */
    
    -- Reserved Kolonlar (ileride kullanım için)
    reserved_text_1     TEXT,
    reserved_text_2     TEXT,
    reserved_text_3     TEXT,
    reserved_int_1      INTEGER,
    reserved_int_2      INTEGER,
    reserved_bool_1     BOOLEAN,
    reserved_json       JSONB,
    
    -- Audit Fields
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at          TIMESTAMP WITH TIME ZONE,   -- Soft delete
    
    -- Constraints
    CONSTRAINT valid_score CHECK (final_score IS NULL OR (final_score >= 0 AND final_score <= 100)),
    CONSTRAINT valid_progress CHECK (progress >= 0 AND progress <= 100)
);

-- Yorum
COMMENT ON TABLE reports IS 'Ana rapor tablosu - firma istihbarat raporları';
COMMENT ON COLUMN reports.version IS 'Aynı firma için birden fazla rapor olduğunda versiyon numarası';
COMMENT ON COLUMN reports.metadata IS 'Esnek JSON alan - source, requested_by, custom_fields vb.';
COMMENT ON COLUMN reports.reserved_text_1 IS 'İleride kullanım için rezerve edilmiş TEXT alan';
```

---

### 2. `agent_results` - Agent Sonuçları

```sql
CREATE TABLE agent_results (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- İlişki
    report_id           UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Agent Bilgileri
    agent_type          VARCHAR(30) NOT NULL,       -- tsg_agent, ihale_agent, news_agent
    agent_version       VARCHAR(20) DEFAULT '1.0',  -- Agent versiyonu
    
    -- Durum
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    status_message      TEXT,
    progress            INTEGER DEFAULT 0,
    retry_count         INTEGER DEFAULT 0,          -- Kaç kez denendi
    
    -- Veriler
    raw_data            JSONB,                      -- Ham veri (scrape edildiği gibi)
    processed_data      JSONB,                      -- İşlenmiş veri (yapılandırılmış)
    /*
        TSG processed_data örnek:
        {
            "kurulus_tarihi": "2018-03-15",
            "sermaye": 5000000,
            "ortaklar": [...],
            "yonetim_kurulu": [...],
            ...
        }
        
        News processed_data örnek:
        {
            "toplam_haber": 24,
            "pozitif": 15,
            "negatif": 4,
            "sentiment_score": 0.62,
            "onemli_haberler": [...]
        }
    */
    
    -- Özet (hızlı erişim için)
    summary             TEXT,                       -- Agent sonuç özeti
    key_findings        JSONB DEFAULT '[]',         -- ["Sermaye artışı", "Yönetici değişikliği"]
    warning_flags       JSONB DEFAULT '[]',         -- ["Vergi yapılandırması", "İhale yasağı geçmişi"]
    
    -- Performans
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    duration_seconds    INTEGER,
    
    -- Kaynak Bilgileri
    source_urls         JSONB DEFAULT '[]',         -- Taranan URL'ler
    source_count        INTEGER,                    -- Kaç kaynak tarandı
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Reserved Kolonlar
    reserved_text_1     TEXT,
    reserved_text_2     TEXT,
    reserved_text_3     TEXT,
    reserved_int_1      INTEGER,
    reserved_int_2      INTEGER,
    reserved_bool_1     BOOLEAN,
    reserved_json       JSONB,
    
    -- Audit Fields
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at          TIMESTAMP WITH TIME ZONE,
    
    -- Unique constraint: Her rapor için her agent tipi bir kez
    CONSTRAINT unique_agent_per_report UNIQUE (report_id, agent_type)
);

COMMENT ON TABLE agent_results IS 'Her agent''ın topladığı veriler ve sonuçları';
COMMENT ON COLUMN agent_results.raw_data IS 'Ham scrape verisi - debug için saklanır';
COMMENT ON COLUMN agent_results.processed_data IS 'İşlenmiş, yapılandırılmış veri - API''de döndürülür';
```

---

### 3. `council_decisions` - Komite Kararları

```sql
CREATE TABLE council_decisions (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- İlişki
    report_id           UUID NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Skorlar
    final_score         INTEGER NOT NULL,
    risk_level          VARCHAR(20) NOT NULL,
    decision            VARCHAR(30) NOT NULL,
    consensus           DECIMAL(3,2),               -- 0.00 - 1.00 arası
    score_variance      DECIMAL(5,2),               -- Skorlar arası varyans
    
    -- Bireysel Skorlar
    initial_scores      JSONB NOT NULL,
    /*
        {
            "risk_analyst": 65,
            "business_analyst": 25,
            "legal_expert": 30,
            "media_analyst": 30,
            "sector_expert": 35
        }
    */
    final_scores        JSONB NOT NULL,
    /*
        {
            "risk_analyst": 45,  // revize edildi
            "business_analyst": 25,
            "legal_expert": 30,
            "media_analyst": 30,
            "sector_expert": 35
        }
    */
    
    -- Revizyon Bilgileri
    revisions           JSONB DEFAULT '[]',
    /*
        [
            {
                "member_id": "risk_analyst",
                "old_score": 65,
                "new_score": 45,
                "reason": "Tartışmada yeni bilgiler öğrendim",
                "timestamp": "2024-12-03T15:00:00Z"
            }
        ]
    */
    
    -- Karar Detayları
    conditions          JSONB DEFAULT '[]',         -- ["6 aylık izleme", "Covenant"]
    dissent_note        TEXT,                       -- Muhalefet notu
    decision_rationale  TEXT,                       -- Karar gerekçesi (uzun)
    
    -- Transcript (tüm konuşmalar)
    transcript          JSONB NOT NULL,
    /*
        [
            {
                "timestamp": "2024-12-03T14:32:00Z",
                "phase": "opening",
                "speaker_id": "moderator",
                "speaker_name": "GMY",
                "content": "Toplantıyı açıyorum...",
                "risk_score": null
            },
            ...
        ]
    */
    
    -- Süre
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    duration_seconds    INTEGER,
    
    -- Faz Bilgileri
    phases_completed    JSONB DEFAULT '{}',
    /*
        {
            "opening": {"duration": 120, "completed_at": "..."},
            "presentation": {"duration": 900, "completed_at": "..."},
            "discussion": {"duration": 900, "completed_at": "..."},
            "decision": {"duration": 300, "completed_at": "..."}
        }
    */
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Reserved Kolonlar
    reserved_text_1     TEXT,
    reserved_text_2     TEXT,
    reserved_text_3     TEXT,
    reserved_int_1      INTEGER,
    reserved_int_2      INTEGER,
    reserved_bool_1     BOOLEAN,
    reserved_json       JSONB,
    
    -- Audit Fields
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at          TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_council_score CHECK (final_score >= 0 AND final_score <= 100),
    CONSTRAINT valid_consensus CHECK (consensus >= 0 AND consensus <= 1)
);

COMMENT ON TABLE council_decisions IS 'Komite toplantı kararları ve transcript';
COMMENT ON COLUMN council_decisions.transcript IS 'Tüm toplantı konuşmalarının JSON kaydı';
COMMENT ON COLUMN council_decisions.revisions IS 'Tartışma sırasında yapılan skor revizyonları';
```

---

### 4. `categories` - Kategoriler

```sql
CREATE TABLE categories (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Temel Bilgiler
    name                VARCHAR(100) NOT NULL UNIQUE,
    slug                VARCHAR(100) NOT NULL UNIQUE, -- URL-friendly isim
    description         TEXT,
    color               VARCHAR(7) DEFAULT '#6B7280', -- Hex renk kodu
    icon                VARCHAR(50),                  -- Icon adı (lucide-react)
    
    -- Hiyerarşi (ileride kullanım için)
    parent_id           UUID REFERENCES categories(id),
    sort_order          INTEGER DEFAULT 0,
    
    -- Durum
    is_active           BOOLEAN DEFAULT true,
    is_default          BOOLEAN DEFAULT false,        -- Varsayılan kategori mi
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Reserved Kolonlar
    reserved_text_1     TEXT,
    reserved_text_2     TEXT,
    reserved_int_1      INTEGER,
    reserved_bool_1     BOOLEAN,
    reserved_json       JSONB,
    
    -- Audit Fields
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at          TIMESTAMP WITH TIME ZONE
);

-- Varsayılan kategoriler
INSERT INTO categories (id, name, slug, description, color, icon, is_default) VALUES
    (gen_random_uuid(), 'Genel', 'genel', 'Genel firma raporları', '#6B7280', 'file-text', true),
    (gen_random_uuid(), 'Kredi', 'kredi', 'Kredi değerlendirme raporları', '#3B82F6', 'credit-card', false),
    (gen_random_uuid(), 'Tedarikçi', 'tedarikci', 'Tedarikçi değerlendirme raporları', '#10B981', 'truck', false),
    (gen_random_uuid(), 'Müşteri', 'musteri', 'Müşteri değerlendirme raporları', '#F59E0B', 'users', false),
    (gen_random_uuid(), 'Yatırım', 'yatirim', 'Yatırım değerlendirme raporları', '#8B5CF6', 'trending-up', false);

COMMENT ON TABLE categories IS 'Rapor kategorileri';
```

---

### 5. `report_tags` - Etiketler (Many-to-Many)

```sql
CREATE TABLE report_tags (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- İlişkiler
    report_id           UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Etiket
    tag_name            VARCHAR(100) NOT NULL,
    tag_color           VARCHAR(7) DEFAULT '#6B7280',
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Audit Fields
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint: Aynı rapor + aynı tag bir kez
    CONSTRAINT unique_tag_per_report UNIQUE (report_id, tag_name)
);

-- Index
CREATE INDEX idx_report_tags_tag_name ON report_tags(tag_name);
CREATE INDEX idx_report_tags_report_id ON report_tags(report_id);

COMMENT ON TABLE report_tags IS 'Raporlara atanan etiketler';
```

---

### 6. `activity_logs` - Aktivite Logları (Opsiyonel ama Faydalı)

```sql
CREATE TABLE activity_logs (
    -- Primary Key
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- İlişki
    report_id           UUID REFERENCES reports(id) ON DELETE SET NULL,
    
    -- Aktivite Bilgileri
    action              VARCHAR(50) NOT NULL,       -- created, updated, completed, failed, deleted
    entity_type         VARCHAR(50) NOT NULL,       -- report, agent, council
    entity_id           UUID,
    
    -- Detaylar
    description         TEXT,
    old_value           JSONB,                      -- Değişiklik öncesi
    new_value           JSONB,                      -- Değişiklik sonrası
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    ip_address          VARCHAR(45),
    user_agent          TEXT,
    
    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index (zaman bazlı sorgular için)
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_report_id ON activity_logs(report_id);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

COMMENT ON TABLE activity_logs IS 'Sistem aktivite logları - audit trail';
```

---

## 🔍 Index'ler

```sql
-- Reports tablosu
CREATE INDEX idx_reports_status ON reports(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_reports_company_name ON reports(company_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_reports_company_tax_no ON reports(company_tax_no) WHERE deleted_at IS NULL AND company_tax_no IS NOT NULL;
CREATE INDEX idx_reports_created_at ON reports(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_reports_category_id ON reports(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_reports_risk_level ON reports(risk_level) WHERE deleted_at IS NULL AND risk_level IS NOT NULL;
CREATE INDEX idx_reports_decision ON reports(decision) WHERE deleted_at IS NULL AND decision IS NOT NULL;

-- Versiyon sorguları için composite index
CREATE INDEX idx_reports_company_version ON reports(company_name, version DESC) WHERE deleted_at IS NULL;

-- JSONB index (metadata içinde arama için)
CREATE INDEX idx_reports_metadata ON reports USING GIN(metadata);

-- Agent Results tablosu
CREATE INDEX idx_agent_results_report_id ON agent_results(report_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agent_results_status ON agent_results(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_agent_results_agent_type ON agent_results(agent_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_agent_results_processed_data ON agent_results USING GIN(processed_data);

-- Council Decisions tablosu
CREATE INDEX idx_council_decisions_report_id ON council_decisions(report_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_council_decisions_risk_level ON council_decisions(risk_level) WHERE deleted_at IS NULL;
CREATE INDEX idx_council_decisions_decision ON council_decisions(decision) WHERE deleted_at IS NULL;
```

---

## 📋 Enum Değerleri

### ReportStatus
| Değer | Açıklama |
|-------|----------|
| `pending` | Oluşturuldu, henüz başlamadı |
| `processing` | İşleniyor |
| `completed` | Tamamlandı |
| `failed` | Hata ile sonlandı |
| `cancelled` | İptal edildi |

### RiskLevel
| Değer | Skor Aralığı | Renk |
|-------|--------------|------|
| `dusuk` | 0-30 | 🟢 Yeşil |
| `orta_dusuk` | 31-45 | 🟡 Açık Yeşil |
| `orta` | 46-60 | 🟠 Sarı |
| `orta_yuksek` | 61-75 | 🟠 Turuncu |
| `yuksek` | 76-100 | 🔴 Kırmızı |

### Decision
| Değer | Açıklama |
|-------|----------|
| `onay` | Koşulsuz onay |
| `sartli_onay` | Şartlı onay |
| `red` | Red |
| `inceleme_gerek` | Daha fazla inceleme gerekli |

### AgentType
| Değer | Açıklama |
|-------|----------|
| `tsg_agent` | Ticaret Sicili Gazetesi |
| `ihale_agent` | İhale/EKAP |
| `news_agent` | Haber Analizi |

### Priority
| Değer | Açıklama |
|-------|----------|
| `low` | Düşük öncelik |
| `normal` | Normal öncelik |
| `high` | Yüksek öncelik |
| `urgent` | Acil |

---

## 💡 Örnek Sorgular

### Aktif raporları listele
```sql
SELECT * FROM reports 
WHERE deleted_at IS NULL 
ORDER BY created_at DESC 
LIMIT 10;
```

### Firma için son raporu getir
```sql
SELECT * FROM reports 
WHERE company_name = 'ABC Teknoloji A.Ş.' 
  AND deleted_at IS NULL 
ORDER BY version DESC 
LIMIT 1;
```

### Firma için tüm versiyonları getir
```sql
SELECT id, company_name, version, status, final_score, created_at 
FROM reports 
WHERE company_name = 'ABC Teknoloji A.Ş.' 
  AND deleted_at IS NULL 
ORDER BY version DESC;
```

### Kategoriye göre rapor sayısı
```sql
SELECT c.name, COUNT(r.id) as report_count
FROM categories c
LEFT JOIN reports r ON r.category_id = c.id AND r.deleted_at IS NULL
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.name
ORDER BY report_count DESC;
```

### Yüksek riskli raporlar
```sql
SELECT r.*, cd.final_score, cd.decision
FROM reports r
JOIN council_decisions cd ON cd.report_id = r.id
WHERE r.deleted_at IS NULL
  AND cd.risk_level IN ('yuksek', 'orta_yuksek')
ORDER BY cd.final_score DESC;
```

### Agent bazlı hata analizi
```sql
SELECT agent_type, status, COUNT(*) as count
FROM agent_results
WHERE deleted_at IS NULL
GROUP BY agent_type, status
ORDER BY agent_type, status;
```

### Tag ile rapor arama
```sql
SELECT r.*
FROM reports r
JOIN report_tags rt ON rt.report_id = r.id
WHERE rt.tag_name = 'acil-inceleme'
  AND r.deleted_at IS NULL;
```

### Rapor + tüm ilişkili veriler (full join)
```sql
SELECT 
    r.*,
    json_agg(DISTINCT ar.*) FILTER (WHERE ar.id IS NOT NULL) as agent_results,
    cd.*
FROM reports r
LEFT JOIN agent_results ar ON ar.report_id = r.id AND ar.deleted_at IS NULL
LEFT JOIN council_decisions cd ON cd.report_id = r.id AND cd.deleted_at IS NULL
WHERE r.id = 'uuid-here'
  AND r.deleted_at IS NULL
GROUP BY r.id, cd.id;
```

---

## 🔄 Migration Notları

### Reserved Kolonları Kullanma

İleride yeni bir alan lazım olduğunda:

```sql
-- YAPMA ❌
ALTER TABLE reports ADD COLUMN new_field TEXT;

-- YAP ✅
-- 1. reserved_text_1'i kullan
-- 2. Sadece bir comment ekle
COMMENT ON COLUMN reports.reserved_text_1 IS 'Artık customer_reference olarak kullanılıyor';
```

### Metadata JSONB Kullanma

```sql
-- Yeni alanları metadata içine ekle
UPDATE reports 
SET metadata = metadata || '{"new_feature": "value"}'::jsonb
WHERE id = 'uuid';

-- Sorgula
SELECT * FROM reports 
WHERE metadata->>'new_feature' = 'value';
```

### Esneklik Kuralları

| Durum | Çözüm |
|-------|-------|
| Yeni basit alan lazım | Reserved kolonlardan birini kullan |
| Yeni karmaşık veri lazım | metadata JSONB içine ekle |
| Yeni ilişki lazım | reserved_json içinde ID tut |
| Enum'a yeni değer lazım | VARCHAR olduğu için direkt ekle |

---

## 🚀 Bartın İçin Kurulum

### 1. PostgreSQL Kurulum

```bash
# Docker ile
docker run -d \
  --name postgres \
  -e POSTGRES_USER=kkb \
  -e POSTGRES_PASSWORD=hackathon2024 \
  -e POSTGRES_DB=firma_istihbarat \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:15
```

### 2. Database Oluştur

```bash
# Container'a bağlan
docker exec -it postgres psql -U kkb -d firma_istihbarat

# Veya dışarıdan
psql -h localhost -U kkb -d firma_istihbarat
```

### 3. Schema'yı Çalıştır

```bash
# schema.sql dosyasını çalıştır
psql -h localhost -U kkb -d firma_istihbarat -f schema.sql
```

### 4. Bağlantı String'i

```
# .env dosyası
DATABASE_URL=postgresql://kkb:hackathon2024@localhost:5432/firma_istihbarat
```

### 5. SQLAlchemy Bağlantısı

```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://kkb:hackathon2024@localhost:5432/firma_istihbarat"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 📁 Tam Schema Dosyası

Tüm tabloları içeren `schema.sql` dosyası `/backend/sql/schema.sql` konumunda olacak.

```
backend/
└── sql/
    ├── schema.sql       # Tüm CREATE TABLE'lar
    ├── indexes.sql      # Tüm index'ler
    ├── seed.sql         # Varsayılan veriler (kategoriler)
    └── drop.sql         # Temizlik için DROP'lar
```

---

## ⚠️ Önemli Notlar

1. **Soft Delete:** Hiçbir şeyi gerçekten silme, `deleted_at` set et
2. **JSONB Validation:** Uygulama katmanında yap, DB'de constraint koyma
3. **Reserved Kullanımı:** Kullandığın reserved kolona COMMENT ekle
4. **Backup:** Production öncesi backup stratejisi belirle
5. **Index:** Yeni sorgu patternleri için index eklemeyi unutma

---

<div align="center">

**⚠️ Migration yapmadan önce bu dökümanı güncelle**

**Son Güncelleme:** 3 Aralık 2024

**Owner:** Bartın (şema), Yamaç (döküman)

</div>
