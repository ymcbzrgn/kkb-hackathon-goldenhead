# Backend - Firma İstihbarat API

KKB Agentic AI Hackathon 2024 - Backend API

## Teknoloji Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL + SQLAlchemy
- **Cache/Queue:** Redis + Celery
- **Vector DB:** Qdrant
- **LLM:** KKB Kloudeks API (gpt-oss-120b, qwen3-omni-30b, qwen3-embedding-8b)

## Proje Yapısı

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── routes/       # Route handlers
│   │   ├── websocket.py  # WebSocket handler
│   │   └── deps.py       # Dependencies
│   │
│   ├── models/           # SQLAlchemy models
│   │   ├── report.py
│   │   ├── company.py
│   │   └── council_decision.py
│   │
│   ├── services/         # Business logic
│   │   ├── report_service.py
│   │   └── pdf_export.py
│   │
│   ├── workers/          # Celery tasks
│   │   ├── celery_app.py
│   │   └── tasks.py
│   │
│   ├── agents/           # AI Agents
│   │   ├── base_agent.py
│   │   ├── tsg_agent.py
│   │   ├── ihale_agent.py
│   │   ├── news_agent.py
│   │   └── orchestrator.py
│   │
│   ├── council/          # AI Council
│   │   ├── council_service.py
│   │   ├── personas.py
│   │   └── prompts/
│   │
│   ├── llm/              # LLM Client
│   │   ├── client.py
│   │   ├── models.py
│   │   └── utils.py
│   │
│   └── core/             # Core utilities
│       ├── config.py
│       ├── database.py
│       └── security.py
│
├── sql/                  # SQL scripts
├── tests/                # Tests
├── main.py               # Entry point
├── requirements.txt
└── .env.example
```

## Kurulum

### 1. Gereksinimler

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Qdrant

### 2. Ortamı Hazırla

```bash
# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyasını oluştur
cp .env.example .env
# .env dosyasını düzenle
```

### 3. Veritabanını Hazırla

```bash
# Docker ile servisler
docker-compose -f ../docker/docker-compose.dev.yml up -d

# Migrations (ilk kurulumda)
alembic upgrade head

# Seed data (opsiyonel)
python ../scripts/seed_db.py
```

### 4. Çalıştır

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
```
GET /api/health
```

### Reports
```
POST /api/reports              # Yeni rapor oluştur
GET  /api/reports              # Rapor listesi
GET  /api/reports/{id}         # Rapor detayı
DELETE /api/reports/{id}       # Rapor sil
GET  /api/reports/{id}/pdf     # PDF indir
```

### Companies
```
GET /api/companies/search      # Firma ara
GET /api/companies/autocomplete # Autocomplete
```

### WebSocket
```
WS /ws/{report_id}             # Real-time rapor takibi
```

## WebSocket Events

```
job_started       - İş başladı
agent_started     - Agent başladı
agent_progress    - Agent ilerlemesi
agent_completed   - Agent tamamlandı
council_started   - Toplantı başladı
council_speech    - Konuşma (streaming)
council_decision  - Final karar
job_completed     - İş tamamlandı
```

## Testler

```bash
pytest -v
pytest --cov=app tests/
```

## Sorumluluk Alanları

| Alan | Owner |
|------|-------|
| api/, models/, services/, workers/, core/ | Bartın |
| agents/, council/, llm/ | Yamaç |

## Lisans

KKB Hackathon 2024
