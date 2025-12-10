# KKB Hackathon - Geliştirme Durumu

> Son Güncelleme: 2025-12-11 00:10
> Yazan: Yamaç
> Branch: dev/yamac

---

## TL;DR - Hızlı Özet

| Bileşen | Durum | Not |
|---------|-------|-----|
| **Backend API** | ✅ Çalışıyor | localhost:8000 |
| **İhale K8s** | ✅ Çalışıyor | 67 saniye, 22 karar tarıyor |
| **News K8s** | ⚠️ Kısmen | 6/10 kaynak çalışıyor |
| **TSG Local** | ❌ Bozuk | ARM64 Playwright hatası |
| **Council** | ✅ Çalışıyor | 45 saniyede karar veriyor |
| **Frontend** | ✅ Çalışıyor | localhost:3000 |

---

## 1. PROJE MİMARİSİ

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                    (React + Vite)                            │
│                    localhost:3000                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND API                              │
│                  (FastAPI + Celery)                          │
│                    localhost:8000                            │
│                                                              │
│  Endpoints:                                                  │
│  - POST /api/reports          → Rapor başlat                │
│  - GET  /api/reports/{id}     → Rapor durumu                │
│  - WS   /ws/{report_id}       → WebSocket stream            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   TSG AGENT     │ │  İHALE AGENT    │ │   NEWS AGENT    │
│   (LOCAL)       │ │   (K8s)         │ │    (K8s)        │
│   ❌ BOZUK      │ │   localhost:8081│ │   localhost:8082│
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │               │
                    ┌─────────┴───────────────┴─────────┐
                    ▼                                   ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│        IHALE K8s CLUSTER        │   │         NEWS K8s CLUSTER        │
│        (minikube)               │   │         (minikube)              │
│                                 │   │                                 │
│  Namespace: ihale-agent         │   │  Namespace: news-agent          │
│                                 │   │                                 │
│  Pods:                          │   │  Pods:                          │
│  - ihale-orchestrator (2)       │   │  - news-orchestrator (1)        │
│  - ihale-scraper (1)            │   │  - llm-gateway (1)              │
│  - ihale-ocr (3)                │   │  - aa-scraper (1)               │
│                                 │   │  - trt-scraper (1)              │
│  Images:                        │   │  - hurriyet-scraper (1)         │
│  - ihale-scraper:v2 ✅          │   │  - milliyet-scraper (1)         │
│                                 │   │  - cnnturk-scraper (1)          │
│                                 │   │  - dunya-scraper (1)            │
│                                 │   │  - ekonomim-scraper (1)         │
│                                 │   │  - bigpara-scraper (1)          │
│                                 │   │  - ntv-scraper (1)              │
│                                 │   │  - sozcu-scraper (1)            │
│                                 │   │                                 │
│                                 │   │  Images:                        │
│                                 │   │  - news-universal-scraper:v8 ✅ │
│                                 │   │  - news-llm-gateway:v8 ✅       │
└─────────────────────────────────┘   └─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                       COUNCIL                                │
│                 (LLM ile 6 kişilik komite)                   │
│                      ✅ ÇALIŞIYOR                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. DOSYA DEĞİŞİKLİKLERİ

### 2.1 İHALE AGENT K8s (✅ TAMAMLANDI)

**Dosya:** `backend/scrapers/ihale-scraper/main.py`

**Problem:** Browser pool `TargetClosedError` - Browser kapanınca `self._browser` hala not None ama `is_connected()` False

**Çözüm (Satır 82-86):**
```python
async def get_context(self):
    async with self._lock:
        # ÖNCEKİ: if self._browser is None:
        # YENİ:
        if self._browser is None or not self._browser.is_connected():
            logger.info("Browser not connected, reinitializing...")
            await self._cleanup_browser()
            await self._init_browser()
```

**Eklenen Method (Satır 120-134):**
```python
async def _cleanup_browser(self):
    """Clean up browser resources before reinitialization"""
    try:
        if self._browser:
            await self._browser.close()
    except Exception as e:
        logger.warning(f"Error closing browser: {e}")
    finally:
        self._browser = None

    try:
        if self._playwright:
            await self._playwright.stop()
    except Exception as e:
        logger.warning(f"Error stopping playwright: {e}")
    finally:
        self._playwright = None
```

**Deploy:**
```bash
cd backend/scrapers/ihale-scraper
docker build -t ihale-scraper:v2 .
minikube image load ihale-scraper:v2
kubectl set image deployment/ihale-scraper scraper=ihale-scraper:v2 -n ihale-agent
kubectl delete pod -n ihale-agent -l app=ihale-scraper
```

**Test Sonucu:**
```
Süre: 67.77 saniye (önceki: 3 saniye HTTP 500!)
Taranan karar: 22
Eşleşen: 0 (Koç Holding için yasaklama yok)
```

---

### 2.2 NEWS AGENT K8s (⚠️ KISMEN ÇALIŞIYOR)

#### 2.2.1 LLM Gateway Değişiklikleri

**Dosya:** `backend/llm-gateway/main.py`

**Fix 1 - max_tokens (Satır ~438):**
```python
# ÖNCEKİ: max_tokens=1000
# YENİ:
max_tokens=2000  # Token limit'e takılıyordu, content: null dönüyordu
```

**Fix 2 - None check (Satır ~439-441):**
```python
response = await call_llm(prompt, max_tokens=2000)
# YENİ: None check eklendi
if not response:
    logger.warning("LLM returned empty response")
    return OCRExtractResponse(articles=[])
```

**Fix 3 - Safe access in call_llm (Satır ~145-149):**
```python
# ÖNCEKİ: result["choices"][0]["message"]["content"]
# YENİ:
content = result.get("choices", [{}])[0].get("message", {}).get("content")
if not content:
    logger.warning(f"LLM response has no content. finish_reason: {result.get('choices', [{}])[0].get('finish_reason')}")
    return None
```

#### 2.2.2 Universal Scraper Değişiklikleri

**Dosya:** `backend/universal-scraper/main.py`

**Düzeltilen Search URL'leri (Satır 33-84):**

| Kaynak | Eski URL | Yeni URL |
|--------|----------|----------|
| AA | `https://www.aa.com.tr/tr/search/?s=` | `https://www.aa.com.tr/tr/search?s=` |
| TRT | `https://www.trthaber.com/haber/ara/` | `https://www.trthaber.com/arama.html?q=` |
| Hürriyet | `https://www.hurriyet.com.tr/search/?query=` | `https://www.hurriyet.com.tr/arama?q=` |
| Milliyet | `https://www.milliyet.com.tr/ara?q=` | `https://www.milliyet.com.tr/arama?query=` |
| Dünya | `https://www.dunya.com/arama?q=` | `https://www.dunya.com/ara?key=` |

**Deploy:**
```bash
cd backend/universal-scraper
docker build -t news-universal-scraper:v8 .
minikube image load news-universal-scraper:v8
for src in aa trt hurriyet milliyet cnnturk dunya ekonomim bigpara ntv sozcu; do
  kubectl set image deployment/${src}-scraper scraper=news-universal-scraper:v8 -n news-agent
done

cd backend/llm-gateway
docker build -t news-llm-gateway:v8 .
minikube image load news-llm-gateway:v8
kubectl set image deployment/llm-gateway llm-gateway=news-llm-gateway:v8 -n news-agent
```

**Test Sonucu (Koç Holding):**
```
Toplam haber: 25
Başarılı kaynak: 10/10
Koç Holding ilgili: 6
Süre: 107 saniye
```

**Test Sonucu (Turkcell):**
```
Toplam haber: 0  ← SORUN!
Başarılı kaynak: 6/10
Başarısız: 4 kaynak
```

---

### 2.3 TSG AGENT (❌ BOZUK)

**Problem:** Local Playwright ARM64 Mac'te çalışmıyor

**Hata:**
```
[Errno 8] Exec format error: '/Users/.../playwright/driver/node'
```

**Neden:** Playwright'ın node binary'si x86_64, Mac ARM64

**Çözüm:** TSG Agent'ı K8s'e taşımak lazım (aşağıda TODO)

---

### 2.4 ORCHESTRATOR

**Dosya:** `backend/app/agents/orchestrator.py`

**Değişiklikler:**
- K8s agent'ları import ediyor (satır 22-25)
- `USE_K8S_IHALE_AGENT` ve `USE_K8S_NEWS_AGENT` env var'ları (satır 18-19)
- Fallback mekanizması: K8s fail olursa local agent'a düşer

**Env Vars:**
```bash
USE_K8S_IHALE_AGENT=true  # default
USE_K8S_NEWS_AGENT=true   # default
```

---

## 3. K8s KOMUTLARI

### Port Forward'lar (HER OTURUMDA ÇALIŞTIR!)
```bash
# News Agent
kubectl port-forward svc/news-orchestrator 8082:8080 -n news-agent &

# İhale Agent
kubectl port-forward svc/ihale-orchestrator 8081:8080 -n ihale-agent &
```

### Health Check'ler
```bash
# News (10/10 olmalı)
curl -s http://localhost:8082/health | python3 -m json.tool

# İhale
curl -s http://localhost:8081/health | python3 -m json.tool

# Backend
curl -s http://localhost:8000/api/health | python3 -m json.tool
```

### Pod Durumları
```bash
kubectl get pods -n news-agent
kubectl get pods -n ihale-agent
```

### Loglar
```bash
# News orchestrator
kubectl logs -n news-agent deployment/news-orchestrator --tail=100

# İhale scraper
kubectl logs -n ihale-agent deployment/ihale-scraper --tail=100

# LLM Gateway
kubectl logs -n news-agent deployment/llm-gateway --tail=100
```

### Image Güncelleme
```bash
# 1. Build
docker build -t IMAGE_NAME:VERSION .

# 2. Minikube'a yükle
minikube image load IMAGE_NAME:VERSION

# 3. Deploy et
kubectl set image deployment/DEPLOYMENT_NAME container=IMAGE_NAME:VERSION -n NAMESPACE

# 4. Restart (opsiyonel, browser reset için)
kubectl delete pod -n NAMESPACE -l app=APP_LABEL
```

---

## 4. TEST KOMUTLARI

### Rapor Başlatma
```bash
curl -s -X POST "http://localhost:8000/api/reports" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Koç Holding"}'
```

### Rapor Durumu
```bash
curl -s "http://localhost:8000/api/reports/REPORT_ID" | python3 -m json.tool
```

### Direkt İhale Test
```bash
curl -s -X POST "http://localhost:8081/api/ihale/check" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Koç Holding", "days": 7}'
```

### Direkt News Test
```bash
curl -s -X POST "http://localhost:8082/api/news/search" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Koç Holding", "request_id": "test-123"}'
```

---

## 5. SORUNLAR VE TODO'LAR

### 5.1 KRİTİK - TSG K8s'e Taşınmalı

**Mevcut Durum:**
- TSG Agent local Playwright kullanıyor
- ARM64 Mac'te `Exec format error`
- x86 makinelerde muhtemelen çalışır

**TODO:**
1. `backend/scrapers/tsg-scraper/` klasörü oluştur
2. Dockerfile yaz (playwright + tesseract)
3. K8s deployment YAML'ları yaz
4. `backend/app/agents/tsg_agent_k8s.py` oluştur
5. Orchestrator'a ekle

**Referans:** İhale scraper yapısını kopyala:
- `backend/scrapers/ihale-scraper/`
- `backend/k8s/ihale-agent/`

---

### 5.2 ORTA - News Agent 4/10 Kaynak Fail

**Başarısız Kaynaklar (Turkcell testinde):**
- CNNTürk
- Ekonomim
- Bigpara
- NTV

**Olası Sebepler:**
1. JavaScript-only arama sayfaları (Playwright render etmiyor)
2. CSS selector değişiklikleri
3. Rate limiting / IP ban

**DEBUG:**
```bash
# Tek kaynak test
kubectl port-forward svc/cnnturk-scraper 8090:8080 -n news-agent &
curl -s -X POST "http://localhost:8090/scrape" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Turkcell"}'
pkill -f "port-forward.*8090"
```

---

### 5.3 DÜŞÜK - İhale 0 Sonuç (Bazı Firmalar)

**Gözlem:**
- Koç Holding: 22 karar tarıyor, 0 eşleşme ✅ (doğru, yasaklı değil)
- Turkcell: 0 karar tarıyor, 0 gün ⚠️ (scraper hiç çalışmamış gibi)

**Olası Sebepler:**
1. Resmi Gazete'de o gün için veri yok
2. Rate limiting
3. PDF bulunamadı

**DEBUG:**
```bash
kubectl logs -n ihale-agent deployment/ihale-scraper --tail=200 | grep -i "turkcell\|error\|pdf"
```

---

### 5.4 ÖNERİ - Council Firma Adı Sorunu

**Gözlem:** Council kararında "XYZ Firması" diyor, gerçek firma adı değil

**Düzeltme:** `backend/app/council/council_service.py` veya prompt'larda firma adını inject et

---

## 6. ÇALIŞAN TEST SONUÇLARI

### Turkcell Raporu (2025-12-11 00:05)

```
Report ID: bbeb4002-ce15-4319-b329-3f5ab437479a
Süre: 127 saniye

Agent Sonuçları:
- TSG: ❌ Failed (Playwright ARM64 hatası)
- İhale: ✅ 8s, yasaklı değil, 0 karar bulundu
- News: ⚠️ 72s, 0 haber, 6/10 kaynak çalıştı

Council Kararı:
- Final Skor: 39/100
- Risk Seviyesi: Orta-Düşük
- Karar: Şartlı Onay
- Konsensüs: %71

Üye Skorları:
- Risk Analisti (Mehmet Bey): 55
- İş Analisti (Ayşe Hanım): 18
- Hukuk (Av. Zeynep): 45
- Medya (Deniz Bey): 20
- Sektör (Prof. Ali): 38
```

### Koç Holding (Önceki Test)

```
İhale K8s:
- Süre: 67.77s
- Taranan karar: 22
- Eşleşen: 0

News K8s v8:
- Süre: 107s
- Toplam haber: 25
- Koç ilgili: 6
- Kaynak başarı: 10/10
```

---

## 7. KLASÖR YAPISI

```
backend/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py      ← Ana koordinatör
│   │   ├── ihale_agent_k8s.py   ← K8s ihale client
│   │   ├── news_agent_k8s.py    ← K8s news client
│   │   ├── tsg/
│   │   │   ├── agent.py         ← TSG agent (LOCAL, BOZUK)
│   │   │   └── scraper.py
│   │   └── ...
│   ├── council/
│   │   └── council_service.py   ← Komite servisi
│   └── ...
├── scrapers/
│   └── ihale-scraper/
│       ├── main.py              ← İhale scraper (K8s)
│       └── Dockerfile
├── universal-scraper/
│   ├── main.py                  ← News scraper (K8s)
│   └── Dockerfile
├── llm-gateway/
│   ├── main.py                  ← LLM API gateway (K8s)
│   └── Dockerfile
└── k8s/
    ├── ihale-agent/             ← İhale K8s YAML'ları
    └── news-agent/              ← News K8s YAML'ları (?)
```

---

## 8. DEPLOY EDİLMİŞ IMAGE'LAR

| Image | Version | Namespace | Durum |
|-------|---------|-----------|-------|
| `ihale-scraper` | v2 | ihale-agent | ✅ |
| `news-universal-scraper` | v8 | news-agent | ✅ |
| `news-llm-gateway` | v8 | news-agent | ✅ |
| `news-orchestrator` | v2 | news-agent | ✅ |
| `ihale-orchestrator` | ? | ihale-agent | ✅ |
| `ihale-ocr` | ? | ihale-agent | ✅ |

---

## 9. ÖNEMLİ NOTLAR

### Minikube Docker Sorunu
```bash
# BU ÇALIŞMIYOR (zsh parse error):
eval $(minikube docker-env)

# BUNUN YERİNE:
docker build -t image:tag .
minikube image load image:tag
```

### Pod Restart Sonrası Browser Sıfırlama
Browser pool sorunlarında pod'u sil:
```bash
kubectl delete pod -n NAMESPACE -l app=APP_LABEL
```

### Port Forward Ölürse
```bash
pkill -f "port-forward"
# Sonra yeniden başlat
```

---

## 10. DEVAM EDECEKLER İÇİN

### Bartın (DevOps):
1. TSG'yi K8s'e taşı (İhale yapısını kopyala)
2. CI/CD pipeline ekle
3. Minikube yerine gerçek K8s cluster'a deploy

### Bekir (Frontend):
1. WebSocket bağlantısı test et
2. Agent progress gösterimi
3. Council transcript streaming

### Yamaç (AI - eğer devam edersem):
1. Council firma adı sorunu
2. News kaynak CSS selector'ları güncelle
3. TSG K8s agent wrapper'ı

---

## İletişim

Sorular için: Slack #kkb-hackathon veya direkt mesaj

**NOT:** Bu dosya commit edilmeli, ekip görsün!

---

## 11. GIT DEĞİŞİKLİKLERİ (UNCOMMITTED!)

> ⚠️ **DİKKAT:** Aşağıdaki değişiklikler henüz commit edilmedi!
> Son commit: `90f297c feat: Enhance Council Service...`
> Toplam: **700+ satır ekleme, 312 silme, 35 dosya**

### 11.1 Değiştirilen Dosyalar (Modified)

| Dosya | Satır Değişikliği | Açıklama |
|-------|-------------------|----------|
| `backend/app/agents/orchestrator.py` | +163 | K8s agent entegrasyonu, fallback mekanizması |
| `backend/app/council/council_service.py` | +342/-? | Council formatlaması, intelligence report |
| `backend/app/agents/tsg/captcha.py` | +221 | Captcha çözümleme iyileştirmeleri |
| `backend/app/agents/tsg/agent.py` | +50 | TSG agent güncellemeleri |
| `frontend/src/components/report-detail/*` | ~150 | UI component güncellemeleri |
| `frontend/src/hooks/useWebSocket.ts` | +13 | WebSocket iyileştirmeleri |
| `.env.example` | +2 | Yeni env var'lar |

### 11.2 Yeni Dosyalar (Untracked - GIT'E EKLENMELİ!)

```
?? backend/app/agents/ihale_agent_k8s.py      ← K8s İhale client
?? backend/app/agents/news_agent_k8s.py       ← K8s News client
?? backend/app/agents/progress_simulator.py   ← Progress simülatör
?? backend/browser-pool/                       ← Browser pool servisi
?? backend/k8s/                                ← TÜM K8s YAML'LAR!
?? backend/llm-gateway/                        ← LLM Gateway servisi
?? backend/news-orchestrator/                  ← News orchestrator
?? backend/scrapers/                           ← İhale scraper
?? backend/universal-scraper/                  ← News scraper
?? docs/DEV-STATUS.md                          ← Bu dosya!
?? frontend/src/utils/agentAdapter.ts          ← Agent adapter
```

### 11.3 K8s Klasör Yapısı (YENİ!)

```
backend/k8s/
├── namespace.yaml                    ← Ana namespace
├── deploy.sh                         ← Deploy script
├── configmaps/
│   └── scraper-config.yaml
├── ihale-agent/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── orchestrator-deployment.yaml
│   ├── scraper-deployment.yaml
│   └── ocr-deployment.yaml
└── services/
    ├── llm-gateway/
    │   └── deployment.yaml
    ├── browser-pool/
    │   └── deployment.yaml
    ├── scrapers/
    │   └── all-scrapers.yaml         ← 10 haber kaynağı
    └── orchestrator/
        └── deployment.yaml

backend/scrapers/
├── base/
├── ihale-ocr/
│   ├── main.py
│   └── Dockerfile
├── ihale-orchestrator/
│   ├── main.py
│   └── Dockerfile
├── ihale-scraper/
│   ├── main.py                       ← v2 FİXLENDİ!
│   └── Dockerfile
└── news_sources/
    └── ...

backend/llm-gateway/
├── main.py                           ← v8 FİXLENDİ!
├── Dockerfile
└── requirements.txt

backend/universal-scraper/
├── main.py                           ← v8 FİXLENDİ!
├── Dockerfile
└── requirements.txt
```

---

## 12. K8s KURULUM REHBERİ (YENİ MAKİNE İÇİN)

### 12.1 Önkoşullar

```bash
# macOS
brew install minikube kubectl docker

# Linux
# Docker: https://docs.docker.com/engine/install/
# Minikube: https://minikube.sigs.k8s.io/docs/start/
# kubectl: https://kubernetes.io/docs/tasks/tools/

# Minikube başlat
minikube start --cpus=4 --memory=8192 --driver=docker
```

### 12.2 Namespace'leri Oluştur

```bash
cd backend/k8s

# Namespace'leri oluştur
kubectl apply -f namespace.yaml
kubectl apply -f ihale-agent/namespace.yaml

# Namespace kontrol
kubectl get namespaces | grep -E "news-agent|ihale-agent"
```

### 12.3 İhale Agent Deploy

```bash
# 1. Image'ları build et
cd backend/scrapers/ihale-scraper
docker build -t ihale-scraper:v2 .

cd ../ihale-orchestrator
docker build -t ihale-orchestrator:v1 .

cd ../ihale-ocr
docker build -t ihale-ocr:v1 .

# 2. Minikube'a yükle
minikube image load ihale-scraper:v2
minikube image load ihale-orchestrator:v1
minikube image load ihale-ocr:v1

# 3. K8s'e deploy et
cd ../../k8s/ihale-agent
kubectl apply -f configmap.yaml
kubectl apply -f orchestrator-deployment.yaml
kubectl apply -f scraper-deployment.yaml
kubectl apply -f ocr-deployment.yaml

# 4. Pod'ları kontrol et
kubectl get pods -n ihale-agent
```

### 12.4 News Agent Deploy

```bash
# 1. Image'ları build et
cd backend/universal-scraper
docker build -t news-universal-scraper:v8 .

cd ../llm-gateway
docker build -t news-llm-gateway:v8 .

cd ../news-orchestrator
docker build -t news-orchestrator:v2 .

# 2. Minikube'a yükle
minikube image load news-universal-scraper:v8
minikube image load news-llm-gateway:v8
minikube image load news-orchestrator:v2

# 3. K8s'e deploy et
cd ../k8s/services
kubectl apply -f llm-gateway/deployment.yaml
kubectl apply -f scrapers/all-scrapers.yaml
kubectl apply -f orchestrator/deployment.yaml

# 4. Pod'ları kontrol et
kubectl get pods -n news-agent
```

### 12.5 Port Forward'lar

```bash
# Terminal 1: İhale
kubectl port-forward svc/ihale-orchestrator 8081:8080 -n ihale-agent

# Terminal 2: News
kubectl port-forward svc/news-orchestrator 8082:8080 -n news-agent

# VEYA arka planda:
kubectl port-forward svc/ihale-orchestrator 8081:8080 -n ihale-agent &
kubectl port-forward svc/news-orchestrator 8082:8080 -n news-agent &
```

### 12.6 Doğrulama

```bash
# Health check
curl -s http://localhost:8081/health | python3 -m json.tool
curl -s http://localhost:8082/health | python3 -m json.tool

# Test
curl -s -X POST "http://localhost:8081/api/ihale/check" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Koç Holding", "days": 7}'
```

---

## 13. HIZLI BAŞLANGIÇ (COPY-PASTE)

```bash
# 1. Repo'yu klonla
git clone <repo-url>
cd kkb-hackathon-goldenhead
git checkout dev/yamac

# 2. Backend başlat
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
redis-server &
celery -A app.workers.celery_app worker --loglevel=info -Q reports &
uvicorn main:app --host 0.0.0.0 --port 8000 &

# 3. K8s başlat (ayrı terminalde)
minikube start
kubectl port-forward svc/ihale-orchestrator 8081:8080 -n ihale-agent &
kubectl port-forward svc/news-orchestrator 8082:8080 -n news-agent &

# 4. Frontend başlat (ayrı terminalde)
cd frontend
npm install
npm run dev

# 5. Test et
curl -s http://localhost:8000/api/health  # Backend
curl -s http://localhost:8081/health       # İhale K8s
curl -s http://localhost:8082/health       # News K8s
```

---

## 14. YAMAÇ'IN YAKIM TARİHÇESİ

| Tarih | Ne Yaptım |
|-------|-----------|
| 8 Aralık | K8s altyapısı kuruldu, ihale-agent namespace |
| 9 Aralık | News agent K8s, 10 scraper deploy |
| 10 Aralık | LLM Gateway fix (max_tokens, None check) |
| 10 Aralık | Universal Scraper fix (5 search URL) |
| 10 Aralık | İhale Scraper fix (browser pool is_connected) |
| 11 Aralık | E2E test (Turkcell), DEV-STATUS.md yazıldı |

**Toplam çalışma:** ~3 gün yoğun K8s + debugging

---

## 15. COMMIT ÖNERİSİ

```bash
# Tüm yeni dosyaları ekle
git add backend/k8s/
git add backend/scrapers/
git add backend/llm-gateway/
git add backend/universal-scraper/
git add backend/news-orchestrator/
git add backend/browser-pool/
git add backend/app/agents/ihale_agent_k8s.py
git add backend/app/agents/news_agent_k8s.py
git add backend/app/agents/progress_simulator.py
git add frontend/src/utils/agentAdapter.ts
git add docs/DEV-STATUS.md

# Değiştirilen dosyaları ekle
git add backend/app/agents/orchestrator.py
git add backend/app/council/council_service.py
git add backend/app/agents/tsg/
git add frontend/src/

# Commit (örnek mesaj)
git commit -m "feat: K8s microservices for ihale and news agents

- İhale Agent K8s: browser pool fix, v2 deployed
- News Agent K8s: 10 scrapers, LLM gateway v8
- Orchestrator: K8s integration with fallback
- Council: enhanced formatting
- Frontend: UI improvements

K8s namespaces: ihale-agent, news-agent
See docs/DEV-STATUS.md for full details"
```
