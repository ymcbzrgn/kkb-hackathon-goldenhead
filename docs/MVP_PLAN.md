# MVP Plan - KKB Firma İstihbarat Sistemi

> **Teslim Tarihi:** 4 Gün Sonra
> **Son Güncelleme:** 6 Aralık 2024
> **PM:** Yamaç

---

## Mevcut Durum (6 Aralık 2024)

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
| **Agent Yapısı** | ✅ %60 | Base agent, orchestrator iskelet hazır |
| **Council Yapısı** | ✅ %70 | Personas, prompts, service iskelet hazır |
| **LLM Client** | ✅ %80 | Client, streaming, vision, embedding hazır |

### Eksik/TODO Listesi

```
Backend (Bartın):
├── reports.py      → Database CRUD (5 TODO)
├── companies.py    → Search, autocomplete (2 TODO)
├── pdf_export.py   → PDF oluşturma (1 TODO)
└── Celery tasks    → Background job (1 TODO)

AI/ML (Yamaç):
├── tsg_agent.py    → TSG scraping + Vision (3 TODO)
├── ihale_agent.py  → EKAP scraping (1 TODO)
├── news_agent.py   → Haber + Sentiment (2 TODO)
└── council_service → Tam implementasyon
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
| **Council Toplantısı** | 6 kişilik AI komite (BONUS!) | Orta |
| Council Streaming | Canlı konuşma gösterimi | Orta |
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
- [ ] TSG Agent GERÇEK veri çekiyor
- [ ] İhale Agent GERÇEK yasak kontrolü yapıyor
- [ ] Rapor DB'ye kaydediliyor

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
| | | | |

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

## Notlar ve Kararlar

### Alınan Kararlar

1. **Mock Data Stratejisi:** İlk 2 gün mock data ile çalış, Gün 3'te gerçek entegrasyon
2. **Council Basitleştirme:** MVP için tek tur konuşma yeterli
3. **PDF Erteleme:** Post-MVP'ye bırakıldı

### Açık Sorular

1. KKB API rate limit var mı?
2. TSG'de captcha var mı?
3. Demo için hangi firmalar kullanılacak?

---

> **Bu döküman canlı bir dökümandır.** Her gün güncellenir.
> Son güncelleme: 6 Aralık 2024, 00:51
