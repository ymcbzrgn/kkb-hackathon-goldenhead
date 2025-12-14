# 🏦 Firma İstihbarat Raporu Sistemi

> **KKB Agentic AI Hackathon 2024** - AI destekli firma analizi ve kredi risk değerlendirmesi

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](LICENSE)

---

## 📋 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Nasıl Çalışır](#-nasıl-çalışır)
- [Özellikler](#-özellikler)
- [Teknoloji Stack](#-teknoloji-stack)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Proje Yapısı](#-proje-yapısı)
- [Kredi Komitesi Detayları](#-kredi-komitesi-detayları)
- [Veritabanı](#-veritabanı)
- [Ekip](#-ekip)
- [Lisans](#-lisans)

---

## 🎯 Proje Hakkında

**Firma İstihbarat Raporu Sistemi**, kredi değerlendirme süreçlerini otomatize eden, yapay zeka destekli bir karar destek sistemidir.

### Problem

Geleneksel firma istihbaratı süreci:
- 📅 **Günler süren** manuel araştırma
- 📄 **Dağınık kaynaklardan** veri toplama
- 👥 **Öznel değerlendirmeler** ve tutarsız kararlar
- ⏰ **Yavaş karar süreçleri**

### Çözüm

Sistemimiz ile:
- ⚡ **Dakikalar içinde** kapsamlı istihbarat raporu
- 🤖 **3 AI Agent** paralel veri toplama
- 🏛️ **6 kişilik sanal komite** objektif değerlendirme
- 📊 **Tutarlı, ağırlıklı skorlama** sistemi

### Hedef Kullanıcılar

- 🏦 Bankalar ve finans kuruluşları
- 💼 Kredi değerlendirme departmanları
- 📈 Risk analizi ekipleri
- 🔍 Firma istihbaratı yapan kurumlar

---

## 🔄 Nasıl Çalışır

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KULLANICI GİRİŞİ                            │
│                                                                     │
│   [  Firma Adı: ACME Teknoloji A.Ş.  ]  [Hızlı Analiz] [Tam Analiz]│
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AŞAMA 1: VERİ TOPLAMA                          │
│                                                                     │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │  TSG Agent  │    │ İhale Agent │    │ News Agent  │            │
│   │   (90s)     │    │   (150s)    │    │   (150s)    │            │
│   │             │    │             │    │             │            │
│   │ ▪ Ticaret   │    │ ▪ Resmi     │    │ ▪ 10 Haber  │            │
│   │   Sicili    │    │   Gazete    │    │   Kaynağı   │            │
│   │ ▪ Vision AI │    │ ▪ Yasaklama │    │ ▪ Sentiment │            │
│   │ ▪ OCR       │    │   Kararları │    │   Analizi   │            │
│   └─────────────┘    └─────────────┘    └─────────────┘            │
│          │                  │                  │                    │
│          └──────────────────┼──────────────────┘                    │
│                             ▼                                       │
│                   [İstihbarat Raporu]                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   AŞAMA 2: KOMİTE DEĞERLENDİRMESİ                   │
│                                                                     │
│    🔴 Mehmet Bey     🟢 Ayşe Hanım     ⚖️ Av. Zeynep                │
│    Risk Analisti    İş Geliştirme     Hukuk Müşaviri               │
│    [SKOR: 65]       [SKOR: 28]        [SKOR: 42]                   │
│                                                                     │
│    📰 Deniz Bey     📊 Prof. Ali      👨‍⚖️ GMY                       │
│    İtibar Analisti  Sektör Uzmanı     Moderatör                    │
│    [SKOR: 38]       [SKOR: 35]        [SENTEZ]                     │
│                                                                     │
│    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            │
│                    TARTIŞMA (Real-time Streaming)                   │
│    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AŞAMA 3: FİNAL KARAR                           │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │                                                              │ │
│   │   FİNAL SKOR: 42/100        RİSK SEVİYESİ: ORTA             │ │
│   │                                                              │ │
│   │   KARAR: ✅ ŞARTLI ONAY                                      │ │
│   │                                                              │ │
│   │   KONSENSÜS: %78                                            │ │
│   │                                                              │ │
│   │   KOŞULLAR:                                                  │ │
│   │   • Teminat mektubu talep edilmeli                          │ │
│   │   • 6 aylık nakit akış projeksiyonu                         │ │
│   │   • Yıllık izleme                                           │ │
│   │                                                              │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│                      [📄 PDF İNDİR]  [🔄 YENİ RAPOR]               │
└─────────────────────────────────────────────────────────────────────┘
```

### Demo Mode vs Full Mode

| Özellik | Demo Mode | Full Mode |
|---------|-----------|-----------|
| **Toplam Süre** | ~4 dakika | Sınırsız |
| **TSG Tarama** | 90 saniye | 240 saniye |
| **Haber Arama** | 1 yıl, 5 haber/kaynak | 3 yıl, 15 haber/kaynak |
| **İhale Tarama** | 365 gün | 1095 gün (3 yıl) |
| **Komite Süresi** | ~5 dakika | ~15 dakika |
| **Kullanım** | Hızlı demo, test | Gerçek analiz |

---

## ✨ Özellikler

### 🤖 AI Agent'lar

#### 1. TSG Agent (Ticaret Sicili Gazetesi)

Ticaret Sicili Gazetesi'nden firma bilgilerini otomatik çıkarır.

**Yetenekler:**
- 🔐 Tesseract OCR ile CAPTCHA çözme
- 🌐 Otomatik TSG portal girişi
- 📰 Akıllı ilan seçimi (kuruluş/tescil öncelikli)
- 📸 Gazete sayfası screenshot
- 👁️ Vision AI ile gazete okuma (qwen3-omni-30b)

**Çıkarılan 8 Başlık:**

| # | Başlık | Açıklama |
|---|--------|----------|
| 1 | Firma Ünvanı | Şirketin tam resmi adı |
| 2 | Tescil Konusu | İşlem türü (kuruluş, sermaye artırımı vb.) |
| 3 | MERSİS Numarası | 16 haneli benzersiz numara |
| 4 | Yöneticiler | Yönetim kurulu üyeleri (array) |
| 5 | İmza Yetkilisi | Şirketi temsile yetkili kişi |
| 6 | Sermaye | Şirket sermayesi (örn: "10.000.000 TL") |
| 7 | Kuruluş Tarihi | Kuruluş tarihi (örn: "15.03.2018") |
| 8 | Faaliyet Konusu | Faaliyet alanı (kısa özet) |

---

#### 2. İhale Agent (Resmi Gazete Yasaklama Kararları)

Resmi Gazete'den firma hakkında yasaklama kararlarını arar.

**Yetenekler:**
- 📰 Resmi Gazete otomatik taraması
- 📄 PDF okuma (PyMuPDF + Tesseract OCR)
- 🔍 LLM ile firma eşleştirmesi
- ⚠️ Risk değerlendirmesi

**Çıkarılan 12 Başlık:**

| # | Başlık | Açıklama |
|---|--------|----------|
| 1 | yasak_durumu | true/false (aktif yasak var mı?) |
| 2 | yasak_kayit_no | Yasak kayıt numarası |
| 3 | ihale_kayit_no | İKN/ISKN numarası |
| 4 | yasaklayan_kurum | Karar veren bakanlık/kurum |
| 5 | ihale_idaresi | İhaleyi yapan idare |
| 6 | yasakli_kisi | Yasaklanan kişi bilgileri |
| 7 | ortaklar | Ortak bilgileri (array) |
| 8 | kanun_dayanagi | Kanun dayanağı (örn: "4735 Sayılı Kanun") |
| 9 | yasak_kapsami | "Tüm İhalelerden" veya "Belirli İhalelerden" |
| 10 | yasak_suresi | Süre (örn: "1 / YIL") |
| 11 | resmi_gazete | RG sayı ve tarih bilgisi |
| 12 | risk_degerlendirmesi | "dusuk" / "orta" / "yuksek" |

**Risk Kuralları:**
- ✅ Yasak yok → **Düşük Risk**
- ⚠️ Geçmiş yasak var, aktif yok → **Orta Risk**
- 🚨 Aktif yasak VAR → **Yüksek Risk** (KRİTİK!)

---

#### 3. News Agent (Haber Toplama + Sentiment)

10 farklı haber kaynağından firma haberlerini toplar ve duygu analizi yapar.

**Haber Kaynakları:**
- 📰 Sözcü
- 💼 Dünya Gazetesi
- 📺 Hürriyet
- 🇹🇷 Anadolu Ajansı
- 📡 NTV
- 💰 Ekonomim
- 📈 BigPara
- 📰 Milliyet
- 📺 CNN Türk
- 📻 TRT Haber

**Çıkarılan Bilgiler:**

```json
{
  "haberler": [
    {
      "baslik": "ACME Teknoloji 100 Milyon TL Yatırım Aldı",
      "url": "https://...",
      "kaynak": "Dünya",
      "tarih": "2024-01-15",
      "ozet": "Teknoloji şirketi yeni yatırım turunu kapattı...",
      "sentiment": "olumlu",
      "sentiment_score": 0.85
    }
  ],
  "ozet": {
    "toplam": 15,
    "olumlu": 10,
    "olumsuz": 2,
    "notr": 3,
    "sentiment_score": 0.65,
    "trend": "pozitif"
  }
}
```

---

### 🏛️ Kredi Komitesi (Council)

6 kişilik sanal kredi komitesi, toplanan verileri değerlendirir ve final kararı oluşturur.

#### Komite Üyeleri

| Emoji | İsim | Rol | Karakter | Skor Eğilimi | Ağırlık |
|-------|------|-----|----------|--------------|---------|
| 🔴 | **Mehmet Bey** | Baş Risk Analisti | Temkinli, şüpheci, detaycı | 50-70 | %30 |
| 🟢 | **Ayşe Hanım** | İş Geliştirme Müdürü | Fırsatçı, iyimser, büyüme odaklı | 20-35 | %15 |
| ⚖️ | **Av. Zeynep Hanım** | Hukuk Müşaviri | Tarafsız, belgeci, mevzuata hakim | 30-50 | %25 |
| 📰 | **Deniz Bey** | İtibar Analisti | Algı odaklı, sosyal medya takipçisi | 25-45 | %15 |
| 📊 | **Prof. Dr. Ali Bey** | Sektör Uzmanı | Makro bakışlı, akademik | 30-45 | %15 |
| 👨‍⚖️ | **GMY** | Komite Başkanı | Sentezci, karar odaklı | - | Moderatör |

#### Toplantı Akışı

```
1. 📢 AÇILIŞ
   └── GMY toplantıyı açar, gündem sunar

2. 🔴 RİSK SUNUMU
   └── Mehmet Bey risk faktörlerini analiz eder
   └── [SKOR VERİR: 0-100]

3. 🟢 İŞ SUNUMU
   └── Ayşe Hanım fırsatları değerlendirir
   └── [SKOR VERİR: 0-100]

4. ⚖️ HUKUK SUNUMU
   └── Av. Zeynep hukuki durumu inceler
   └── [SKOR VERİR: 0-100]

5. 📰 MEDYA SUNUMU
   └── Deniz Bey itibar analizini sunar
   └── [SKOR VERİR: 0-100]

6. 📊 SEKTÖR SUNUMU
   └── Prof. Ali makro perspektif sunar
   └── [SKOR VERİR: 0-100]

7. 💬 TARTIŞMA
   └── En farklı görüşler tartışılır
   └── Üyeler skorlarını revize edebilir

8. ✅ FİNAL KARAR
   └── GMY tüm görüşleri sentezler
   └── Ağırlıklı final skor hesaplanır
   └── Karar açıklanır
```

#### Karar Mekanizması

**Risk Seviyeleri:**
| Skor Aralığı | Risk Seviyesi |
|--------------|---------------|
| 0-20 | 🟢 Düşük |
| 21-40 | 🟡 Orta Düşük |
| 41-60 | 🟠 Orta |
| 61-80 | 🔴 Orta Yüksek |
| 81-100 | ⛔ Yüksek |

**Karar Çıktıları:**
| Final Skor | Karar |
|------------|-------|
| ≤30 | ✅ ONAY |
| 31-50 | ⚠️ ŞARTLI ONAY |
| 51-70 | 🔍 İNCELEME GEREK |
| 71+ | ❌ RED |
| Aktif İhale Yasağı | ❌ OTOMATİK RED |

---

### 🎨 Teknik Özellikler

- **⚡ Real-time WebSocket Streaming** - Komite konuşmaları canlı akış
- **🔄 Paralel Agent Çalıştırma** - 3 agent aynı anda veri toplar
- **📊 Rule-based + LLM-based Skorlama** - Hibrit değerlendirme
- **📄 PDF Rapor Export** - Profesyonel rapor çıktısı
- **🎭 Persona Tabanlı AI** - Her komite üyesi farklı karakter
- **🔒 Prompt Injection Koruması** - Güvenli input sanitization
- **💾 Kurumsal Hafıza** - Qdrant ile geçmiş kararlar
- **📱 Responsive UI** - Mobil uyumlu arayüz

---

## 🛠️ Teknoloji Stack

### Backend

| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| **Python** | 3.11+ | Ana programlama dili |
| **FastAPI** | 0.104+ | Web framework, REST API |
| **Celery** | 5.3+ | Async task queue |
| **SQLAlchemy** | 2.x | ORM, veritabanı işlemleri |
| **Alembic** | 1.12+ | Database migrations |
| **Playwright** | 1.40+ | Web scraping, browser automation |
| **Uvicorn** | 0.24+ | ASGI server |
| **httpx** | 0.25+ | Async HTTP client |
| **Pydantic** | 2.5+ | Data validation |

### Frontend

| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| **React** | 18.3+ | UI framework |
| **TypeScript** | 5.x | Type-safe development |
| **Vite** | 6.x | Build tool, HMR |
| **Tailwind CSS** | 3.4+ | Utility-first styling |
| **Zustand** | 5.x | Lightweight state management |
| **React Query** | 5.60+ | Server state, caching |
| **Framer Motion** | 11.11+ | Smooth animations |
| **Lucide React** | 0.460+ | Icon library |

### AI/ML

| Model | Provider | Kullanım |
|-------|----------|----------|
| **gpt-oss-120b** | KKB Kloudeks | Council konuşmaları, rapor yazma, sentiment analizi |
| **qwen3-omni-30b** | KKB Kloudeks | Vision AI - PDF ve görsel okuma |
| **qwen3-embedding-8b** | KKB Kloudeks | RAG için text embedding |

### Veritabanları

| Teknoloji | Versiyon | Kullanım |
|-----------|----------|----------|
| **PostgreSQL** | 15+ | Ana veritabanı (raporlar, firmalar) |
| **Redis** | 7+ | Cache, Celery broker, Pub/Sub |
| **Qdrant** | latest | Vector DB, kurumsal hafıza |

### DevOps

| Teknoloji | Kullanım |
|-----------|----------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **Kubernetes** | Production deployment (opsiyonel) |
| **Nginx** | Reverse proxy, static serving |
| **Makefile** | Build automation |

---

## 🏗️ Sistem Mimarisi

### Genel Mimari

```
                                    ┌─────────────────┐
                                    │    Kullanıcı    │
                                    │    (Browser)    │
                                    └────────┬────────┘
                                             │
                                             │ HTTP/WS
                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              NGINX                                      │
│                        (Reverse Proxy)                                  │
│   ┌──────────────────────┐    ┌──────────────────────────────────┐    │
│   │  Static Files (/)    │    │  API Proxy (/api, /ws)           │    │
│   │  React Build         │    │  Rate Limit: 10r/s, burst 20     │    │
│   └──────────────────────┘    └──────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
                                             │
                 ┌───────────────────────────┼───────────────────────────┐
                 │                           │                           │
                 ▼                           ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│       FRONTEND          │  │        BACKEND          │  │     CELERY WORKERS      │
│      (React 18)         │  │       (FastAPI)         │  │      (Python 3.11)      │
│                         │  │                         │  │                         │
│ ▪ Zustand stores        │  │ ▪ REST API endpoints    │  │ ▪ TSG Agent            │
│ ▪ React Query           │  │ ▪ WebSocket handler     │  │ ▪ İhale Agent          │
│ ▪ WebSocket client      │  │ ▪ Report service        │  │ ▪ News Agent           │
│ ▪ Framer Motion         │  │ ▪ Council service       │  │ ▪ Council Service      │
│                         │  │ ▪ PDF generator         │  │ ▪ Report Generator     │
│ Port: 5173 (dev)        │  │                         │  │                         │
│ Port: 80 (prod)         │  │ Port: 8000              │  │ Concurrency: 2         │
└─────────────────────────┘  └───────────┬─────────────┘  └───────────┬─────────────┘
                                         │                             │
                                         │         ┌───────────────────┘
                                         │         │
                                         ▼         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           DATABASES                                     │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │   PostgreSQL     │  │      Redis       │  │     Qdrant       │     │
│  │    (Port 5432)   │  │   (Port 6379)    │  │   (Port 6333)    │     │
│  │                  │  │                  │  │                  │     │
│  │ ▪ reports        │  │ ▪ Cache          │  │ ▪ companies      │     │
│  │ ▪ companies      │  │ ▪ Celery broker  │  │ ▪ decisions      │     │
│  │ ▪ agent_results  │  │ ▪ Pub/Sub        │  │ ▪ embeddings     │     │
│  │ ▪ council_data   │  │ ▪ Sessions       │  │                  │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │  KKB Kloudeks    │  │    TSG Portal    │  │   Resmi Gazete   │     │
│  │   (LLM API)      │  │  (tsg.gov.tr)    │  │ (resmigazete.    │     │
│  │                  │  │                  │  │     gov.tr)      │     │
│  │ ▪ gpt-oss-120b   │  │ ▪ Firma arama    │  │                  │     │
│  │ ▪ qwen3-omni-30b │  │ ▪ Gazete okuma   │  │ ▪ Yasaklama      │     │
│  │ ▪ qwen3-embed-8b │  │ ▪ PDF indirme    │  │   kararları      │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                     HABER KAYNAKLARI                          │     │
│  │  Sözcü | Dünya | Hürriyet | AA | NTV | Ekonomim | BigPara   │     │
│  │  Milliyet | CNN Türk | TRT Haber                              │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Veri Akışı

```
1. RAPOR TALEBİ
   User → POST /api/reports {company_name}
                    │
                    ▼
2. JOB OLUŞTURMA
   Backend → Celery Task Queue
                    │
                    ▼
3. AGENT ORKESTRASYONU
   ┌─────────────────────────────────────────────┐
   │           ORCHESTRATOR                       │
   │                                              │
   │   [AŞAMA 1] TSG Agent (90s)                 │
   │        │                                     │
   │        ▼ (Firma ünvanı bulunursa)           │
   │   [AŞAMA 2] News + İhale (paralel, 150s)   │
   │        │                                     │
   │        ▼                                     │
   │   [AŞAMA 3] İstihbarat Raporu (Rule-based) │
   │        │                                     │
   │        ▼                                     │
   │   [AŞAMA 4] Council Toplantısı             │
   └─────────────────────────────────────────────┘
                    │
                    ▼
4. REAL-TIME UPDATES
   Celery → Redis Pub/Sub → WebSocket → Frontend
                    │
                    ▼
5. FİNAL RAPOR
   Backend → PostgreSQL → GET /api/reports/{id}
```

### WebSocket Events

| Event | Yön | Açıklama |
|-------|-----|----------|
| `job_started` | Server → Client | Job başladı |
| `agent_started` | Server → Client | Agent çalışmaya başladı |
| `agent_progress` | Server → Client | Agent ilerleme (%0-100) |
| `agent_completed` | Server → Client | Agent tamamlandı |
| `agent_failed` | Server → Client | Agent hata aldı |
| `council_started` | Server → Client | Komite toplantısı başladı |
| `council_phase_changed` | Server → Client | Toplantı aşaması değişti |
| `council_speaker_changed` | Server → Client | Konuşmacı değişti |
| `council_speech` | Server → Client | Konuşma (streaming chunks) |
| `council_score_given` | Server → Client | Skor verildi |
| `council_decision` | Server → Client | Final karar açıklandı |
| `job_completed` | Server → Client | Tüm süreç tamamlandı |

---

## 📦 Kurulum

### Gereksinimler

- **Docker** & **Docker Compose** (önerilen)
- **Node.js** 20+ (frontend development)
- **Python** 3.11+ (backend development)
- **PostgreSQL** 15+ (database)
- **Redis** 7+ (cache & broker)

### Hızlı Başlangıç (Docker)

```bash
# 1. Repository'yi klonla
git clone https://github.com/ymcbzrgn/kkb-hackathon-goldenhead.git
cd kkb-hackathon-goldenhead

# 2. Environment variables ayarla
cp .env.example .env

# .env dosyasını düzenle ve KKB API key'i ekle:
# KKB_API_KEY=sk-your-api-key-here

# 3. Docker ile tüm servisleri başlat
make dev

# 4. Tarayıcıda aç
# Frontend:  http://localhost:5173
# Backend:   http://localhost:8000
# Swagger:   http://localhost:8000/docs
# pgAdmin:   http://localhost:5050
# Qdrant UI: http://localhost:6333/dashboard
```

### Manuel Kurulum

#### Backend

```bash
# 1. Backend klasörüne git
cd backend

# 2. Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Dependencies yükle
pip install -r requirements.txt

# 4. Playwright browser'larını yükle
playwright install chromium

# 5. Environment variables
cp .env.example .env
# .env dosyasını düzenle

# 6. Database'i hazırla
# PostgreSQL çalışıyor olmalı
alembic upgrade head

# 7. Backend'i başlat
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 8. Celery worker başlat (ayrı terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

#### Frontend

```bash
# 1. Frontend klasörüne git
cd frontend

# 2. Dependencies yükle
npm install

# 3. Development server başlat
npm run dev

# Frontend http://localhost:5173 adresinde çalışacak
```

### Environment Variables

#### Root `.env`

```env
# Database
DATABASE_URL=postgresql://kkb:hackathon2024@localhost:5432/firma_istihbarat

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# KKB Kloudeks LLM API
KKB_API_URL=https://mia.csp.kloudeks.com/v1
KKB_API_KEY=sk-your-api-key-here

# Application Settings
DEBUG=true
LOG_LEVEL=INFO

# CORS (virgülle ayrılmış origin'ler)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### Makefile Komutları

```bash
# Kurulum
make setup          # İlk kurulum
make install        # Tüm dependencies

# Development
make dev            # Tüm stack (Docker)
make dev-services   # Sadece veritabanları
make dev-backend    # Backend (uvicorn)
make dev-frontend   # Frontend (vite)

# Database
make db-migrate     # Alembic migrations
make db-seed        # Test verisi ekle
make db-reset       # Sıfırdan başla

# Vector DB
make qdrant-init    # Koleksiyonları oluştur
make qdrant-list    # Koleksiyonları listele

# Test & Lint
make test           # Tüm testler
make lint           # Tüm linter'lar

# Utilities
make logs           # Docker logları
make clean          # Temizlik
make shell-backend  # Backend container shell
make shell-db       # PostgreSQL shell
```

---

## 🚀 Kullanım

### Yeni Rapor Oluşturma

1. **Ana sayfayı aç**: `http://localhost:5173`

2. **Firma adını gir**: Arama kutusuna firma adını yaz
   - Örnek: "ACME Teknoloji A.Ş."

3. **Analiz türünü seç**:
   - **Hızlı Analiz**: ~4 dakika, demo için ideal
   - **Tam Analiz**: Kapsamlı, gerçek kullanım için

4. **Süreci takip et**:
   - Agent'ların veri toplamasını izle
   - Komite tartışmasını canlı takip et
   - Final kararı gör

5. **Raporu indir**: PDF olarak kaydet

### Demo Mode Kullanımı

Demo mode, hackathon sunumları ve hızlı testler için optimize edilmiştir:

- **Toplam süre**: ~4 dakika
- **Kısaltılmış taramalar**: Daha az kaynak, daha hızlı sonuç
- **Streaming hızı artırılmış**: Daha dinamik görünüm

```bash
# Demo mode varsayılan olarak "Hızlı Analiz" butonuyla aktif olur
```

### Rapor Listesi

- `http://localhost:5173/reports` adresinden tüm raporlara erişin
- Durum filtresi: Bekliyor, İşleniyor, Tamamlandı, Başarısız
- Arama: Firma adına göre filtrele
- Aksiyonlar: Görüntüle, Canlı İzle, Sil

---

## 📚 API Dokümantasyonu

### Base URL

```
http://localhost:8000/api
```

### Swagger UI

Interactive API dokümantasyonu:
```
http://localhost:8000/docs
```

### Endpoints

#### Raporlar

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `POST` | `/reports` | Yeni rapor oluştur |
| `GET` | `/reports` | Rapor listesi (paginated) |
| `GET` | `/reports/{id}` | Rapor detayı |
| `GET` | `/reports/{id}/pdf` | PDF indir |
| `DELETE` | `/reports/{id}` | Rapor sil |

#### Firmalar

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/companies/search` | Firma arama (autocomplete) |

#### Sistem

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/health` | Health check |

### Örnek İstekler

#### Yeni Rapor Oluştur

```bash
curl -X POST "http://localhost:8000/api/reports" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "ACME Teknoloji A.Ş.",
    "company_tax_no": "1234567890",
    "demo_mode": true
  }'
```

**Response:**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "websocket_url": "ws://localhost:8000/ws/550e8400-e29b-41d4-a716-446655440000"
}
```

#### Rapor Listesi

```bash
curl "http://localhost:8000/api/reports?page=1&limit=10&status=completed"
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "company_name": "ACME Teknoloji A.Ş.",
      "status": "completed",
      "final_score": 42,
      "risk_level": "orta",
      "decision": "sartli_onay",
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:34:30Z",
      "duration_seconds": 270
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

#### Rapor Detayı

```bash
curl "http://localhost:8000/api/reports/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_name": "ACME Teknoloji A.Ş.",
  "company_tax_no": "1234567890",
  "status": "completed",
  "final_score": 42,
  "risk_level": "orta",
  "decision": "sartli_onay",
  "tsg_data": {
    "firma_unvani": "ACME TEKNOLOJİ ANONİM ŞİRKETİ",
    "mersis_no": "0123456789012345",
    "sermaye": "10.000.000 TL",
    "kurulus_tarihi": "15.03.2018",
    "yoneticiler": ["Ahmet YILMAZ", "Mehmet KAYA"],
    "imza_yetkilisi": "Ahmet YILMAZ",
    "faaliyet_konusu": "Yazılım geliştirme ve danışmanlık"
  },
  "ihale_data": {
    "yasak_durumu": false,
    "risk_degerlendirmesi": "dusuk"
  },
  "news_data": {
    "toplam": 15,
    "olumlu": 10,
    "olumsuz": 2,
    "sentiment_score": 0.65,
    "trend": "pozitif"
  },
  "council_data": {
    "final_score": 42,
    "risk_level": "orta",
    "decision": "sartli_onay",
    "consensus": 0.78,
    "conditions": [
      "Teminat mektubu talep edilmeli",
      "6 aylık nakit akış projeksiyonu"
    ],
    "scores": {
      "risk_analyst": 65,
      "business_analyst": 28,
      "legal_expert": 42,
      "media_analyst": 38,
      "sector_expert": 35
    },
    "transcript": [...]
  },
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:34:30Z"
}
```

### WebSocket Bağlantısı

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/REPORT_ID');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.event) {
    case 'agent_progress':
      console.log(`${data.agent_id}: ${data.progress}%`);
      break;
    case 'council_speech':
      console.log(`${data.speaker}: ${data.chunk}`);
      break;
    case 'council_decision':
      console.log(`Final: ${data.final_score}, Karar: ${data.decision}`);
      break;
  }
};
```

---

## 📁 Proje Yapısı

```
kkb-hackathon-goldenhead/
│
├── 📂 frontend/                      # React Frontend
│   ├── 📂 src/
│   │   ├── 📂 components/           # React bileşenleri
│   │   │   ├── 📂 layout/          # Header, Footer, MainLayout
│   │   │   ├── 📂 landing/         # Hero, SearchForm, AgentCards
│   │   │   ├── 📂 council/         # Komite UI bileşenleri
│   │   │   ├── 📂 live/            # Live session bileşenleri
│   │   │   ├── 📂 reports/         # Rapor listesi
│   │   │   ├── 📂 report-detail/   # Rapor detay
│   │   │   └── 📂 ui/              # Base UI components
│   │   ├── 📂 pages/               # Sayfa bileşenleri
│   │   ├── 📂 hooks/               # Custom React hooks
│   │   ├── 📂 stores/              # Zustand state stores
│   │   ├── 📂 services/            # API & WebSocket clients
│   │   ├── 📂 types/               # TypeScript definitions
│   │   ├── 📂 utils/               # Helpers, formatters
│   │   └── 📄 App.tsx              # Root component
│   ├── 📄 package.json
│   ├── 📄 tailwind.config.js
│   ├── 📄 tsconfig.json
│   └── 📄 vite.config.ts
│
├── 📂 backend/                       # FastAPI Backend
│   ├── 📂 app/
│   │   ├── 📂 agents/              # AI Agent'lar
│   │   │   ├── 📄 base_agent.py   # Base Agent sınıfı
│   │   │   ├── 📄 orchestrator.py # Agent koordinatörü
│   │   │   ├── 📂 tsg/            # TSG Agent
│   │   │   │   ├── 📄 agent.py
│   │   │   │   ├── 📄 scraper.py
│   │   │   │   └── 📄 ocr.py
│   │   │   ├── 📂 ihale/          # İhale Agent
│   │   │   │   ├── 📄 agent.py
│   │   │   │   ├── 📄 scraper.py
│   │   │   │   └── 📄 pdf_reader.py
│   │   │   └── 📂 news/           # News Agent
│   │   │       ├── 📄 agent.py
│   │   │       └── 📂 sources/    # Haber kaynakları
│   │   │
│   │   ├── 📂 council/             # Komite Servisi
│   │   │   ├── 📄 council_service.py
│   │   │   ├── 📄 personas.py     # Komite üyeleri
│   │   │   └── 📂 prompts/        # System prompts
│   │   │       ├── 📄 risk_analyst.py
│   │   │       ├── 📄 business_analyst.py
│   │   │       ├── 📄 legal_expert.py
│   │   │       ├── 📄 media_analyst.py
│   │   │       ├── 📄 sector_expert.py
│   │   │       └── 📄 moderator.py
│   │   │
│   │   ├── 📂 llm/                 # LLM Entegrasyonu
│   │   │   ├── 📄 client.py       # KKB API wrapper
│   │   │   ├── 📄 models.py       # Model configs
│   │   │   └── 📄 utils.py
│   │   │
│   │   ├── 📂 api/                 # REST API
│   │   │   ├── 📂 routes/
│   │   │   │   └── 📄 reports.py
│   │   │   └── 📄 websocket.py
│   │   │
│   │   ├── 📂 services/            # Business Logic
│   │   │   ├── 📄 report_generator.py
│   │   │   └── 📄 redis_pubsub.py
│   │   │
│   │   ├── 📂 models/              # SQLAlchemy Models
│   │   │   └── 📄 report.py
│   │   │
│   │   ├── 📂 workers/             # Celery Tasks
│   │   │   └── 📄 agent_tasks.py
│   │   │
│   │   └── 📂 core/                # Core Config
│   │       ├── 📄 config.py
│   │       └── 📄 database.py
│   │
│   ├── 📂 sql/                     # Database Scripts
│   │   ├── 📄 schema.sql
│   │   ├── 📄 indexes.sql
│   │   └── 📄 seed.sql
│   │
│   ├── 📂 scrapers/                # Microservices
│   │   ├── 📂 tsg-scraper/
│   │   ├── 📂 ihale-scraper/
│   │   └── 📂 universal-scraper/
│   │
│   ├── 📂 k8s/                     # Kubernetes Manifests
│   │
│   ├── 📄 main.py                  # FastAPI entrypoint
│   └── 📄 requirements.txt
│
├── 📂 docker/                        # Docker Configs
│   ├── 📄 Dockerfile.backend
│   ├── 📄 Dockerfile.frontend
│   ├── 📄 Dockerfile.pdf-downloader
│   ├── 📄 docker-compose.yml
│   ├── 📄 docker-compose.dev.yml
│   └── 📂 nginx/
│       └── 📄 nginx.conf
│
├── 📂 docs/                          # Dokümantasyon
│   ├── 📄 ARCHITECTURE-2.md
│   ├── 📄 API.md
│   ├── 📄 DATABASE.md
│   └── 📄 DEPLOYMENT.md
│
├── 📂 scripts/                       # Utility Scripts
│   ├── 📄 setup.sh
│   ├── 📄 deploy.sh
│   ├── 📄 seed_db.py
│   └── 📄 init_qdrant.py
│
├── 📂 shared/                        # Shared Schemas
│   └── 📂 schemas/
│
├── 📄 .env.example
├── 📄 Makefile
└── 📄 README.md                     # Bu dosya
```

---

## 🏛️ Kredi Komitesi Detayları

### Üye Karakterleri

#### 🔴 Mehmet Bey (Baş Risk Analisti)

**Deneyim:** 25 yıl bankacılık
**Karakter:** Temkinli, şüpheci, detaycı
**Yaklaşım:** "En kötü senaryo ne olabilir?"

**Konuşma Tarzı:**
- Rakamlarla konuşur
- Her zaman risk faktörlerini vurgular
- Diğer üyelerin iyimserliğini dengeler
- Somut veriler ister

**Skor Eğilimi:** 50-70 (temkinli)
**Ağırlık:** %30 (en yüksek)

---

#### 🟢 Ayşe Hanım (İş Geliştirme Müdürü)

**Deneyim:** 15 yıl iş geliştirme
**Karakter:** Fırsatçı, iyimser, büyüme odaklı
**Yaklaşım:** "Bu firmada nasıl bir potansiyel var?"

**Konuşma Tarzı:**
- Fırsatları ön plana çıkarır
- Büyüme potansiyelini değerlendirir
- Pozitif senaryoları vurgular
- İş hacmi ve getiri odaklı

**Skor Eğilimi:** 20-35 (iyimser)
**Ağırlık:** %15

---

#### ⚖️ Av. Zeynep Hanım (Hukuk Müşaviri)

**Deneyim:** 20 yıl finans hukuku
**Karakter:** Tarafsız, belgeci, mevzuata hakim
**Yaklaşım:** "Hukuki çerçeve ne diyor?"

**Konuşma Tarzı:**
- Kanun ve yönetmeliklere atıf yapar
- Belge ve tescil durumunu önemser
- Tarafsız ve objektif değerlendirme
- Potansiyel hukuki riskleri belirtir

**Skor Eğilimi:** 30-50 (dengeli)
**Ağırlık:** %25 (yüksek)

---

#### 📰 Deniz Bey (İtibar Analisti)

**Deneyim:** 12 yıl itibar yönetimi
**Karakter:** Algı odaklı, sosyal medya takipçisi
**Yaklaşım:** "Kamuoyunda nasıl algılanıyor?"

**Konuşma Tarzı:**
- Medya görünürlüğünü değerlendirir
- Sosyal medya trendlerini takip eder
- İtibar risklerini öne çıkarır
- Algı yönetimi perspektifi

**Skor Eğilimi:** 25-45
**Ağırlık:** %15

---

#### 📊 Prof. Dr. Ali Bey (Sektör Uzmanı)

**Deneyim:** 30 yıl akademi + danışmanlık
**Karakter:** Makro bakışlı, akademik, veri odaklı
**Yaklaşım:** "Sektör dinamikleri neler?"

**Konuşma Tarzı:**
- Makroekonomik perspektif sunar
- Sektör karşılaştırmaları yapar
- Akademik ve analitik dil
- Trend analizleri

**Skor Eğilimi:** 30-45
**Ağırlık:** %15

---

#### 👨‍⚖️ GMY (Komite Başkanı / Moderatör)

**Deneyim:** 35 yıl bankacılık yönetimi
**Karakter:** Sentezci, karar odaklı, dengeleyici
**Yaklaşım:** "Tüm görüşleri değerlendirelim"

**Konuşma Tarzı:**
- Toplantıyı yönetir
- Tüm görüşleri dinler ve sentezler
- Konsensüs arar
- Final kararı açıklar

**Skor:** Skor vermez, sentez yapar
**Rol:** Moderatör

---

### Skor Hesaplama Algoritması

```python
# Ağırlıklar
weights = {
    "risk_analyst": 0.30,      # Mehmet Bey
    "legal_expert": 0.25,      # Av. Zeynep
    "business_analyst": 0.15,  # Ayşe Hanım
    "media_analyst": 0.15,     # Deniz Bey
    "sector_expert": 0.15,     # Prof. Ali
}

# Ağırlıklı ortalama
final_score = sum(
    scores[member] * weights[member]
    for member in weights
)

# Konsensüs hesaplama (0-1 arası)
# Düşük standart sapma = yüksek konsensüs
values = list(scores.values())
avg = sum(values) / len(values)
variance = sum((x - avg) ** 2 for x in values) / len(values)
std_dev = sqrt(variance)
consensus = 1 - (std_dev / 50)  # Normalize
consensus = max(0, min(1, consensus))
```

---

## 💾 Veritabanı

### PostgreSQL Şeması

#### reports (Ana Tablo)

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `id` | UUID | Primary key |
| `company_name` | VARCHAR(255) | Firma adı |
| `company_tax_no` | VARCHAR(20) | Vergi numarası |
| `status` | ENUM | pending, processing, completed, failed |
| `final_score` | INTEGER | Final risk skoru (0-100) |
| `risk_level` | ENUM | dusuk, orta_dusuk, orta, orta_yuksek, yuksek |
| `decision` | ENUM | onay, sartli_onay, inceleme_gerek, red |
| `tsg_data` | JSONB | TSG Agent sonuçları |
| `ihale_data` | JSONB | İhale Agent sonuçları |
| `news_data` | JSONB | News Agent sonuçları |
| `council_data` | JSONB | Komite verileri ve transcript |
| `created_at` | TIMESTAMP | Oluşturulma zamanı |
| `completed_at` | TIMESTAMP | Tamamlanma zamanı |
| `duration_seconds` | INTEGER | Toplam süre (saniye) |

#### companies (Firma Cache)

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(255) | Firma adı |
| `tax_no` | VARCHAR(20) | Vergi numarası (unique) |
| `sector` | VARCHAR(100) | Sektör |
| `cached_data` | JSONB | Cache edilmiş veriler |
| `total_reports` | INTEGER | Toplam rapor sayısı |

#### agent_results (Agent Sonuçları)

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `id` | UUID | Primary key |
| `report_id` | UUID | Foreign key → reports |
| `agent_id` | VARCHAR(50) | Agent tipi |
| `status` | ENUM | pending, running, completed, failed |
| `data` | JSONB | Agent sonuçları |
| `duration_seconds` | INTEGER | Çalışma süresi |

### Qdrant Koleksiyonları

| Koleksiyon | Boyut | Kullanım |
|------------|-------|----------|
| `companies` | 1536 | Firma embedding'leri |
| `decisions` | 1536 | Geçmiş karar embedding'leri |

### Redis Kullanımı

| Key Pattern | TTL | Kullanım |
|-------------|-----|----------|
| `session:{id}` | 24h | WebSocket session |
| `cache:company:{tax}` | 1h | Firma cache |
| `pubsub:report:{id}` | - | Real-time events |

---

## 👥 Ekip

### GoldenHead Team

| Kişi | Rol | Sorumluluk Alanı |
|------|-----|------------------|
| **Yamaç** | Tech Lead & AI/ML Engineer | Proje yönetimi, AI Agent'lar, Council servisi, LLM entegrasyonu, DevOps, Docker, Kubernetes, Qdrant, Dokümantasyon, Sistem mimarisi |
| **Bekir** | Frontend Developer | React UI, WebSocket entegrasyonu, UX/UI tasarımı |
| **Bartın** | Backend Developer | FastAPI, PostgreSQL, REST API |

### İletişim

- **Proje Repository:** [GitHub](https://github.com/ymcbzrgn/kkb-hackathon-goldenhead)
- **Hackathon:** KKB Agentic AI Hackathon 2024

---

## 🤝 Katkıda Bulunma

1. **Fork** yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'e push edin (`git push origin feature/amazing-feature`)
5. **Pull Request** açın

### Code Style

- **Python:** Ruff ile format ve lint
- **TypeScript:** ESLint + Prettier
- **Commit Convention:** Conventional Commits

---

## 📄 Lisans

Bu proje **Apache License 2.0** altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- **KKB (Kredi Kayıt Bürosu)** - Hackathon organizasyonu
- **Kloudeks** - LLM API sağlayıcısı
- **Tüm katılımcılar** - İlham verici projeler

---

<div align="center">

**⭐ Bu projeyi beğendiyseniz yıldız vermeyi unutmayın! ⭐**

Made with ❤️ by **GoldenHead Team** for **KKB Agentic AI Hackathon 2024**

</div>
