# MVP Plan - KKB Firma İstihbarat Sistemi

> **Teslim Tarihi:** 4 Gün Sonra
> **Son Güncelleme:** 7 Aralık 2024
> **PM:** Yamaç

---

## Mevcut Durum (7 Aralık 2024)

### Tamamlanan İşler

| Kategori | Durum | Detay |
|----------|-------|-------|
| **Proje Yapısı** | ✅ %100 | Monorepo yapısı tamamlandı |
| **Dökümanlar** | ✅ %100 | API.md, DATABASE.md, ARCHITECTURE-2.md, VECTORDB.md |
| **Frontend UI** | ✅ %90 | Bekir tamamladı (components, pages, hooks, stores) |
| **Backend Boilerplate** | ✅ %80 | FastAPI, routes, models, schemas hazır |
| **Docker Setup** | ✅ %100 | PostgreSQL, Redis, Qdrant, pgAdmin çalışıyor |
| **Database Schema** | ✅ %100 | Tüm tablolar ve indexler oluşturuldu |
| **WebSocket** | ✅ %100 | Temel bağlantı çalışıyor |
| **Agent Yapısı** | ✅ %85 | TSG Agent %100, Orchestrator %100, İhale/News mock |
| **Council Yapısı** | ✅ %100 | 8 aşamalı toplantı, streaming TAM |
| **LLM Client** | ✅ %100 | Client, streaming, vision, embedding TAM |

### Eksik/TODO Listesi

```
Backend (Bartın):
├── reports.py      → Database CRUD (5 TODO)
├── companies.py    → Search, autocomplete (2 TODO)
├── pdf_export.py   → PDF oluşturma (1 TODO)
└── Celery tasks    → Background job (1 TODO)

AI/ML (Yamaç):
├── tsg_agent.py    → ✅ TAMAMLANDI (Vision + CAPTCHA + PDF gen)
├── ihale_agent.py  → EKAP scraping - Agentic yapı (IN PROGRESS)
├── news_agent.py   → Haber + Sentiment (2 TODO)
└── council_service → ✅ TAMAMLANDI (8 aşama, streaming)
```

---

## MVP Kapsamı (Must Have vs Nice to Have)

> **KRİTİK NOT:** Bu bir hackathon ürünü! Jüri'nin beklediği ana deliverable:
> 1. **3 Agent'ın GERÇEK veri toplaması**
> 2. **Bu verilerden anlamlı bir rapor üretilmesi**
>
> Council (6 kişilik AI komite) bizim eklediğimiz bonus özellik!

### MUST HAVE (MVP) - KRİTİK

| Özellik | Açıklama | Owner | Öncelik |
|---------|----------|-------|---------|
| **TSG Agent** | TSG'den GERÇEK veri çekme (Playwright + Vision) | Yamaç | **P0** |
| **İhale Agent** | EKAP'tan GERÇEK yasak kontrolü | Yamaç | **P0** |
| **News Agent** | GERÇEK haber toplama + sentiment analizi | Yamaç | **P0** |
| **Rapor Üretimi** | Agent verilerinden kapsamlı rapor | Yamaç | **P0** |
| Rapor oluşturma | Yeni rapor başlatma + DB kayıt | Bartın | P1 |
| Rapor listeleme | Tüm raporları görme | Bartın | P1 |
| Rapor detay | Tek rapor detayı | Bartın | P1 |
| WebSocket Stream | Real-time ilerleme gösterimi | Bartın + Yamaç | P1 |
| UI Entegrasyonu | Backend-Frontend bağlantısı | Bekir | P1 |
| Firma arama | İsim ile firma arama | Bartın | P2 |

### NICE TO HAVE (Bonus Özellikler)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| ~~Council Toplantısı~~ | ~~6 kişilik AI komite~~ | ✅ **TAMAMLANDI!** |
| ~~Council Streaming~~ | ~~Canlı konuşma gösterimi~~ | ✅ **TAMAMLANDI!** |
| PDF Export | Rapor PDF indirme | Düşük |
| Qdrant RAG | Geçmiş raporlardan öğrenme | Düşük |
| Skor Revizyonu | Tartışma sonrası skor değişimi | Düşük |

---

## 4 Günlük Roadmap

### GÜN 1 (Bugün - 6 Aralık) - AGENT TEMELLERİ

> **Odak:** Agent'ların GERÇEK veri toplaması için altyapı

#### Sabah (09:00 - 13:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | TSG Agent - Playwright scraping | TSG sitesinden gerçek veri çekilir |
| **Bartın** | Report CRUD implementasyonu | `POST/GET/DELETE /api/reports` çalışır |
| **Bekir** | API bağlantı kontrolü | Frontend API'ye bağlanır |

#### Öğleden Sonra (14:00 - 18:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | İhale Agent - EKAP scraping | EKAP'tan yasak listesi çekilir |
| **Bartın** | Agent sonuçlarını DB'ye kaydetme | agent_results tablosu doluyor |
| **Bekir** | Agent progress UI | İlerleme çubukları görünür |

#### Gün Sonu Milestone
- [x] TSG Agent GERÇEK veri çekiyor ✅
- [ ] İhale Agent GERÇEK yasak kontrolü yapıyor
- [x] Rapor DB'ye kaydediliyor ✅

---

### GÜN 2 (7 Aralık) - AGENT TAMAMLAMA + RAPOR

> **Odak:** News Agent + LLM ile rapor üretimi

#### Sabah (09:00 - 13:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | News Agent - Haber scraping | Google News/Haber sitelerinden veri |
| **Yamaç** | Sentiment Analizi (LLM) | Haberlerin duygu analizi |
| **Bartın** | Celery task entegrasyonu | Agent'lar async çalışıyor |
| **Bekir** | WebSocket entegrasyonu | Real-time event'ler görünür |

#### Öğleden Sonra (14:00 - 18:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | Rapor Üretimi (LLM) | 3 agent verisinden kapsamlı rapor |
| **Yamaç** | Risk Skoru Hesaplama | Otomatik skor algoritması |
| **Bartın** | Rapor detay endpoint'i | Tam rapor JSON döner |
| **Bekir** | Rapor detay sayfası UI | Güzel rapor görünümü |

#### Gün Sonu Milestone
- [ ] **3 Agent GERÇEK veri topluyor**
- [ ] **LLM ile rapor üretiliyor**
- [ ] **Risk skoru hesaplanıyor**
- [ ] End-to-end akış çalışıyor

---

### GÜN 3 (8 Aralık) - POLISH + COUNCIL (BONUS)

> **Odak:** Hata yönetimi + Council (eğer zaman kalırsa)

#### Sabah (09:00 - 13:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | Edge case'ler (firma bulunamadı, timeout) | Graceful error handling |
| **Yamaç** | Council Service (BONUS) | 6 üye konuşuyor (basit versiyon) |
| **Bartın** | Hata yönetimi + Retry logic | Robust backend |
| **Bekir** | UI polish + hata mesajları | Kullanıcı dostu hatalar |

#### Öğleden Sonra (14:00 - 18:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **Yamaç** | Rapor kalitesi iyileştirme | Daha detaylı raporlar |
| **Yamaç** | Council streaming (BONUS) | Canlı konuşma gösterimi |
| **Bartın** | Company search implementasyonu | Firma arama çalışır |
| **Bekir** | Council UI (BONUS) | Konuşma baloncukları |

#### Gün Sonu Milestone
- [ ] Agent'lar %100 stabil çalışıyor
- [ ] Raporlar yüksek kalitede
- [ ] (BONUS) Council çalışıyorsa süper!

---

### GÜN 4 (9 Aralık - TESLİM)

> **Odak:** Test + Demo + Submission

#### Sabah (09:00 - 12:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **HERKES** | End-to-end test (3 farklı firma) | Tam akış sorunsuz |
| **Yamaç** | Demo senaryosu hazırlama | Düşük/Orta/Yüksek risk örnekleri |
| **Bekir** | Son UI düzeltmeleri | Pixel perfect |

#### Öğleden Sonra (13:00 - 16:00)

| Kişi | Görev | Çıktı |
|------|-------|-------|
| **HERKES** | Bug fixing | Kritik buglar düzeltildi |
| **Bartın** | Production build + deploy | Canlı sistem |
| **Yamaç** | README + Demo video | Sunum materyalleri |

#### Teslim Öncesi (16:00 - 18:00)
- [ ] Final test
- [ ] Demo rehearsal
- [ ] Submission

---

## Risk Yönetimi

### Yüksek Risk Senaryoları (Agent Odaklı)

| Risk | Etki | Plan B |
|------|------|--------|
| **TSG sitesi değişti/captcha** | Veri çekilemiyor | Alternatif kaynak: firma.com.tr veya manual input |
| **EKAP erişim engeli** | Yasak kontrolü yapılamıyor | Resmi API varsa kullan, yoksa kullanıcıdan bilgi iste |
| **Haber sitesi scraping engeli** | Sentiment analizi yapılamıyor | Google Custom Search API kullan |
| **KKB API rate limit** | LLM yanıt vermiyor | Retry + exponential backoff |
| **KKB API tamamen çöktü** | Rapor üretilemez | OpenAI/Claude API yedek (son çare) |

### Orta Risk Senaryoları

| Risk | Etki | Plan B |
|------|------|--------|
| Playwright yavaş | Agent timeout | Headless mode + optimize selectors |
| LLM hallucination | Yanlış bilgi | Structured output + validation |
| WebSocket bağlantı sorunu | Real-time yok | Polling ile fallback |
| Frontend-Backend uyumsuzluk | Entegrasyon sorunu | API.md'yi referans al |

### Düşük Risk Senaryoları

| Risk | Etki | Plan B |
|------|------|--------|
| Database performans | Yavaş sorgular | Index'leri kontrol et |
| Docker sorunları | Servisler çalışmaz | Manuel başlatma |
| Celery worker crash | Task'lar çalışmaz | Sync işlem (yavaş ama çalışır) |

### Kaçış Planı (Son 1 Gün Kaldıysa)

> **ÖNEMLİ:** Agent'lar MUTLAKA çalışmalı! Aşağıdaki sadece son çare:

Eğer Gün 3 sonunda agent'lar hala çalışmıyorsa:

1. **TSG için:** Manuel firma bilgisi girişi (kullanıcı girer, LLM analiz eder)
2. **İhale için:** Kullanıcıya "yasak var mı?" checkbox'ı göster
3. **News için:** Kullanıcıdan haber link'leri iste, LLM analiz etsin
4. **Council'ı tamamen atla:** Sadece 3 agent + LLM rapor
5. **Risk skorunu basitleştir:** Rule-based skor (LLM yerine)

---

## Günlük Stand-up Formatı

Her gün sabah 09:00'da 15 dakikalık stand-up:

```
1. Dün ne yaptın?
2. Bugün ne yapacaksın?
3. Blocker var mı?
```

### İletişim Kanalları

| Kanal | Kullanım |
|-------|----------|
| Slack #general | Genel iletişim |
| Slack #blockers | Acil yardım |
| GitHub Issues | Bug tracking |
| Bu dosya | Plan güncellemeleri |

---

## Teknik Notlar

### API Base URL'ler

```
Development:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Qdrant: localhost:6333
```

### Önemli Komutlar

```bash
# Backend başlat
cd backend && source venv/bin/activate && uvicorn main:app --reload

# Frontend başlat
cd frontend && npm run dev

# Docker servisler
docker compose -f docker/docker-compose.dev.yml up -d

# Database seed
cat backend/sql/seed.sql | docker exec -i kkb-postgres-dev psql -U kkb -d firma_istihbarat
```

### Branch Stratejisi

```
main          → Production-ready kod
dev/bekir     → Frontend development
dev/bartin    → Backend development
dev/yamac     → AI/ML development
```


---

## Checklist - MVP Tamamlanma Kriterleri

### KRİTİK (Hackathon Jüri Beklentisi)

- [ ] **TSG Agent GERÇEK veri çekiyor** (firma kuruluş, sermaye, ortaklar)
- [ ] **İhale Agent GERÇEK yasak kontrolü yapıyor** (EKAP)
- [ ] **News Agent GERÇEK haber topluyor** (son 6 ay)
- [ ] **LLM ile sentiment analizi yapılıyor**
- [ ] **LLM ile kapsamlı rapor üretiliyor**
- [ ] **Risk skoru hesaplanıyor** (0-100)
- [ ] **Karar önerisi veriliyor** (Onay/Şartlı/Red/İnceleme)

### Fonksiyonel

- [ ] Firma adı girip rapor başlatılabiliyor
- [ ] Real-time ilerleme WebSocket'te görünüyor
- [ ] Rapor listesi görüntülenebiliyor
- [ ] Rapor detayı görüntülenebiliyor
- [ ] (BONUS) Council toplantısı çalışıyor

### Teknik

- [ ] Backend tüm endpoint'lerde 200 dönüyor
- [ ] Frontend hatasız render oluyor
- [ ] WebSocket bağlantısı stabil
- [ ] Database kayıtları doğru
- [ ] Agent'lar 60 saniye içinde veri çekiyor
- [ ] Rapor 2 dakika içinde tamamlanıyor

### Demo

- [ ] 3 farklı firma ile demo senaryosu hazır
- [ ] Düşük/Orta/Yüksek risk örnekleri
- [ ] Jüri'ye agent'ların GERÇEK çalıştığı gösteriliyor
- [ ] Canlı demo 5 dakikada tamamlanıyor

---

## Sorumluluk Matrisi (RACI)

| Görev | Bekir | Bartın | Yamaç |
|-------|-------|--------|-------|
| Frontend UI | **R** | C | I |
| Backend API | C | **R** | I |
| Database | I | **R** | C |
| AI Agents | I | C | **R** |
| Council | I | C | **R** |
| LLM Integration | I | C | **R** |
| WebSocket | C | **R** | A |
| Docker/DevOps | I | **R** | C |
| Documentation | C | C | **R** |

> R: Responsible, A: Accountable, C: Consulted, I: Informed

---

## Günlük Progress Log

### 6 Aralık (Gün 1)

| Saat | Kişi | Yapılan İş | Durum |
|------|------|------------|-------|
| 00:51 | Yamaç | Monorepo yapısı tamamlandı | ✅ |
| 00:51 | Yamaç | E2E testleri geçti | ✅ |
| 00:51 | Yamaç | MVP_PLAN.md oluşturuldu | ✅ |
| 23:00 | Yamaç | TSG Agent v9.3 tamamlandı (1,312+ satır) | ✅ |
| 23:00 | Yamaç | CAPTCHA çözümü eklendi (Tesseract OCR) | ✅ |
| 23:00 | Yamaç | PDF generator eklendi | ✅ |
| 23:00 | Yamaç | Council Service %100 tamamlandı (533 satır) | ✅ |
| 23:00 | Yamaç | LLM Client %100 tamamlandı | ✅ |

### 7 Aralık (Gün 2)

| Saat | Kişi | Yapılan İş | Durum |
|------|------|------------|-------|
| | | | |

### 8 Aralık (Gün 3)

| Saat | Kişi | Yapılan İş | Durum |
|------|------|------------|-------|
| | | | |

### 9 Aralık (Gün 4 - TESLİM)

| Saat | Kişi | Yapılan İş | Durum |
|------|------|------------|-------|
| | | | |

---

## Mevcut Kod Analizi (7 Aralık Güncellemesi)

### Genel Durum Tablosu

| Bileşen | Durum | Açıklama |
|---------|-------|----------|
| **LLM Client** | ✅ 100% | Streaming, Vision, Embedding TAM |
| **Council Service** | ✅ 100% | 8 aşamalı toplantı, streaming TAM |
| **Orchestrator** | ✅ 100% | Paralel agent yönetimi TAM |
| **Base Agent** | ✅ 100% | Progress tracking TAM |
| **WebSocket** | ✅ 100% | Event'ler, heartbeat TAM |
| **TSG Agent** | ✅ 100% | **Vision AI, CAPTCHA, PDF gen TAM** |
| **İhale Agent** | ⚠️ 20% | **Interface hazır, EKAP MOCK - Agentic yapıya geçiliyor** |
| **News Agent** | ⚠️ 20% | **Interface hazır, Haber MOCK** |
| **Reports API** | ⚠️ 60% | Schema OK, DB ops TODO |

---

## Kişi Bazlı Görev Kartları

---

### YAMAÇ - AI/ML Görevleri

#### GÜN 1: Agent Implementasyonları

**GÖREV 1.1: TSG Agent - Web Scraping** ✅ TAMAMLANDI
```
Dosya: backend/app/agents/tsg/scraper.py (1,357 satır)
Durum: TAMAMLANDI

Yapılanlar:
1. [x] Playwright ile TSG sitesine bağlantı
2. [x] CAPTCHA çözümü (Tesseract OCR)
3. [x] Firma arama + şehir filtresi
4. [x] Multi-PDF indirme stratejisi (YÖNETIM → KURULUS → SERMAYE)
5. [x] Gazete sayfası screenshot

Çıktı: 8 zorunlu alan (Firma Unvanı, Tescil Konusu, Mersis No, vb.)
```

**GÖREV 1.2: TSG Agent - PDF Vision** ✅ TAMAMLANDI
```
Dosya: backend/app/agents/tsg/agent.py (1,312 satır)
Durum: TAMAMLANDI

Yapılanlar:
1. [x] LLM Vision API entegrasyonu
2. [x] PDF okuma + OCR
3. [x] Structured JSON çıkarma
4. [x] PDF generator (profesyonel gazete sayfası)
5. [x] 5 dakika time limit (hackathon güvenliği)

Modül: backend/app/agents/tsg/ (7 dosya, 4,000+ satır)
```

**GÖREV 1.3: İhale Agent - EKAP Scraping** 🔄 IN PROGRESS (Agentic Yapı)
```
Yeni Modül: backend/app/agents/ekap/
Durum: BAŞLIYOR

TSG tarzı agentic yapı ile yeniden yazılıyor:
1. [ ] ekap/logger.py - TSG'den kopyala
2. [ ] ekap/scraper.py - Playwright ile EKAP scraping
3. [ ] ekap/company_finder.py - LLM ile firma doğrulama (temperature=0.0)
4. [ ] ekap/agent.py - System + User prompt ayrımı (temperature=0.1)

LLM Stratejisi:
- company_finder: Firma eşleştirme (EVET/HAYIR) - temp=0.0
- agent: Yasak analizi (JSON) - temp=0.1
- System + User prompt ayrımı → %80 token tasarrufu

Kaynak: https://ekapv2.kik.gov.tr/sorgulamalar/yasak-sorgulama
```

**GÖREV 1.4: News Agent - Haber Scraping**
```
Dosya: backend/app/agents/news_agent.py (Satır 77)
Süre: 2-3 saat

Yapılacaklar:
1. [ ] Google News veya haber sitesi scraping
2. [ ] Son 12 ayın haberlerini topla
3. [ ] Başlık, kaynak, tarih, URL çek

Kabul Kriterleri:
- [ ] Minimum 5 haber döndürüyor
- [ ] Rate limiting var
```

**GÖREV 1.5: News Agent - LLM Sentiment**
```
Dosya: backend/app/agents/news_agent.py (Satır 111)
Süre: 1-2 saat

Yapılacaklar:
1. [ ] LLMClient.analyze_sentiment() kullan
2. [ ] Her haber için pozitif/negatif/nötr belirle

Kabul Kriterleri:
- [ ] LLM sentiment skoru 0.0-1.0 arası
- [ ] Açıklama dönüyor
```

---

### BARTIN - Backend Görevleri

#### GÜN 1: API & Database

**GÖREV B1.1: Reports CRUD**
```
Dosya: backend/app/api/routes/reports.py
Süre: 3-4 saat

Yapılacaklar:
1. [ ] POST /api/reports → DB'ye kaydet + Celery task başlat
2. [ ] GET /api/reports → DB'den listele
3. [ ] GET /api/reports/{id} → Detay getir
4. [ ] DELETE /api/reports/{id} → Soft delete

Kabul Kriterleri:
- [ ] curl ile POST çalışıyor
- [ ] report_id UUID dönüyor
- [ ] Celery task tetikleniyor
```

**GÖREV B1.2: Celery Task Integration**
```
Dosya: backend/app/workers/tasks.py
Süre: 2 saat

Yapılacaklar:
1. [ ] generate_report_task içinde Orchestrator çağır
2. [ ] Sonuçları DB'ye kaydet
3. [ ] Status güncelle (processing → completed)
```

---

### BEKİR - Frontend Görevleri

#### GÜN 1: API Entegrasyonu

**GÖREV F1.1: WebSocket Hook**
```
Dosya: frontend/src/hooks/useWebSocket.ts
Süre: 2-3 saat

Yapılacaklar:
1. [ ] WebSocket bağlantısı aç
2. [ ] Event listener'ları kur
3. [ ] Reconnect logic ekle

Event'ler: job_started, agent_progress, council_speech, council_decision
```

**GÖREV F1.2: Agent Progress UI**
```
Süre: 2-3 saat

Yapılacaklar:
1. [ ] 3 agent için progress bar
2. [ ] Her agent'ın durumunu göster
3. [ ] agent_progress event'lerini dinle
```

#### GÜN 2: Council UI

**GÖREV F2.1: Council Streaming**
```
Süre: 3-4 saat

Yapılacaklar:
1. [ ] council_speaker_changed → Konuşmacıyı göster
2. [ ] council_speech → Streaming text
3. [ ] council_decision → Final karar göster
```

---

## Demo Hazırlık

### Demo Firmaları (Belirlenmeli)
```
1. DÜŞÜK RİSK: _______________  (Beklenen: 15-30, ONAY)
2. ORTA RİSK:  _______________  (Beklenen: 35-55, ŞARTLI ONAY)
3. YÜKSEK RİSK: ______________ (Beklenen: 65+, RED)
```

### Demo Script (5 dakika)
```
0:00-0:30  → Sistem tanıtımı
0:30-1:00  → Firma adı girişi
1:00-2:30  → Agent'ların çalışması
2:30-4:00  → Council toplantısı
4:00-5:00  → Final rapor
```

---

## Acil Kontrol Listesi

### Başlamadan Önce
- [ ] Docker servisleri çalışıyor mu? (PostgreSQL, Redis, Qdrant)
- [ ] KKB_API_KEY .env'de set edildi mi?
- [ ] Backend başlıyor mu? (`python main.py`)
- [ ] Frontend başlıyor mu? (`npm run dev`)
- [ ] Celery worker başlıyor mu?

---

## Notlar ve Kararlar

### Alınan Kararlar

1. **Mock Data Stratejisi:** İlk 2 gün mock data ile çalış, Gün 3'te gerçek entegrasyon
2. **Council Basitleştirme:** MVP için tek tur konuşma yeterli
3. **PDF Erteleme:** Post-MVP'ye bırakıldı

### Açık Sorular

1. ~~KKB API rate limit var mı?~~ → ✅ Hayır, sınırsız
2. ~~TSG'de captcha var mı?~~ → ✅ EVET, Tesseract OCR ile çözüldü
3. Demo için hangi firmalar kullanılacak? → Belirlenmeli

---

> **Bu döküman canlı bir dökümandır.** Her gün güncellenir.
> Son güncelleme: 6 Aralık 2024
