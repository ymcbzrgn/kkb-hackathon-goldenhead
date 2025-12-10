# 🏗️ Sistem Mimarisi

> Firma İstihbarat Raporu Sistemi - Teknik Mimari Dökümanı

---

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Sistem Bileşenleri](#-sistem-bileşenleri)
- [Veri Akışı](#-veri-akışı)
- [Klasör Yapısı ve Ownership](#-klasör-yapısı-ve-ownership)
- [Teknoloji Stack](#-teknoloji-stack)
- [API İletişimi](#-api-iletişimi)
- [WebSocket Protokolü](#-websocket-protokolü)
- [Veritabanı](#-veritabanı)
- [Background Jobs](#-background-jobs)
- [LLM Entegrasyonu](#-llm-entegrasyonu)
- [Deployment](#-deployment)

---

## 🎯 Genel Bakış

Sistem iki ana aşamadan oluşur:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  AŞAMA 1: VERİ TOPLAMA (~5 dk)                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                          │
│  │   TSG   │ │  İhale  │ │  Haber  │  ← Agent'lar             │
│  │  Agent  │ │  Agent  │ │  Agent  │    paralel çalışır       │
│  └────┬────┘ └────┬────┘ └────┬────┘                          │
│       └───────────┼───────────┘                                │
│                   ▼                                             │
│            ┌─────────────┐                                     │
│            │ Veri Havuzu │                                     │
│            └──────┬──────┘                                     │
│                   │                                             │
├───────────────────┼─────────────────────────────────────────────┤
│                   ▼                                             │
│  AŞAMA 2: DEĞERLENDİRME (~35 dk)                               │
│            ┌─────────────┐                                     │
│            │   COUNCIL   │  ← 6 kişilik komite                 │
│            │  Toplantısı │    tartışarak karar verir           │
│            └──────┬──────┘                                     │
│                   │                                             │
│                   ▼                                             │
│            ┌─────────────┐                                     │
│            │ Final Rapor │                                     │
│            └─────────────┘                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Sistem Bileşenleri

### Katmanlı Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    React Frontend                         │ │
│  │                       (Bekir)                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                    REST API + WebSocket                         │
│                              │                                  │
├──────────────────────────────┼──────────────────────────────────┤
│                       API LAYER                                 │
│                              │                                  │
│  ┌───────────────────────────┴───────────────────────────────┐ │
│  │                    FastAPI Server                         │ │
│  │                       (Bartın)                            │ │
│  │                                                           │ │
│  │   /api/reports     → Rapor CRUD                          │ │
│  │   /api/companies   → Firma arama                         │ │
│  │   /ws              → WebSocket bağlantısı                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
├──────────────────────────────┼──────────────────────────────────┤
│                     SERVICE LAYER                               │
│                              │                                  │
│  ┌──────────────────┐ ┌──────┴───────┐ ┌──────────────────┐   │
│  │  Report Service  │ │ Orchestrator │ │  Council Service │   │
│  │    (Bartın)      │ │   (Yamaç)    │ │     (Yamaç)      │   │
│  └──────────────────┘ └──────────────┘ └──────────────────┘   │
│                              │                                  │
├──────────────────────────────┼──────────────────────────────────┤
│                     AGENT LAYER                                 │
│                              │                                  │
│  ┌──────────────────┐ ┌──────┴───────┐ ┌──────────────────┐   │
│  │    TSG Agent     │ │ İhale Agent  │ │   Haber Agent    │   │
│  │     (Yamaç)      │ │   (Yamaç)    │ │     (Yamaç)      │   │
│  └──────────────────┘ └──────────────┘ └──────────────────┘   │
│                              │                                  │
├──────────────────────────────┼──────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                          │
│                              │                                  │
│  ┌──────────────────┐ ┌──────┴───────┐ ┌──────────────────┐   │
│  │   PostgreSQL     │ │    Redis     │ │   KKB Kloudeks   │   │
│  │    (Bartın)      │ │   (Bartın)   │ │   LLM API        │   │
│  └──────────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Bileşen Açıklamaları

| Bileşen | Sorumlu | Açıklama |
|---------|---------|----------|
| **React Frontend** | Bekir | Kullanıcı arayüzü, WebSocket client |
| **FastAPI Server** | Bartın | REST API, WebSocket server, routing |
| **Report Service** | Bartın | Rapor CRUD, PDF export |
| **Orchestrator** | Yamaç | Agent'ları ve Council'ı koordine eder |
| **Council Service** | Yamaç | 6 kişilik komite toplantısı mantığı |
| **TSG Agent** | Yamaç | Ticaret Sicili Gazetesi scraping |
| **İhale Agent** | Yamaç | EKAP yasaklı kontrolü |
| **Haber Agent** | Yamaç | Haber toplama + sentiment analizi |
| **PostgreSQL** | Bartın | Ana veritabanı |
| **Redis** | Bartın | Cache + Celery broker |
| **KKB Kloudeks** | - | LLM API (gpt-oss-120b, qwen3-omni-30b) |

---

## 🔄 Veri Akışı

### Rapor Oluşturma Akışı

```
┌────────┐     ┌────────┐     ┌────────────┐     ┌─────────┐
│ Bekir  │     │ Bartın │     │   Yamaç    │     │ External│
│Frontend│     │ Backend│     │   AI/ML    │     │ Sources │
└───┬────┘     └───┬────┘     └─────┬──────┘     └────┬────┘
    │              │                │                  │
    │ POST /api/reports/create      │                  │
    │ {company_name: "ABC A.Ş."}    │                  │
    │─────────────────────────────► │                  │
    │              │                │                  │
    │              │ Celery Task    │                  │
    │              │ başlat         │                  │
    │              │───────────────►│                  │
    │              │                │                  │
    │ WS: job_started               │                  │
    │◄─────────────────────────────│                  │
    │              │                │                  │
    │              │                │  TSG, EKAP,      │
    │              │                │  Haberler        │
    │              │                │─────────────────►│
    │              │                │◄─────────────────│
    │              │                │                  │
    │ WS: agent_progress            │                  │
    │◄─────────────────────────────│                  │
    │              │                │                  │
    │              │                │  Council         │
    │              │                │  Toplantısı      │
    │              │                │  (LLM calls)     │
    │              │                │─────────────────►│
    │              │                │◄─────────────────│
    │              │                │                  │
    │ WS: council_speech (streaming)│                  │
    │◄─────────────────────────────│                  │
    │              │                │                  │
    │ WS: council_decision          │                  │
    │◄─────────────────────────────│                  │
    │              │                │                  │
    │              │ Save to DB     │                  │
    │              │◄───────────────│                  │
    │              │                │                  │
    │ WS: job_completed             │                  │
    │◄─────────────────────────────│                  │
    │              │                │                  │
```

### Event Akışı Özeti

```
1. Kullanıcı firma adı girer
2. Backend Celery task başlatır
3. Orchestrator 3 agent'ı paralel çalıştırır
4. Her agent ilerlemesini WebSocket ile bildirir
5. Veriler toplandığında Council başlar
6. Council konuşmaları streaming ile gönderilir
7. Final karar ve rapor kaydedilir
8. Kullanıcıya tamamlandı bildirimi
```

---

## 📁 Klasör Yapısı ve Ownership

### Monorepo Yapısı

```
kkb-hackathon/
│
├── 📁 frontend/                    ← 🔵 BEKİR
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/             # Button, Input, Modal
│   │   │   ├── layout/             # Header, Sidebar
│   │   │   ├── dashboard/          # Ana sayfa bileşenleri
│   │   │   ├── report/             # Rapor görüntüleme
│   │   │   └── council/            # Council toplantı UI
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Report.tsx
│   │   │   └── CouncilMeeting.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useReport.ts
│   │   ├── stores/                 # Zustand
│   │   ├── services/               # API calls
│   │   └── types/                  # TypeScript types
│   ├── package.json
│   └── vite.config.ts
│
├── 📁 backend/                     
│   ├── app/
│   │   ├── 📁 api/                 ← 🟢 BARTIN
│   │   │   ├── routes/
│   │   │   │   ├── reports.py
│   │   │   │   ├── companies.py
│   │   │   │   └── health.py
│   │   │   ├── websocket.py
│   │   │   └── deps.py
│   │   │
│   │   ├── 📁 models/              ← 🟢 BARTIN
│   │   │   ├── report.py
│   │   │   ├── company.py
│   │   │   └── council_decision.py
│   │   │
│   │   ├── 📁 services/            ← 🟢 BARTIN
│   │   │   ├── report_service.py
│   │   │   └── pdf_export.py
│   │   │
│   │   ├── 📁 workers/             ← 🟢 BARTIN
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   │
│   │   ├── 📁 agents/              ← 🔴 YAMAÇ
│   │   │   ├── base_agent.py
│   │   │   ├── tsg_agent.py
│   │   │   ├── ihale_agent.py
│   │   │   ├── news_agent.py
│   │   │   └── orchestrator.py
│   │   │
│   │   ├── 📁 council/             ← 🔴 YAMAÇ
│   │   │   ├── council_service.py
│   │   │   ├── personas.py
│   │   │   └── prompts/
│   │   │       ├── risk_analyst.py
│   │   │       ├── business_analyst.py
│   │   │       ├── legal_expert.py
│   │   │       ├── media_analyst.py
│   │   │       ├── sector_expert.py
│   │   │       └── moderator.py
│   │   │
│   │   ├── 📁 llm/                 ← 🔴 YAMAÇ
│   │   │   ├── client.py           # KKB API wrapper
│   │   │   ├── models.py           # Model configs
│   │   │   └── utils.py
│   │   │
│   │   └── 📁 core/                ← 🟢 BARTIN
│   │       ├── config.py
│   │       ├── database.py
│   │       └── security.py
│   │
│   ├── alembic/                    ← 🟢 BARTIN
│   ├── tests/
│   ├── requirements.txt
│   └── main.py
│
├── 📁 shared/                      ← 🟡 ORTAKLAŞA (Yamaç başlatır)
│   └── schemas/
│       ├── report.py               # Pydantic models
│       ├── agent.py
│       ├── council.py
│       └── websocket.py
│
├── 📁 docker/                      ← 🟢 BARTIN
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   └── nginx/
│
├── 📁 scripts/                     ← 🟢 BARTIN
│   ├── setup.sh
│   ├── deploy.sh
│   └── seed_db.py
│
├── 📁 docs/                        ← 🔴 YAMAÇ
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATABASE.md
│   └── DEPLOYMENT.md
│
├── .env.example
├── Makefile
└── README.md
```

### Ownership Özeti

| Renk | Kişi | Alanlar |
|------|------|---------|
| 🔵 | **Bekir** | `/frontend` |
| 🟢 | **Bartın** | `/backend/api`, `/backend/models`, `/backend/services`, `/backend/workers`, `/backend/core`, `/docker`, `/scripts`, `/alembic` |
| 🔴 | **Yamaç** | `/backend/agents`, `/backend/council`, `/backend/llm`, `/docs` |
| 🟡 | **Ortaklaşa** | `/shared/schemas` (Yamaç tanımlar, herkes kullanır) |

### ⚠️ Kurallar

1. **Kendi alanında çalış:** Başka klasöre dokunmadan önce owner'a haber ver
2. **Shared schemas:** Değişiklik yapılacaksa grup chate yaz
3. **Interface first:** Önce schema tanımla, sonra implementasyon

---

## 🛠️ Teknoloji Stack

### Backend

| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| Python | 3.11+ | Ana dil |
| FastAPI | 0.104+ | Web framework |
| SQLAlchemy | 2.x | ORM |
| Alembic | 1.12+ | Migration |
| Celery | 5.3+ | Task queue |
| Redis | 7+ | Cache + Broker |
| PostgreSQL | 15+ | Database |
| Playwright | 1.40+ | Web scraping |
| httpx | 0.25+ | Async HTTP |

### Frontend

| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Tailwind CSS | 3.x | Styling |
| shadcn/ui | - | Component library |
| Zustand | 4.x | State management |
| React Query | 5.x | Server state |

### AI/ML

| Teknoloji | Kullanım |
|-----------|----------|
| gpt-oss-120b | Ana LLM (reasoning, rapor yazma) |
| qwen3-omni-30b | Vision (PDF okuma) |
| qwen3-embedding-8b | Embedding (RAG için) |

### DevOps

| Teknoloji | Kullanım |
|-----------|----------|
| Docker | Containerization |
| Docker Compose | Orchestration |
| Nginx | Reverse proxy |
| GitHub Actions | CI/CD |

---

## 📡 API İletişimi

### Genel Kurallar

| Kural | Değer |
|-------|-------|
| Format | JSON |
| Naming | snake_case |
| Auth | Bearer token (opsiyonel, hackathon için basit) |
| Versioning | URL'de yok (tek versiyon) |

### REST Endpoints

```
Base URL: http://localhost:8000/api

POST   /reports              → Yeni rapor başlat
GET    /reports              → Rapor listesi
GET    /reports/{id}         → Rapor detayı
GET    /reports/{id}/pdf     → PDF export
DELETE /reports/{id}         → Rapor sil

GET    /companies/search     → Firma ara (autocomplete)
```

### Request/Response Format

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "REPORT_NOT_FOUND",
    "message": "Rapor bulunamadı"
  }
}
```

### HTTP Status Codes

| Code | Kullanım |
|------|----------|
| 200 | Başarılı GET, PUT |
| 201 | Başarılı POST (create) |
| 400 | Validation error |
| 404 | Resource not found |
| 500 | Server error |

---

## 🔌 WebSocket Protokolü

### Bağlantı

```
URL: ws://localhost:8000/ws/{report_id}
```

### Event Formatı

```json
{
  "type": "event_type",
  "timestamp": "2024-12-03T14:30:00Z",
  "payload": { ... }
}
```

### Event Tipleri

#### 1. Job Events

```json
// İş başladı
{
  "type": "job_started",
  "payload": {
    "report_id": "uuid",
    "company_name": "ABC A.Ş."
  }
}

// İş tamamlandı
{
  "type": "job_completed",
  "payload": {
    "report_id": "uuid",
    "duration_seconds": 2340
  }
}

// Hata oluştu
{
  "type": "job_error",
  "payload": {
    "error_code": "TSG_TIMEOUT",
    "message": "TSG'ye bağlanılamadı"
  }
}
```

#### 2. Agent Events

```json
// Agent başladı
{
  "type": "agent_started",
  "payload": {
    "agent": "tsg_agent",
    "display_name": "TSG Agent"
  }
}

// Agent ilerleme
{
  "type": "agent_progress",
  "payload": {
    "agent": "tsg_agent",
    "progress": 50,
    "message": "4/8 PDF analiz edildi"
  }
}

// Agent tamamlandı
{
  "type": "agent_completed",
  "payload": {
    "agent": "tsg_agent",
    "result_summary": {
      "records_found": 8,
      "key_findings": ["Sermaye artışı", "Yönetici değişikliği"]
    }
  }
}
```

#### 3. Council Events

```json
// Toplantı başladı
{
  "type": "council_started",
  "payload": {
    "estimated_duration_minutes": 35
  }
}

// Aşama değişti
{
  "type": "council_phase",
  "payload": {
    "phase": "presentation",
    "phase_number": 2,
    "total_phases": 8,
    "title": "Risk Sunumu"
  }
}

// Konuşmacı değişti
{
  "type": "council_speaker",
  "payload": {
    "speaker_id": "risk_analyst",
    "name": "Mehmet Bey",
    "role": "Baş Risk Analisti",
    "emoji": "🔴"
  }
}

// Konuşma (streaming)
{
  "type": "council_speech_chunk",
  "payload": {
    "speaker_id": "risk_analyst",
    "chunk": "8 ayda 3 genel müdür değişikliği var. "
  }
}

// Konuşma tamamlandı
{
  "type": "council_speech_complete",
  "payload": {
    "speaker_id": "risk_analyst",
    "risk_score": 65,
    "summary": "Yüksek risk görüyorum..."
  }
}

// Skor revizyonu
{
  "type": "council_score_revision",
  "payload": {
    "speaker_id": "risk_analyst",
    "old_score": 65,
    "new_score": 45,
    "reason": "Tartışmada yeni bilgiler öğrendim"
  }
}

// Final karar
{
  "type": "council_decision",
  "payload": {
    "final_score": 33,
    "risk_level": "ORTA_DUSUK",
    "decision": "SARTLI_ONAY",
    "conditions": ["6 aylık izleme", "Bildirim covenant'ı"],
    "consensus": 0.85,
    "dissent_note": "Risk analisti başlangıçta..."
  }
}
```

---

## 🗄️ Veritabanı

### Temel Tablolar

```
┌─────────────────────────────────────────────────────────────┐
│                         reports                              │
├─────────────────────────────────────────────────────────────┤
│ id (PK)          │ UUID                                     │
│ company_name     │ VARCHAR(255)                             │
│ company_tax_no   │ VARCHAR(20), nullable                    │
│ status           │ ENUM(pending, processing, completed, failed)│
│ final_score      │ INTEGER, nullable                        │
│ risk_level       │ VARCHAR(20), nullable                    │
│ decision         │ VARCHAR(50), nullable                    │
│ created_at       │ TIMESTAMP                                │
│ completed_at     │ TIMESTAMP, nullable                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     council_decisions                        │
├─────────────────────────────────────────────────────────────┤
│ id (PK)          │ UUID                                     │
│ report_id (FK)   │ UUID → reports.id                        │
│ transcript       │ JSONB                                    │
│ scores           │ JSONB                                    │
│ conditions       │ JSONB                                    │
│ dissent_note     │ TEXT, nullable                           │
│ consensus        │ FLOAT                                    │
│ duration_seconds │ INTEGER                                  │
│ created_at       │ TIMESTAMP                                │
└─────────────────────────────────────────────────────────────┘
                              
┌─────────────────────────────────────────────────────────────┐
│                      agent_results                           │
├─────────────────────────────────────────────────────────────┤
│ id (PK)          │ UUID                                     │
│ report_id (FK)   │ UUID → reports.id                        │
│ agent_type       │ ENUM(tsg, ihale, news)                   │
│ raw_data         │ JSONB                                    │
│ processed_data   │ JSONB                                    │
│ status           │ ENUM(pending, completed, failed)         │
│ error_message    │ TEXT, nullable                           │
│ duration_seconds │ INTEGER                                  │
│ created_at       │ TIMESTAMP                                │
└─────────────────────────────────────────────────────────────┘
```

### JSONB Yapıları

**scores (council_decisions):**
```json
{
  "initial": {
    "risk_analyst": 65,
    "business_analyst": 25,
    "legal_expert": 30,
    "media_analyst": 30,
    "sector_expert": 35
  },
  "final": {
    "risk_analyst": 45,
    "business_analyst": 25,
    "legal_expert": 30,
    "media_analyst": 30,
    "sector_expert": 35
  },
  "average": 33
}
```

**transcript (council_decisions):**
```json
{
  "entries": [
    {
      "timestamp": "2024-12-03T14:30:00Z",
      "speaker_id": "moderator",
      "speaker_name": "GMY",
      "content": "Toplantıyı açıyorum...",
      "phase": "opening"
    },
    {
      "timestamp": "2024-12-03T14:32:00Z",
      "speaker_id": "risk_analyst",
      "speaker_name": "Mehmet Bey",
      "content": "8 ayda 3 yönetici değişikliği...",
      "phase": "presentation",
      "risk_score": 65
    }
  ]
}
```

---

## ⚙️ Background Jobs

### Celery Yapısı

```
┌─────────────────────────────────────────────────────────────┐
│                      Celery Worker                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task: generate_report                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  1. Update status → "processing"                    │   │
│  │  2. Run agents (parallel)                           │   │
│  │     ├── tsg_agent.run()                            │   │
│  │     ├── ihale_agent.run()                          │   │
│  │     └── news_agent.run()                           │   │
│  │  3. Aggregate results                               │   │
│  │  4. Run council meeting                             │   │
│  │  5. Save to database                                │   │
│  │  6. Update status → "completed"                     │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  WebSocket notifications at each step                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Task Flow

```python
# Pseudo-code
@celery_app.task
def generate_report(report_id: str, company_name: str):
    # 1. Status update
    update_status(report_id, "processing")
    notify_ws(report_id, "job_started")
    
    # 2. Parallel agents
    results = await asyncio.gather(
        tsg_agent.run(company_name),
        ihale_agent.run(company_name),
        news_agent.run(company_name),
    )
    
    # 3. Council
    council_result = await council_service.run_meeting(
        company_data=aggregate(results),
        ws_callback=lambda e: notify_ws(report_id, e)
    )
    
    # 4. Save
    save_results(report_id, results, council_result)
    update_status(report_id, "completed")
    notify_ws(report_id, "job_completed")
```

---

## 🤖 LLM Entegrasyonu

### KKB Kloudeks API

```
Base URL: https://mia.csp.kloudeks.com/api/v1
Auth: Bearer token
```

### Model Kullanımı

| Model | Kullanım Yeri |
|-------|---------------|
| **gpt-oss-120b** | Council konuşmaları, sentiment analizi, rapor yazma |
| **qwen3-omni-30b** | PDF/görsel okuma (Vision) |
| **qwen3-embedding-8b** | RAG için embedding (opsiyonel) |

### LLM Client Wrapper

```
┌─────────────────────────────────────────────────────────────┐
│                      LLMClient                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Methods:                                                   │
│  ├── chat(messages, model, stream=False)                   │
│  ├── chat_stream(messages, model) → AsyncGenerator         │
│  ├── vision(image_base64, prompt)                          │
│  └── embed(text) → list[float]                             │
│                                                             │
│  Features:                                                  │
│  ├── Retry logic (3 attempts)                              │
│  ├── Rate limiting                                          │
│  ├── Error handling                                         │
│  └── Token counting (opsiyonel)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment

### VPS Bilgileri

| Özellik | Değer |
|---------|-------|
| CPU | 4 Core Platinum |
| RAM | 32 GB ECC |
| Disk | 160 GB E-NVMe |
| Lokasyon | İstanbul / Bursa |
| OS | Ubuntu 22.04 |

### Container Yapısı

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (32 GB RAM)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Nginx                             │   │
│  │                   (Port 80)                          │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│           ┌────────────┴────────────┐                      │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │    Frontend     │    │     Backend     │               │
│  │   (Port 3000)   │    │   (Port 8000)   │               │
│  └─────────────────┘    └────────┬────────┘               │
│                                  │                         │
│                    ┌─────────────┼─────────────┐          │
│                    │             │             │          │
│                    ▼             ▼             ▼          │
│           ┌─────────────┐ ┌───────────┐ ┌───────────┐    │
│           │ PostgreSQL  │ │   Redis   │ │  Celery   │    │
│           │ (Port 5432) │ │(Port 6379)│ │  Workers  │    │
│           └─────────────┘ └───────────┘ └───────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### RAM Dağılımı (32 GB)

| Servis | RAM | Not |
|--------|-----|-----|
| PostgreSQL | 2 GB | shared_buffers=512MB |
| Redis | 1 GB | Yeterli cache alanı |
| FastAPI | 2 GB | Uvicorn workers |
| Celery Workers (x2) | 4 GB | Paralel task işleme |
| Playwright | 2 GB | Headless browser |
| Qdrant | 4 GB | Vector DB (RAM mode) |
| Frontend | 512 MB | Static serve |
| Nginx | 128 MB | Reverse proxy |
| OS + Buffer | ~16 GB | Yeterli headroom |
| **TOPLAM** | ~32 GB | ✅ Rahat |

### CPU Dağılımı (4 Core)

| Servis | Core |
|--------|------|
| FastAPI + Uvicorn | 1 |
| Celery Workers | 2 |
| PostgreSQL + Redis + Qdrant | 1 |

---

## 📏 Geliştirme Kuralları

### Git Workflow

```
main
  │
  ├── feature/bekir-dashboard
  ├── feature/bartin-api-endpoints
  └── feature/yamac-council-service
```

### Commit Convention

```
feat: Yeni özellik
fix: Bug düzeltme
docs: Döküman güncelleme
refactor: Kod iyileştirme
test: Test ekleme
```

### PR Kuralları

1. Kendi alanında çalış
2. Başka klasöre dokunuyorsan owner'dan onay al
3. PR açmadan önce local test
4. Merge conflict'leri kendi çöz

---

## 📞 İletişim Protokolü

| Durum | Aksiyon |
|-------|---------|
| `/shared/schemas` değişikliği | Slack'e mesaj at |
| API endpoint değişikliği | Bekir'e haber ver |
| Database şema değişikliği | Herkese haber ver |
| Blocker var | Hemen sesli arama |

---

<div align="center">

**Son Güncelleme:** 3 Aralık 2024

**Owner:** Yamaç

</div>
