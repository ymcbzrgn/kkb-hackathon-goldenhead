# 🏢 Firma İstihbarat Raporu - Frontend

> **Takım:** GoldenHead  
> **Hackathon:** KKB Agentic AI Hackathon 2024  
> **Geliştirici:** Bekir (Frontend)  
> **Branch:** `dev/bekir`

---

## 📋 İçindekiler

- [Proje Özeti](#-proje-özeti)
- [Teknoloji Stack](#-teknoloji-stack)
- [KKB Renk Paleti](#-kkb-renk-paleti)
- [Sayfa Yapısı](#-sayfa-yapısı-routes)
- [Klasör Yapısı](#-klasör-yapısı)
- [Mock Sistemi](#-mock-sistemi)
- [WebSocket Akışı](#-websocket-akışı)
- [Komutlar](#-komutlar)
- [Komite Üyeleri](#-komite-üyeleri)
- [Türkçe Çeviriler](#-türkçe-çeviriler)

---

## 🎯 Proje Özeti

### Ne Yapıyoruz?

Bir banka/finans kurumu için **Firma Risk Değerlendirme Sistemi** geliştiriyoruz:

1. **Kullanıcı** bir firma adı girer
2. **3 AI Agent** paralel çalışarak veri toplar (~5 dk):
   - 📰 **TSG Agent:** Ticaret Sicili Gazetesi'nden firma bilgileri
   - 🚫 **İhale Agent:** EKAP'tan ihale yasağı kontrolü
   - 📺 **Haber Agent:** İnternet haberlerinden sentiment analizi
3. **6 Kişilik Sanal Kredi Komitesi (Council)** tartışarak karar verir (~35 dk)
4. **Çıktı:** Risk Skoru (0-100), Karar (Onay/Şartlı/Red), Komite Tartışma Transcript'i

### Bekir'in Sorumluluğu

| Alan | Açıklama |
|------|----------|
| **Frontend** | React + TypeScript ile tüm UI |
| **WebSocket Client** | Gerçek zamanlı event dinleme |
| **Mock System** | Backend olmadan test |
| **Animasyonlar** | Council konuşmaları için Framer Motion |

### ⚠️ Kritik Kurallar

- ❌ API.md dışına çıkma
- ❌ Ekstra özellik ekleme
- ❌ Backend'siz gerçek API çağrısı yapma
- ✅ Mock mode ile geliştir
- ✅ Her adımda test et
- ✅ Onay almadan ilerleme

---

## 🛠 Teknoloji Stack

| Teknoloji | Versiyon | Amaç |
|-----------|----------|------|
| **Vite** | ^6.0 | Build tool, hızlı HMR |
| **React** | ^18.3 | UI Framework |
| **TypeScript** | ^5.6 | Type safety |
| **Tailwind CSS** | ^3.4 | Utility-first CSS |
| **shadcn/ui** | latest | UI Component Library |
| **React Router** | ^6.28 | Client-side routing |
| **Zustand** | ^5.0 | State management |
| **React Query** | ^5.60 | Server state, caching |
| **Framer Motion** | ^11.11 | Animasyonlar |
| **Lucide React** | ^0.460 | İkon seti |

---

## 🎨 KKB Renk Paleti

### Ana Renkler (Logo'dan)

| Renk | Hex | CSS Variable | Kullanım |
|------|-----|--------------|----------|
| 🔵 **Navy Blue** | `#1B365D` | `kkb-900` | Ana arka plan, başlıklar |
| 🟠 **Orange** | `#F7941D` | `accent-500` | CTA, vurgular, aksan |
| ⚪ **White** | `#FFFFFF` | `white` | Metin, kartlar |

### Genişletilmiş Palet

```css
/* Primary - Navy Blue */
--kkb-50: #f0f4f8;
--kkb-100: #d9e2ec;
--kkb-200: #bcccdc;
--kkb-300: #9fb3c8;
--kkb-400: #829ab1;
--kkb-500: #627d98;
--kkb-600: #486581;
--kkb-700: #334e68;
--kkb-800: #243b53;
--kkb-900: #1B365D;  /* Ana primary */
--kkb-950: #0F1F3D;

/* Accent - Orange */
--accent-50: #fff8f1;
--accent-100: #feecdc;
--accent-200: #fcd9bd;
--accent-300: #fdba8c;
--accent-400: #ff8a4c;
--accent-500: #F7941D;  /* Ana accent */
--accent-600: #E07B00;
--accent-700: #b45309;
```

### Risk Seviyeleri

| Seviye | Türkçe | Renk | Hex |
|--------|--------|------|-----|
| `dusuk` | Düşük Risk | 🟢 Yeşil | `#22C55E` |
| `orta_dusuk` | Orta-Düşük Risk | 🟢 Açık Yeşil | `#84CC16` |
| `orta` | Orta Risk | 🟡 Sarı | `#F59E0B` |
| `orta_yuksek` | Orta-Yüksek Risk | 🟠 Turuncu | `#F97316` |
| `yuksek` | Yüksek Risk | 🔴 Kırmızı | `#EF4444` |

### Karar Renkleri

| Karar | Türkçe | Renk | Hex |
|-------|--------|------|-----|
| `onay` | Onay | 🟢 Yeşil | `#22C55E` |
| `sartli_onay` | Şartlı Onay | 🟡 Sarı | `#F59E0B` |
| `red` | Red | 🔴 Kırmızı | `#EF4444` |
| `inceleme_gerek` | İnceleme Gerekli | 🔵 Mavi | `#3B82F6` |

---

## 🗺 Sayfa Yapısı (Routes)

| Route | Sayfa | Açıklama |
|-------|-------|----------|
| `/` | **Landing** | Vitrin sayfası, ürün tanıtımı, "Rapor Oluştur" formu |
| `/reports` | **Reports List** | Tüm raporlar, filtreleme, pagination |
| `/reports/:id` | **Report Detail** | Tamamlanmış rapor detayı, PDF indirme |
| `/reports/:id/live` | **Live Session** | Canlı agent akışı + Council toplantısı |

### Sayfa Akışı

```
┌─────────────────────────────────────────────────────────────────┐
│                         KULLANICI AKIŞI                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [/] Landing ──────────────────────────────────────────────────►│
│       │                                                          │
│       │ "Rapor Oluştur" butonu                                  │
│       ▼                                                          │
│  POST /api/reports ─────────────────────────────────────────────►│
│       │                                                          │
│       │ report_id alındı                                        │
│       ▼                                                          │
│  [/reports/:id/live] Live Session ──────────────────────────────►│
│       │                                                          │
│       │ WebSocket bağlantısı                                    │
│       │ Agent'lar çalışıyor...                                  │
│       │ Council toplantısı...                                   │
│       │ job_completed event                                     │
│       ▼                                                          │
│  [/reports/:id] Report Detail ──────────────────────────────────►│
│       │                                                          │
│       │ Rapor görüntüleme                                       │
│       │ PDF indirme                                             │
│       ▼                                                          │
│  [/reports] Reports List ◄──────────────────────────────────────│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Klasör Yapısı

```
frontend/
├── public/
│   ├── kkb-logo.svg           # KKB logosu
│   └── favicon.ico
│
├── src/
│   ├── components/
│   │   ├── ui/                # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── badge.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/            # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── PageContainer.tsx
│   │   │
│   │   ├── landing/           # Landing page components
│   │   │   ├── Hero.tsx
│   │   │   ├── SearchForm.tsx
│   │   │   ├── AgentCards.tsx
│   │   │   └── CouncilIntro.tsx
│   │   │
│   │   ├── reports/           # Reports list components
│   │   │   ├── ReportCard.tsx
│   │   │   ├── ReportList.tsx
│   │   │   ├── ReportFilters.tsx
│   │   │   ├── Pagination.tsx
│   │   │   └── StatusBadge.tsx
│   │   │
│   │   ├── report-detail/     # Report detail components
│   │   │   ├── FinalDecision.tsx
│   │   │   ├── RiskGauge.tsx
│   │   │   ├── ConsensusBar.tsx
│   │   │   ├── ConditionsList.tsx
│   │   │   ├── AgentResults.tsx
│   │   │   └── TranscriptAccordion.tsx
│   │   │
│   │   ├── live/              # Live session components
│   │   │   ├── LiveIndicator.tsx
│   │   │   ├── Timer.tsx
│   │   │   ├── PhaseStepper.tsx
│   │   │   ├── AgentProgress.tsx
│   │   │   └── AgentStatusCard.tsx
│   │   │
│   │   └── council/           # Council UI components
│   │       ├── CouncilContainer.tsx
│   │       ├── SpeakerAvatar.tsx
│   │       ├── SpeechBubble.tsx
│   │       ├── StreamingText.tsx
│   │       ├── ScoreBoard.tsx
│   │       ├── ScoreRevision.tsx
│   │       └── FinalDecisionCard.tsx
│   │
│   ├── pages/
│   │   ├── Landing.tsx        # /
│   │   ├── Reports.tsx        # /reports
│   │   ├── ReportDetail.tsx   # /reports/:id
│   │   └── LiveSession.tsx    # /reports/:id/live
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts    # WebSocket connection
│   │   ├── useReport.ts       # Single report operations
│   │   ├── useReports.ts      # Reports list
│   │   ├── useCouncil.ts      # Council state
│   │   └── useAgents.ts       # Agent progress
│   │
│   ├── stores/
│   │   ├── reportStore.ts     # Zustand - Report state
│   │   ├── agentStore.ts      # Zustand - Agent state
│   │   ├── councilStore.ts    # Zustand - Council state
│   │   └── uiStore.ts         # Zustand - UI state
│   │
│   ├── services/
│   │   ├── api.ts             # REST API client
│   │   ├── websocket.ts       # WebSocket client
│   │   └── pdf.ts             # PDF download
│   │
│   ├── mocks/
│   │   ├── mockApi.ts         # Mock REST responses
│   │   ├── mockWebSocket.ts   # Mock WS events
│   │   ├── mockData.ts        # Sample data
│   │   └── mockScenarios.ts   # Test scenarios
│   │
│   ├── types/
│   │   ├── api.ts             # API response types
│   │   ├── report.ts          # Report types
│   │   ├── agent.ts           # Agent types
│   │   ├── council.ts         # Council types
│   │   └── websocket.ts       # WebSocket event types
│   │
│   ├── utils/
│   │   ├── constants.ts       # Constants, labels
│   │   ├── formatters.ts      # Date, money formatters
│   │   ├── helpers.ts         # Helper functions
│   │   ├── cn.ts              # className utility
│   │   └── animations.ts      # Framer Motion presets
│   │
│   ├── styles/
│   │   └── globals.css        # Tailwind + custom CSS
│   │
│   ├── App.tsx                # Main app with routes
│   ├── main.tsx               # Entry point
│   └── vite-env.d.ts          # Vite types
│
├── .env                       # Environment variables
├── .env.example               # Example env file
├── index.html                 # HTML template
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── README-BEKIR.md            # Bu dosya
└── ROADMAP-BEKIR.md           # Geliştirme roadmap
```

---

## 🎭 Mock Sistemi

### Neden Mock Kullanıyoruz?

- Backend henüz hazır değil
- UI'ı bağımsız test edebilmek
- Demo senaryoları oluşturmak
- Hızlı geliştirme

### Mock Mode Açma/Kapama

```bash
# .env dosyasında:
VITE_USE_MOCK=true   # Mock mode (default)
VITE_USE_MOCK=false  # Gerçek API
```

### Mock Senaryolar

| Senaryo | Açıklama | Test Amacı |
|---------|----------|------------|
| `HAPPY_PATH` | Her şey başarılı | Normal akış |
| `AGENT_FAIL` | Bir agent hata alır | Hata UI |
| `LONG_COUNCIL` | Uzun komite tartışması | Animasyonlar |
| `QUICK_DECISION` | Hızlı karar | Performance |
| `SCORE_REVISION` | Skor revizyonu var | Revizyon animasyonu |

---

## 🔌 WebSocket Akışı

### Bağlantı Lifecycle

```
1. POST /api/reports → report_id alınır
2. WebSocket bağlantısı: ws://localhost:8000/ws/{report_id}
3. Event'ler dinlenir
4. job_completed geldiğinde bağlantı kapatılır
```

### Event Tipleri

#### Job Events
| Event | Açıklama |
|-------|----------|
| `job_started` | İş başladı |
| `job_completed` | İş tamamlandı |
| `job_failed` | İş hata aldı |

#### Agent Events
| Event | Açıklama |
|-------|----------|
| `agent_started` | Agent çalışmaya başladı |
| `agent_progress` | Agent ilerlemesi (%) |
| `agent_completed` | Agent tamamlandı |
| `agent_failed` | Agent hata aldı |

#### Council Events
| Event | Açıklama |
|-------|----------|
| `council_started` | Komite toplantısı başladı |
| `council_phase_changed` | Toplantı aşaması değişti |
| `council_speaker_changed` | Konuşmacı değişti |
| `council_speech` | Konuşma chunk'ı (streaming) |
| `council_score_revision` | Skor revize edildi |
| `council_decision` | Final karar açıklandı |

### Speech Chunk Birleştirme

```typescript
// council_speech event'leri chunk olarak gelir
// is_complete: true olana kadar birleştir

if (payload.is_complete) {
  // Tüm chunk'ları birleştir
  const fullText = chunks.join(' ');
  // risk_score bu event'te gelir
}
```

---

## 💻 Komutlar

### Development

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Dev server başlat
npm run dev
# veya
npx vite

# Port 3000'de açılır: http://localhost:3000
```

### Build

```bash
# Production build
npm run build

# Preview
npm run preview
```

### Diğer

```bash
# Type check
npm run typecheck

# Lint
npm run lint
```

---

## 👥 Komite Üyeleri

| ID | İsim | Rol | Emoji |
|----|------|-----|-------|
| `risk_analyst` | Mehmet Bey | Baş Risk Analisti | 🔴 |
| `business_analyst` | Ayşe Hanım | İş Geliştirme Müdürü | 🟢 |
| `legal_expert` | Av. Zeynep Hanım | Hukuk Müşaviri | ⚖️ |
| `media_analyst` | Deniz Bey | İtibar Analisti | 📰 |
| `sector_expert` | Prof. Dr. Ali Bey | Sektör Uzmanı | 📊 |
| `moderator` | Genel Müdür Yardımcısı | Komite Başkanı | 👨‍⚖️ |

---

## 🌐 Türkçe Çeviriler

### Risk Seviyeleri

```typescript
const RISK_LEVEL_LABELS = {
  dusuk: 'Düşük Risk',
  orta_dusuk: 'Orta-Düşük Risk',
  orta: 'Orta Risk',
  orta_yuksek: 'Orta-Yüksek Risk',
  yuksek: 'Yüksek Risk',
};
```

### Kararlar

```typescript
const DECISION_LABELS = {
  onay: 'Onay',
  sartli_onay: 'Şartlı Onay',
  red: 'Red',
  inceleme_gerek: 'İnceleme Gerekli',
};
```

### Durumlar

```typescript
const STATUS_LABELS = {
  pending: 'Bekliyor',
  processing: 'İşleniyor',
  completed: 'Tamamlandı',
  failed: 'Hata',
};
```

---

## 🎬 Animasyonlar (Framer Motion)

### Kullanılacak Animasyonlar

| Animasyon | Kullanım Yeri |
|-----------|---------------|
| `fadeInUp` | Sayfa geçişleri, kart girişleri |
| `scaleBump` | Skor değişimi, badge'ler |
| `staggerChildren` | Liste elemanları |
| `speechDrop` | Konuşma balonları |
| `scoreRevision` | Skor revizyonu (flash + scale) |
| `progressFill` | Progress bar dolumu |
| `cursorBlink` | Streaming text cursor |

---

## 📞 İletişim

| Kişi | Rol | Alan |
|------|-----|------|
| **Bekir** | Frontend Dev | React, UI |
| **Bartın** | Backend Dev | FastAPI, DB |
| **Yamaç** | AI/ML | Agents, Council |

**Değişiklik gerekirse:** Önce API.md'yi güncelle, takıma haber ver.

---

<div align="center">

**GoldenHead Team** 🏆

KKB Agentic AI Hackathon 2024

</div>
