# 🗺️ Frontend Geliştirme Roadmap

> **Takım:** GoldenHead  
> **Geliştirici:** Bekir  
> **Son Güncelleme:** 4 Aralık 2024

---

## 📊 Genel İlerleme

| Faz | Açıklama | Durum | İlerleme |
|-----|----------|-------|----------|
| 🔧 **Faz 1** | Proje Kurulumu | 🟡 Devam Ediyor | ████░░░░░░ 40% |
| 📝 **Faz 2** | Types & Mock System | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 🔌 **Faz 3** | Infrastructure | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 🏠 **Faz 4** | Landing Page | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 📋 **Faz 5** | Reports Page | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 📊 **Faz 6** | Report Detail | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 🔴 **Faz 7** | Live Page | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 🏛️ **Faz 8** | Council UI | ⚪ Başlamadı | ░░░░░░░░░░ 0% |
| 🎨 **Faz 9** | Polish & Test | ⚪ Başlamadı | ░░░░░░░░░░ 0% |

---

## 🔧 FAZ 1: Proje Kurulumu

**Tahmini Süre:** 1-2 saat  
**Durum:** 🟡 Devam Ediyor

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 1.1 | Vite + React + TypeScript projesi | ✅ Tamamlandı | `npm create vite` |
| 1.2 | Tailwind CSS kurulumu | ✅ Tamamlandı | PostCSS config dahil |
| 1.3 | React Router kurulumu | ✅ Tamamlandı | v6, 4 route tanımlı |
| 1.4 | Zustand kurulumu | ✅ Tamamlandı | State management |
| 1.5 | React Query kurulumu | ✅ Tamamlandı | @tanstack/react-query |
| 1.6 | Framer Motion kurulumu | ✅ Tamamlandı | Animasyonlar için |
| 1.7 | Lucide React kurulumu | ✅ Tamamlandı | İkonlar |
| 1.8 | KKB renk paleti (tailwind.config.js) | ✅ Tamamlandı | kkb-*, accent-*, risk-* |
| 1.9 | .env dosyaları | ✅ Tamamlandı | VITE_USE_MOCK=true |
| 1.10 | Klasör yapısı oluştur | ⬜ Bekliyor | components, pages, hooks... |
| 1.11 | shadcn/ui kurulumu | ⬜ Bekliyor | UI component library |
| 1.12 | ESLint + Prettier config | ⬜ Bekliyor | Code quality |
| 1.13 | İlk commit | ⬜ Bekliyor | "feat: project setup" |

**Test:** `npm run dev` → localhost:3000'de sayfa açılıyor ✅

---

## 📝 FAZ 2: Types & Mock System

**Tahmini Süre:** 2-3 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 2.1 | `types/api.ts` - Base types | ⬜ | ApiResponse, ApiError, Pagination |
| 2.2 | `types/report.ts` - Report types | ⬜ | ReportStatus, RiskLevel, Decision |
| 2.3 | `types/agent.ts` - Agent types | ⬜ | TsgData, IhaleData, NewsData |
| 2.4 | `types/council.ts` - Council types | ⬜ | CouncilDecision, TranscriptEntry |
| 2.5 | `types/websocket.ts` - WS events | ⬜ | Tüm event tipleri |
| 2.6 | `utils/constants.ts` - Sabitler | ⬜ | Labels, colors, members |
| 2.7 | `mocks/mockData.ts` - Örnek veriler | ⬜ | 2-3 örnek rapor |
| 2.8 | `mocks/mockApi.ts` - Mock REST | ⬜ | Fake API responses |
| 2.9 | `mocks/mockWebSocket.ts` - Mock WS | ⬜ | Event simulation |
| 2.10 | `mocks/mockScenarios.ts` - Senaryolar | ⬜ | HAPPY_PATH, AGENT_FAIL... |
| 2.11 | Type test | ⬜ | TypeScript hata kontrolü |

**Çıktı:** Tüm tipler tanımlı, mock sistem hazır

---

## 🔌 FAZ 3: Infrastructure (Hooks & Services)

**Tahmini Süre:** 3-4 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 3.1 | `services/api.ts` - API client | ⬜ | fetch wrapper, mock switch |
| 3.2 | `services/websocket.ts` - WS client | ⬜ | Bağlantı yönetimi |
| 3.3 | `hooks/useWebSocket.ts` | ⬜ | Event handling hook |
| 3.4 | `stores/reportStore.ts` | ⬜ | Zustand report state |
| 3.5 | `stores/agentStore.ts` | ⬜ | Agent progress state |
| 3.6 | `stores/councilStore.ts` | ⬜ | Council state, chunks |
| 3.7 | `stores/uiStore.ts` | ⬜ | UI state (modals...) |
| 3.8 | `hooks/useReport.ts` | ⬜ | React Query hook |
| 3.9 | `hooks/useReports.ts` | ⬜ | List + pagination |
| 3.10 | `utils/formatters.ts` | ⬜ | Date, money, duration |
| 3.11 | `utils/animations.ts` | ⬜ | Framer Motion presets |
| 3.12 | `utils/cn.ts` | ⬜ | className utility |
| 3.13 | Infrastructure test | ⬜ | Mock WS bağlantı testi |

**Çıktı:** Tüm servisler ve hook'lar çalışıyor

---

## 🏠 FAZ 4: Landing Page

**Tahmini Süre:** 3-4 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 4.1 | `components/layout/Header.tsx` | ⬜ | Logo, nav links |
| 4.2 | `components/layout/Footer.tsx` | ⬜ | GoldenHead, KKB copyright |
| 4.3 | `components/layout/PageContainer.tsx` | ⬜ | Sayfa wrapper |
| 4.4 | `components/landing/Hero.tsx` | ⬜ | Gradient bg, başlık |
| 4.5 | `components/landing/SearchForm.tsx` | ⬜ | Firma adı input |
| 4.6 | `components/landing/AgentCards.tsx` | ⬜ | 3 agent tanıtımı |
| 4.7 | `components/landing/CouncilIntro.tsx` | ⬜ | 6 üye tanıtımı |
| 4.8 | `pages/Landing.tsx` | ⬜ | Tüm bileşenler birleşik |
| 4.9 | Form submit → POST /api/reports | ⬜ | API call + redirect |
| 4.10 | Responsive test | ⬜ | Mobile, tablet, desktop |
| 4.11 | Animasyonlar | ⬜ | fadeInUp, stagger |
| 4.12 | Landing commit | ⬜ | "feat: landing page" |

**Çıktı:** Profesyonel vitrin sayfası

---

## 📋 FAZ 5: Reports Page

**Tahmini Süre:** 3-4 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 5.1 | `components/reports/StatusBadge.tsx` | ⬜ | pending/processing/completed/failed |
| 5.2 | `components/reports/RiskBadge.tsx` | ⬜ | Risk level + renk |
| 5.3 | `components/reports/ReportCard.tsx` | ⬜ | Tek rapor kartı |
| 5.4 | `components/reports/ReportList.tsx` | ⬜ | Kart listesi |
| 5.5 | `components/reports/ReportFilters.tsx` | ⬜ | Status, date filter |
| 5.6 | `components/reports/Pagination.tsx` | ⬜ | Sayfa navigasyonu |
| 5.7 | `pages/Reports.tsx` | ⬜ | Liste sayfası |
| 5.8 | Empty state | ⬜ | Rapor yoksa |
| 5.9 | Loading state | ⬜ | Yüklenirken |
| 5.10 | Kart tıklama → /reports/:id | ⬜ | Navigation |
| 5.11 | Responsive test | ⬜ | Grid düzeni |
| 5.12 | Reports commit | ⬜ | "feat: reports page" |

**Çıktı:** Çalışan rapor listesi sayfası

---

## 📊 FAZ 6: Report Detail Page

**Tahmini Süre:** 4-5 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 6.1 | `components/report-detail/RiskGauge.tsx` | ⬜ | Circular gauge |
| 6.2 | `components/report-detail/ConsensusBar.tsx` | ⬜ | Konsensüs % bar |
| 6.3 | `components/report-detail/ConditionsList.tsx` | ⬜ | Şartlar listesi |
| 6.4 | `components/report-detail/FinalDecision.tsx` | ⬜ | Ana karar kartı |
| 6.5 | `components/report-detail/TsgResults.tsx` | ⬜ | TSG agent sonuçları |
| 6.6 | `components/report-detail/IhaleResults.tsx` | ⬜ | İhale agent sonuçları |
| 6.7 | `components/report-detail/NewsResults.tsx` | ⬜ | Haber agent sonuçları |
| 6.8 | `components/report-detail/AgentResults.tsx` | ⬜ | 3 agent container |
| 6.9 | `components/report-detail/TranscriptAccordion.tsx` | ⬜ | Komite transcript |
| 6.10 | `pages/ReportDetail.tsx` | ⬜ | Detay sayfası |
| 6.11 | PDF indirme butonu | ⬜ | GET /reports/:id/pdf |
| 6.12 | Silme butonu + modal | ⬜ | DELETE confirm |
| 6.13 | Processing → Live redirect | ⬜ | Auto redirect |
| 6.14 | Report detail commit | ⬜ | "feat: report detail" |

**Çıktı:** Tam çalışan rapor detay sayfası

---

## 🔴 FAZ 7: Live Page (Agent Progress)

**Tahmini Süre:** 4-5 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 7.1 | `components/live/LiveIndicator.tsx` | ⬜ | 🔴 CANLI badge |
| 7.2 | `components/live/Timer.tsx` | ⬜ | Geçen süre sayacı |
| 7.3 | `components/live/PhaseStepper.tsx` | ⬜ | Aşama göstergesi |
| 7.4 | `components/live/AgentStatusCard.tsx` | ⬜ | Tek agent durumu |
| 7.5 | `components/live/AgentProgressBar.tsx` | ⬜ | Animated progress |
| 7.6 | `components/live/AgentProgress.tsx` | ⬜ | 3 agent container |
| 7.7 | `pages/LiveSession.tsx` | ⬜ | Canlı sayfa |
| 7.8 | WebSocket bağlantısı | ⬜ | useWebSocket hook |
| 7.9 | Agent event handling | ⬜ | started, progress, completed |
| 7.10 | Council başlangıç geçişi | ⬜ | Agent → Council UI |
| 7.11 | job_completed → redirect | ⬜ | /reports/:id'ye yönlendir |
| 7.12 | Error handling | ⬜ | job_failed, agent_failed |
| 7.13 | Live page commit | ⬜ | "feat: live page" |

**Çıktı:** Çalışan canlı akış sayfası

---

## 🏛️ FAZ 8: Council UI

**Tahmini Süre:** 5-6 saat (En karmaşık kısım)  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 8.1 | `components/council/SpeakerAvatar.tsx` | ⬜ | Emoji + name + role |
| 8.2 | `components/council/StreamingText.tsx` | ⬜ | Typing efekti + cursor |
| 8.3 | `components/council/SpeechBubble.tsx` | ⬜ | Konuşma balonu |
| 8.4 | `components/council/ScoreBoard.tsx` | ⬜ | 5 üye skorları |
| 8.5 | `components/council/ScoreRevision.tsx` | ⬜ | Skor değişim animasyonu |
| 8.6 | `components/council/PhaseIndicator.tsx` | ⬜ | Mevcut aşama |
| 8.7 | `components/council/CouncilContainer.tsx` | ⬜ | Ana container |
| 8.8 | `components/council/FinalDecisionCard.tsx` | ⬜ | Final karar reveal |
| 8.9 | Speech chunk birleştirme | ⬜ | councilStore logic |
| 8.10 | Konuşmacı değişim animasyonu | ⬜ | Framer Motion |
| 8.11 | Skor güncelleme animasyonu | ⬜ | Scale bump |
| 8.12 | Skor revizyonu animasyonu | ⬜ | Flash + scale |
| 8.13 | Final karar reveal | ⬜ | Dramatic entrance |
| 8.14 | LiveSession'a entegre | ⬜ | council_started sonrası |
| 8.15 | Tam akış testi (mock) | ⬜ | Start to finish |
| 8.16 | Council UI commit | ⬜ | "feat: council ui" |

**Çıktı:** Tam çalışan, animasyonlu Council UI

---

## 🎨 FAZ 9: Polish & Final Test

**Tahmini Süre:** 2-3 saat  
**Durum:** ⚪ Başlamadı

| # | Görev | Durum | Notlar |
|---|-------|-------|--------|
| 9.1 | Responsive kontrol | ⬜ | Tüm sayfalar, tüm boyutlar |
| 9.2 | Dark mode (opsiyonel) | ⬜ | Tailwind dark: prefix |
| 9.3 | Loading states | ⬜ | Tüm async işlemler |
| 9.4 | Error states | ⬜ | Hata mesajları, retry |
| 9.5 | Empty states | ⬜ | Boş durumlar |
| 9.6 | Accessibility | ⬜ | Keyboard nav, ARIA |
| 9.7 | Performance | ⬜ | Lighthouse audit |
| 9.8 | Console temizliği | ⬜ | No errors, no warnings |
| 9.9 | Production build | ⬜ | `npm run build` test |
| 9.10 | Demo senaryo | ⬜ | Jüri sunumu için |
| 9.11 | README güncelle | ⬜ | Son hali |
| 9.12 | Final commit | ⬜ | "feat: ready for demo" |

**Çıktı:** Production-ready, demo-ready frontend

---

## 🎯 Milestone Özeti

| # | Milestone | Hedef Tarih | Durum |
|---|-----------|-------------|-------|
| M1 | Proje kurulumu tamamlandı | - | 🟡 Devam |
| M2 | Types & Mock hazır | - | ⬜ |
| M3 | Infrastructure hazır | - | ⬜ |
| M4 | Landing sayfası canlı | - | ⬜ |
| M5 | Reports listesi çalışıyor | - | ⬜ |
| M6 | Report detail çalışıyor | - | ⬜ |
| M7 | Live page çalışıyor | - | ⬜ |
| M8 | Council animasyonları tamam | - | ⬜ |
| M9 | **FRONTEND HAZIR** | - | ⬜ |

---

## 📋 Günlük Log

### 4 Aralık 2024

| Saat | Yapılan İş | Notlar |
|------|------------|--------|
| - | Proje analizi yapıldı | API.md incelendi |
| - | Teknoloji stack belirlendi | Vite, React, Tailwind... |
| - | README-BEKIR.md oluşturuldu | Detaylı dokümantasyon |
| - | ROADMAP-BEKIR.md oluşturuldu | Bu dosya |
| - | Vite projesi kuruldu | npm install tamamlandı |
| - | Tailwind config yapıldı | KKB renkleri eklendi |
| - | Test sayfası çalıştı | localhost:3000 ✅ |

---

## 🚧 Bilinen Sorunlar

| # | Sorun | Durum | Çözüm |
|---|-------|-------|-------|
| - | Henüz yok | - | - |

---

## 💡 Notlar & Fikirler

| # | Not | Öncelik |
|---|-----|---------|
| 1 | Dark mode hackathon sonrasına bırakılabilir | Düşük |
| 2 | PWA support sonraya | Düşük |
| 3 | Unit testler vakit kalırsa | Orta |

---

## ⚠️ Önemli Kurallar

1. **Her adımda test et** - İlerlemeden önce çalıştığını doğrula
2. **Onay al** - Bekir'den onay almadan sonraki faza geçme
3. **API.md'ye sadık kal** - Ekstra özellik ekleme
4. **Mock mode kullan** - Backend hazır olana kadar
5. **Commit at** - Her faz sonunda commit

---

<div align="center">

**🚀 Bir faz, bir test, bir commit!**

**GoldenHead Team** | KKB Hackathon 2024

</div>
