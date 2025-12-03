# 📡 API Dökümanı

> Frontend-Backend Sözleşmesi
>
> ⚠️ **Bu döküman bir kontrat niteliğindedir.** Bekir bu sözleşmeye göre frontend yazacak, Bartın bu sözleşmeye göre backend implement edecek. Değişiklik yapılacaksa **önce bu döküman güncellenip herkese haber verilmeli**.

---

## 📋 İçindekiler

- [Genel Kurallar](#-genel-kurallar)
- [REST Endpoints](#-rest-endpoints)
- [WebSocket Protokolü](#-websocket-protokolü)
- [Veri Modelleri](#-veri-modelleri)
- [Hata Kodları](#-hata-kodları)

---

## 📐 Genel Kurallar

### Base URL

```
Development: http://localhost:8000/api
Production:  http://{VPS_IP}/api
```

### Standartlar

| Konu | Standart |
|------|----------|
| Format | JSON |
| Encoding | UTF-8 |
| Naming | snake_case |
| Tarih | ISO8601 (`2024-12-03T14:30:00Z`) |
| ID | UUID v4 |
| Auth | Yok |

### Response Envelope

**Tüm response'lar bu formatta:**

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

**Hata durumunda:**

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "REPORT_NOT_FOUND",
    "message": "Rapor bulunamadı"
  }
}
```

### HTTP Status Codes

| Code | Anlam | Kullanım |
|------|-------|----------|
| 200 | OK | Başarılı GET, PUT, DELETE |
| 201 | Created | Başarılı POST |
| 400 | Bad Request | Validation hatası |
| 404 | Not Found | Kaynak bulunamadı |
| 500 | Server Error | Sunucu hatası |

### Pagination

Liste dönen endpoint'lerde:

**Request:**
```
GET /api/reports?page=1&limit=10
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total_items": 45,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  },
  "error": null
}
```

---

## 🛣️ REST Endpoints

### Özet Tablo

| Method | Endpoint | Açıklama | Owner |
|--------|----------|----------|-------|
| POST | `/api/reports` | Yeni rapor başlat | Bartın |
| GET | `/api/reports` | Rapor listesi | Bartın |
| GET | `/api/reports/{id}` | Rapor detayı | Bartın |
| DELETE | `/api/reports/{id}` | Rapor sil | Bartın |
| GET | `/api/reports/{id}/pdf` | PDF export | Bartın |
| GET | `/api/health` | Health check | Bartın |

---

### POST `/api/reports`

Yeni rapor oluşturma işlemi başlatır. İşlem arka planda çalışır, WebSocket üzerinden takip edilir.

**Request:**

```json
{
  "company_name": "ABC Teknoloji A.Ş.",
  "company_tax_no": "1234567890"        // opsiyonel
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "websocket_url": "/ws/550e8400-e29b-41d4-a716-446655440000"
  },
  "error": null
}
```

**Errors:**

| Code | Message | Durum |
|------|---------|-------|
| VALIDATION_ERROR | "company_name zorunlu" | 400 |
| COMPANY_NAME_TOO_SHORT | "Firma adı en az 2 karakter olmalı" | 400 |

**Bekir Notu:** Response aldıktan sonra hemen `websocket_url`'e bağlan ve event'leri dinlemeye başla.

---

### GET `/api/reports`

Tüm raporları listeler.

**Query Parameters:**

| Param | Type | Default | Açıklama |
|-------|------|---------|----------|
| page | int | 1 | Sayfa numarası |
| limit | int | 10 | Sayfa başı kayıt (max 50) |
| status | string | - | Filtre: pending, processing, completed, failed |
| sort | string | -created_at | Sıralama: created_at, -created_at, company_name |

**Request:**
```
GET /api/reports?page=1&limit=10&status=completed&sort=-created_at
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "company_name": "ABC Teknoloji A.Ş.",
        "company_tax_no": "1234567890",
        "status": "completed",
        "final_score": 33,
        "risk_level": "orta_dusuk",
        "decision": "sartli_onay",
        "created_at": "2024-12-03T14:30:00Z",
        "completed_at": "2024-12-03T15:08:00Z",
        "duration_seconds": 2280
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "company_name": "XYZ Holding A.Ş.",
        "company_tax_no": null,
        "status": "processing",
        "final_score": null,
        "risk_level": null,
        "decision": null,
        "created_at": "2024-12-03T15:00:00Z",
        "completed_at": null,
        "duration_seconds": null
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total_items": 45,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  },
  "error": null
}
```

---

### GET `/api/reports/{id}`

Tek bir raporun tam detayını döner.

**Request:**
```
GET /api/reports/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "company_name": "ABC Teknoloji A.Ş.",
    "company_tax_no": "1234567890",
    "status": "completed",
    "created_at": "2024-12-03T14:30:00Z",
    "completed_at": "2024-12-03T15:08:00Z",
    "duration_seconds": 2280,
    
    "agent_results": {
      "tsg": {
        "status": "completed",
        "duration_seconds": 180,
        "data": {
          "kurulus_tarihi": "2018-03-15",
          "sermaye": 5000000,
          "sermaye_para_birimi": "TRY",
          "adres": "Maslak, İstanbul",
          "faaliyet_konusu": "Yazılım geliştirme, yapay zeka",
          "ortaklar": [
            {"ad": "Ahmet Yılmaz", "pay_orani": 40},
            {"ad": "XYZ Yatırım A.Ş.", "pay_orani": 20},
            {"ad": "Mehmet Demir", "pay_orani": 40}
          ],
          "yonetim_kurulu": [
            {"ad": "Ahmet Yılmaz", "gorev": "Başkan"},
            {"ad": "Ayşe Kaya", "gorev": "Üye"}
          ],
          "sermaye_degisiklikleri": [
            {"tarih": "2024-03-01", "eski": 3000000, "yeni": 5000000}
          ],
          "yonetici_degisiklikleri": [
            {"tarih": "2024-01-15", "eski": "Ali Veli", "yeni": "Ayşe Kaya", "gorev": "Genel Müdür"}
          ]
        }
      },
      "ihale": {
        "status": "completed",
        "duration_seconds": 45,
        "data": {
          "yasak_durumu": false,
          "aktif_yasak": null,
          "gecmis_yasaklar": []
        }
      },
      "news": {
        "status": "completed",
        "duration_seconds": 120,
        "data": {
          "toplam_haber": 24,
          "pozitif": 15,
          "negatif": 4,
          "notr": 5,
          "sentiment_score": 0.62,
          "trend": "yukari",
          "onemli_haberler": [
            {
              "baslik": "ABC Teknoloji 50 kişilik istihdam sağlayacak",
              "kaynak": "ekonomi.com",
              "tarih": "2024-10-15",
              "sentiment": "pozitif",
              "url": "https://..."
            },
            {
              "baslik": "ABC Teknoloji vergi yapılandırması yaptı",
              "kaynak": "finans.com",
              "tarih": "2023-09-20",
              "sentiment": "negatif",
              "url": "https://..."
            }
          ]
        }
      }
    },
    
    "council_decision": {
      "final_score": 33,
      "risk_level": "orta_dusuk",
      "decision": "sartli_onay",
      "consensus": 0.85,
      "conditions": [
        "6 aylık izleme periyodu",
        "Yönetim değişikliği bildirim yükümlülüğü",
        "Çeyreklik finansal rapor talebi"
      ],
      "dissent_note": "Risk analisti başlangıçta yüksek risk görmüş (65), tartışma sonunda revize etmiştir (45). İzleme şartlarının kritik olduğunu vurgulamıştır.",
      "scores": {
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
        }
      },
      "duration_seconds": 2100,
      "transcript": [
        {
          "timestamp": "2024-12-03T14:32:00Z",
          "phase": "opening",
          "speaker_id": "moderator",
          "speaker_name": "Genel Müdür Yardımcısı",
          "speaker_emoji": "👨‍⚖️",
          "content": "Değerli komite üyeleri, bugün ABC Teknoloji A.Ş. hakkında değerlendirme yapacağız...",
          "risk_score": null
        },
        {
          "timestamp": "2024-12-03T14:35:00Z",
          "phase": "presentation",
          "speaker_id": "risk_analyst",
          "speaker_name": "Mehmet Bey",
          "speaker_emoji": "🔴",
          "content": "Teşekkürler Başkanım. TSG kayıtlarını inceledim. Ciddi kırmızı bayraklar görüyorum...",
          "risk_score": 65
        }
      ]
    }
  },
  "error": null
}
```

**Errors:**

| Code | Message | Durum |
|------|---------|-------|
| REPORT_NOT_FOUND | "Rapor bulunamadı" | 404 |

---

### DELETE `/api/reports/{id}`

Raporu siler.

**Request:**
```
DELETE /api/reports/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "deleted": true,
    "id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "error": null
}
```

**Errors:**

| Code | Message | Durum |
|------|---------|-------|
| REPORT_NOT_FOUND | "Rapor bulunamadı" | 404 |
| REPORT_IN_PROGRESS | "İşlemi devam eden rapor silinemez" | 400 |

---

### GET `/api/reports/{id}/pdf`

Raporun PDF versiyonunu indirir.

**Request:**
```
GET /api/reports/550e8400-e29b-41d4-a716-446655440000/pdf
```

**Response (200 OK):**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="ABC_Teknoloji_AS_Rapor_2024-12-03.pdf"

[binary PDF data]
```

**Errors:**

| Code | Message | Durum |
|------|---------|-------|
| REPORT_NOT_FOUND | "Rapor bulunamadı" | 404 |
| REPORT_NOT_COMPLETED | "Tamamlanmamış raporun PDF'i oluşturulamaz" | 400 |

---

### GET `/api/health`

Sistem sağlık kontrolü.

**Request:**
```
GET /api/health
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-12-03T14:30:00Z",
    "services": {
      "database": "up",
      "redis": "up",
      "celery": "up"
    }
  },
  "error": null
}
```

---

## 🔌 WebSocket Protokolü

### Bağlantı

```
URL: ws://localhost:8000/ws/{report_id}
```

**Bekir Notu:** `POST /api/reports` response'undaki `websocket_url`'i kullan.

### Bağlantı Lifecycle

```
1. Bekir: POST /api/reports → report_id alır
2. Bekir: WebSocket bağlantısı açar → ws://localhost:8000/ws/{report_id}
3. Backend: Event'leri gönderir
4. İş bitince: job_completed event'i gelir
5. Bekir: Bağlantıyı kapatır (veya açık tutar, yeni sorgular için)
```

### Event Format

```json
{
  "type": "event_type",
  "timestamp": "2024-12-03T14:30:00Z",
  "payload": { ... }
}
```

---

### Event Tipleri

#### 🚀 Job Events

**job_started**

İş başladığında gönderilir.

```json
{
  "type": "job_started",
  "timestamp": "2024-12-03T14:30:00Z",
  "payload": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "company_name": "ABC Teknoloji A.Ş.",
    "estimated_duration_seconds": 2400
  }
}
```

**job_completed**

İş başarıyla tamamlandığında gönderilir.

```json
{
  "type": "job_completed",
  "timestamp": "2024-12-03T15:08:00Z",
  "payload": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "duration_seconds": 2280,
    "final_score": 33,
    "risk_level": "orta_dusuk",
    "decision": "sartli_onay"
  }
}
```

**job_failed**

İş hata ile sonlandığında gönderilir.

```json
{
  "type": "job_failed",
  "timestamp": "2024-12-03T14:45:00Z",
  "payload": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "error_code": "TSG_CONNECTION_FAILED",
    "error_message": "Ticaret Sicili Gazetesi'ne bağlanılamadı"
  }
}
```

---

#### 🤖 Agent Events

**agent_started**

Bir agent çalışmaya başladığında.

```json
{
  "type": "agent_started",
  "timestamp": "2024-12-03T14:30:05Z",
  "payload": {
    "agent_id": "tsg_agent",
    "agent_name": "TSG Agent",
    "agent_description": "Ticaret Sicili Gazetesi taranıyor"
  }
}
```

**agent_progress**

Agent ilerlemesi (birden fazla kez gelebilir).

```json
{
  "type": "agent_progress",
  "timestamp": "2024-12-03T14:31:00Z",
  "payload": {
    "agent_id": "tsg_agent",
    "progress": 50,
    "message": "4/8 PDF analiz edildi"
  }
}
```

**agent_completed**

Agent işini tamamladığında.

```json
{
  "type": "agent_completed",
  "timestamp": "2024-12-03T14:33:00Z",
  "payload": {
    "agent_id": "tsg_agent",
    "duration_seconds": 180,
    "summary": {
      "records_found": 8,
      "key_findings": [
        "Sermaye artışı tespit edildi",
        "3 yönetici değişikliği bulundu"
      ]
    }
  }
}
```

**agent_failed**

Agent hata aldığında (diğer agent'lar devam edebilir).

```json
{
  "type": "agent_failed",
  "timestamp": "2024-12-03T14:35:00Z",
  "payload": {
    "agent_id": "news_agent",
    "error_code": "SCRAPING_BLOCKED",
    "error_message": "Haber sitesine erişim engellendi",
    "will_retry": true
  }
}
```

---

#### 🏛️ Council Events

**council_started**

Komite toplantısı başladığında.

```json
{
  "type": "council_started",
  "timestamp": "2024-12-03T14:35:00Z",
  "payload": {
    "estimated_duration_seconds": 2100,
    "members": [
      {"id": "risk_analyst", "name": "Mehmet Bey", "role": "Baş Risk Analisti", "emoji": "🔴"},
      {"id": "business_analyst", "name": "Ayşe Hanım", "role": "İş Geliştirme Müdürü", "emoji": "🟢"},
      {"id": "legal_expert", "name": "Av. Zeynep Hanım", "role": "Hukuk Müşaviri", "emoji": "⚖️"},
      {"id": "media_analyst", "name": "Deniz Bey", "role": "İtibar Analisti", "emoji": "📰"},
      {"id": "sector_expert", "name": "Prof. Dr. Ali Bey", "role": "Sektör Uzmanı", "emoji": "📊"},
      {"id": "moderator", "name": "Genel Müdür Yardımcısı", "role": "Komite Başkanı", "emoji": "👨‍⚖️"}
    ]
  }
}
```

**council_phase_changed**

Toplantı aşaması değiştiğinde.

```json
{
  "type": "council_phase_changed",
  "timestamp": "2024-12-03T14:37:00Z",
  "payload": {
    "phase": "presentation",
    "phase_number": 2,
    "total_phases": 8,
    "phase_title": "Risk Analisti Sunumu"
  }
}
```

**Aşamalar:**
1. `opening` - Açılış
2. `presentation` - Risk Analisti Sunumu
3. `presentation` - İş Analisti Sunumu
4. `presentation` - Hukuk Uzmanı Sunumu
5. `presentation` - İtibar Analisti Sunumu
6. `presentation` - Sektör Uzmanı Sunumu
7. `discussion` - Tartışma
8. `decision` - Final Karar

**council_speaker_changed**

Konuşmacı değiştiğinde.

```json
{
  "type": "council_speaker_changed",
  "timestamp": "2024-12-03T14:37:05Z",
  "payload": {
    "speaker_id": "risk_analyst",
    "speaker_name": "Mehmet Bey",
    "speaker_role": "Baş Risk Analisti",
    "speaker_emoji": "🔴"
  }
}
```

**council_speech**

Konuşma içeriği (cümle cümle gelir, streaming).

```json
{
  "type": "council_speech",
  "timestamp": "2024-12-03T14:37:10Z",
  "payload": {
    "speaker_id": "risk_analyst",
    "chunk": "Teşekkürler Başkanım. TSG kayıtlarını inceledim.",
    "is_complete": false
  }
}
```

```json
{
  "type": "council_speech",
  "timestamp": "2024-12-03T14:37:15Z",
  "payload": {
    "speaker_id": "risk_analyst",
    "chunk": "Ciddi kırmızı bayraklar görüyorum.",
    "is_complete": false
  }
}
```

```json
{
  "type": "council_speech",
  "timestamp": "2024-12-03T14:38:00Z",
  "payload": {
    "speaker_id": "risk_analyst",
    "chunk": "Risk değerlendirmem: 65/100.",
    "is_complete": true,
    "risk_score": 65
  }
}
```

**Bekir Notu:** `is_complete: true` gelene kadar chunk'ları birleştir. `is_complete: true` geldiğinde `risk_score` da gelir (sunum fazında).

**council_score_revision**

Bir üye skorunu revize ettiğinde.

```json
{
  "type": "council_score_revision",
  "timestamp": "2024-12-03T15:00:00Z",
  "payload": {
    "speaker_id": "risk_analyst",
    "speaker_name": "Mehmet Bey",
    "old_score": 65,
    "new_score": 45,
    "reason": "Tartışmada ortaya çıkan yeni bilgiler ışığında revize ediyorum"
  }
}
```

**council_decision**

Final karar açıklandığında.

```json
{
  "type": "council_decision",
  "timestamp": "2024-12-03T15:05:00Z",
  "payload": {
    "final_score": 33,
    "risk_level": "orta_dusuk",
    "decision": "sartli_onay",
    "consensus": 0.85,
    "conditions": [
      "6 aylık izleme periyodu",
      "Yönetim değişikliği bildirim yükümlülüğü",
      "Çeyreklik finansal rapor talebi"
    ],
    "dissent_note": "Risk analisti başlangıçta yüksek risk görmüş (65), tartışma sonunda revize etmiştir (45).",
    "final_scores": {
      "risk_analyst": 45,
      "business_analyst": 25,
      "legal_expert": 30,
      "media_analyst": 30,
      "sector_expert": 35
    }
  }
}
```

---

### WebSocket Event Akış Örneği

```
┌─────────────────────────────────────────────────────────────────┐
│ Zaman    │ Event                  │ Açıklama                   │
├──────────┼────────────────────────┼────────────────────────────┤
│ 00:00    │ job_started            │ İş başladı                 │
│ 00:01    │ agent_started          │ TSG Agent başladı          │
│ 00:01    │ agent_started          │ İhale Agent başladı        │
│ 00:01    │ agent_started          │ News Agent başladı         │
│ 00:30    │ agent_progress         │ TSG: 25% (2/8 PDF)         │
│ 00:45    │ agent_completed        │ İhale Agent tamamlandı     │
│ 01:00    │ agent_progress         │ TSG: 50% (4/8 PDF)         │
│ 01:30    │ agent_progress         │ News: 60% (14/24 haber)    │
│ 02:00    │ agent_completed        │ News Agent tamamlandı      │
│ 03:00    │ agent_completed        │ TSG Agent tamamlandı       │
│ 03:05    │ council_started        │ Komite toplantısı başladı  │
│ 03:10    │ council_phase_changed  │ Aşama 1: Açılış            │
│ 03:10    │ council_speaker_changed│ Moderatör konuşuyor        │
│ 03:10    │ council_speech         │ "Değerli komite üyeleri..."│
│ 03:15    │ council_speech         │ "...bugün ABC hakkında..." │
│ 03:20    │ council_phase_changed  │ Aşama 2: Risk Sunumu       │
│ 03:20    │ council_speaker_changed│ Mehmet Bey konuşuyor       │
│ 03:20    │ council_speech         │ "Teşekkürler Başkanım..."  │
│ ...      │ ...                    │ ...                        │
│ 35:00    │ council_score_revision │ Mehmet Bey: 65 → 45        │
│ 37:00    │ council_decision       │ Final karar açıklandı      │
│ 38:00    │ job_completed          │ İş tamamlandı              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Veri Modelleri

### Enum Değerleri

**ReportStatus**
```
pending      → Oluşturuldu, henüz başlamadı
processing   → İşleniyor
completed    → Tamamlandı
failed       → Hata ile sonlandı
```

**RiskLevel**
```
dusuk        → 0-30 puan
orta_dusuk   → 31-45 puan
orta         → 46-60 puan
orta_yuksek  → 61-75 puan
yuksek       → 76-100 puan
```

**Decision**
```
onay           → Koşulsuz onay
sartli_onay    → Şartlı onay
red            → Red
inceleme_gerek → Daha fazla inceleme gerekli
```

**AgentType**
```
tsg_agent    → Ticaret Sicili Gazetesi
ihale_agent  → İhale/EKAP
news_agent   → Haber Analizi
```

**CouncilPhase**
```
opening      → Açılış
presentation → Uzman sunumları
discussion   → Tartışma
decision     → Final karar
```

**CouncilMemberId**
```
risk_analyst     → Mehmet Bey
business_analyst → Ayşe Hanım
legal_expert     → Av. Zeynep Hanım
media_analyst    → Deniz Bey
sector_expert    → Prof. Dr. Ali Bey
moderator        → Genel Müdür Yardımcısı
```

---

### TypeScript Types (Bekir İçin)

```typescript
// types/api.ts

// Base Response
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
}

interface ApiError {
  code: string;
  message: string;
}

// Pagination
interface Pagination {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
}

// Report
type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';
type RiskLevel = 'dusuk' | 'orta_dusuk' | 'orta' | 'orta_yuksek' | 'yuksek';
type Decision = 'onay' | 'sartli_onay' | 'red' | 'inceleme_gerek';

interface ReportListItem {
  id: string;
  company_name: string;
  company_tax_no: string | null;
  status: ReportStatus;
  final_score: number | null;
  risk_level: RiskLevel | null;
  decision: Decision | null;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

interface ReportDetail extends ReportListItem {
  agent_results: {
    tsg: AgentResult<TsgData>;
    ihale: AgentResult<IhaleData>;
    news: AgentResult<NewsData>;
  };
  council_decision: CouncilDecision;
}

// Agent Results
interface AgentResult<T> {
  status: 'pending' | 'completed' | 'failed';
  duration_seconds: number | null;
  data: T | null;
}

interface TsgData {
  kurulus_tarihi: string;
  sermaye: number;
  sermaye_para_birimi: string;
  adres: string;
  faaliyet_konusu: string;
  ortaklar: Array<{ ad: string; pay_orani: number }>;
  yonetim_kurulu: Array<{ ad: string; gorev: string }>;
  sermaye_degisiklikleri: Array<{ tarih: string; eski: number; yeni: number }>;
  yonetici_degisiklikleri: Array<{ tarih: string; eski: string; yeni: string; gorev: string }>;
}

interface IhaleData {
  yasak_durumu: boolean;
  aktif_yasak: YasakBilgisi | null;
  gecmis_yasaklar: YasakBilgisi[];
}

interface YasakBilgisi {
  sebep: string;
  baslangic: string;
  bitis: string;
  kurum: string;
}

interface NewsData {
  toplam_haber: number;
  pozitif: number;
  negatif: number;
  notr: number;
  sentiment_score: number;
  trend: 'yukari' | 'asagi' | 'stabil';
  onemli_haberler: HaberItem[];
}

interface HaberItem {
  baslik: string;
  kaynak: string;
  tarih: string;
  sentiment: 'pozitif' | 'negatif' | 'notr';
  url: string;
}

// Council
interface CouncilDecision {
  final_score: number;
  risk_level: RiskLevel;
  decision: Decision;
  consensus: number;
  conditions: string[];
  dissent_note: string | null;
  scores: {
    initial: CouncilScores;
    final: CouncilScores;
  };
  duration_seconds: number;
  transcript: TranscriptEntry[];
}

interface CouncilScores {
  risk_analyst: number;
  business_analyst: number;
  legal_expert: number;
  media_analyst: number;
  sector_expert: number;
}

interface TranscriptEntry {
  timestamp: string;
  phase: CouncilPhase;
  speaker_id: CouncilMemberId;
  speaker_name: string;
  speaker_emoji: string;
  content: string;
  risk_score: number | null;
}

type CouncilPhase = 'opening' | 'presentation' | 'discussion' | 'decision';
type CouncilMemberId = 'risk_analyst' | 'business_analyst' | 'legal_expert' | 'media_analyst' | 'sector_expert' | 'moderator';

// WebSocket Events
type WebSocketEvent =
  | JobStartedEvent
  | JobCompletedEvent
  | JobFailedEvent
  | AgentStartedEvent
  | AgentProgressEvent
  | AgentCompletedEvent
  | AgentFailedEvent
  | CouncilStartedEvent
  | CouncilPhaseChangedEvent
  | CouncilSpeakerChangedEvent
  | CouncilSpeechEvent
  | CouncilScoreRevisionEvent
  | CouncilDecisionEvent;

interface BaseEvent {
  type: string;
  timestamp: string;
}

interface JobStartedEvent extends BaseEvent {
  type: 'job_started';
  payload: {
    report_id: string;
    company_name: string;
    estimated_duration_seconds: number;
  };
}

interface JobCompletedEvent extends BaseEvent {
  type: 'job_completed';
  payload: {
    report_id: string;
    duration_seconds: number;
    final_score: number;
    risk_level: RiskLevel;
    decision: Decision;
  };
}

// ... diğer event tipleri benzer şekilde
```

---

## ❌ Hata Kodları

### Genel Hatalar

| Code | Message | HTTP |
|------|---------|------|
| VALIDATION_ERROR | Doğrulama hatası | 400 |
| INTERNAL_ERROR | Sunucu hatası | 500 |
| SERVICE_UNAVAILABLE | Servis kullanılamıyor | 503 |

### Rapor Hataları

| Code | Message | HTTP |
|------|---------|------|
| REPORT_NOT_FOUND | Rapor bulunamadı | 404 |
| REPORT_IN_PROGRESS | İşlemi devam eden rapor | 400 |
| REPORT_NOT_COMPLETED | Rapor henüz tamamlanmadı | 400 |
| COMPANY_NAME_TOO_SHORT | Firma adı en az 2 karakter olmalı | 400 |

### Agent Hataları

| Code | Message |
|------|---------|
| TSG_CONNECTION_FAILED | TSG'ye bağlanılamadı |
| TSG_NO_RESULTS | TSG'de kayıt bulunamadı |
| TSG_PDF_PARSE_ERROR | PDF okunamadı |
| IHALE_CONNECTION_FAILED | EKAP'a bağlanılamadı |
| NEWS_SCRAPING_BLOCKED | Haber sitesine erişim engellendi |
| NEWS_NO_RESULTS | Haber bulunamadı |

### Council Hataları

| Code | Message |
|------|---------|
| COUNCIL_LLM_ERROR | LLM servisine bağlanılamadı |
| COUNCIL_TIMEOUT | Komite toplantısı zaman aşımına uğradı |

---

## 📝 Bekir İçin Notlar

1. **POST /api/reports** sonrası hemen WebSocket'e bağlan
2. **council_speech** event'leri chunk olarak gelir, `is_complete: true` olana kadar birleştir
3. **agent_progress** birden fazla kez gelebilir, progress bar güncelle
4. **job_completed** geldiğinde full raporu çekmek için `GET /api/reports/{id}` kullan
5. Risk level ve decision enum değerleri Türkçe UI'a çevrilmeli:
   - `dusuk` → "Düşük Risk"
   - `sartli_onay` → "Şartlı Onay"

## 📝 Bartın İçin Notlar

1. Tüm response'lar `{success, data, error}` envelope'unda olmalı
2. WebSocket event'leri her zaman `{type, timestamp, payload}` formatında
3. Council transcript'i tam kaydet, frontend istediğinde dönecek
4. PDF export için rapor `completed` olmalı, değilse 400 dön
5. Agent'lar paralel çalışabilir, hata alan agent diğerlerini durdurmasın

---

<div align="center">

**⚠️ Bu döküman bir sözleşmedir**

Değişiklik yapmadan önce Bekir ve Bartın'a haber verin.

**Son Güncelleme:** 3 Aralık 2024

**Owner:** Yamaç

</div>
