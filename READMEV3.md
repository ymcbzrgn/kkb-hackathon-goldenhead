# 🏢 Firma İstihbarat Raporu Sistemi

> **KKB Agentic AI Hackathon 2024 - Konu 2**

Bir firma adı girin, yapay zeka agent'ları veri toplasın, 6 kişilik sanal kredi komitesi tartışsın, size kapsamlı istihbarat raporu çıksın.

---

## 📋 İçindekiler

- [Problem](#-problem)
- [Çözüm](#-çözüm)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Agent'lar](#-agentlar)
- [Council: Değerlendirme Komitesi](#-council-değerlendirme-komitesi)
- [Çıktılar](#-çıktılar)
- [Fark Yaratan Özellikler](#-fark-yaratan-özellikler)
- [Ekranlar](#-ekranlar)
- [Takım](#-takım)
- [Yol Haritası](#-yol-haritası)

---

## 🎯 Problem

Bir banka veya finans kurumunda kredi kararı verilmeden önce firma hakkında detaylı araştırma yapılması gerekiyor:

| Araştırılacak | Kaynak | Manuel Süre |
|---------------|--------|-------------|
| Firma bilgileri, ortaklar, sermaye | Ticaret Sicili Gazetesi | 2-3 saat |
| İhale yasaklı mı? | EKAP Sistemi | 30 dk |
| Olumsuz haberler var mı? | İnternet | 1-2 saat |
| Tüm verileri birleştirip rapor yazma | - | 2-3 saat |

**Toplam: 6-8 saat / firma**

Bu süreç:
- ⏰ Çok uzun sürüyor
- 😫 Tekrarlayan ve sıkıcı
- ⚠️ İnsan hatasına açık
- 📊 Standart değil (kişiden kişiye değişiyor)

---

## 💡 Çözüm

**Tek bir firma adı girin, 40 dakikada kapsamlı istihbarat raporu alın.**

Sistemimiz iki aşamalı çalışıyor:

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  AŞAMA 1: VERİ TOPLAMA (~5 dakika)                            │
│  ─────────────────────────────────                            │
│  4 yapay zeka agent'ı paralel çalışarak                       │
│  tüm kaynaklardan veri topluyor                               │
│                                                                │
│     📰 TSG Agent      → Ticaret Sicili Gazetesi               │
│     🚫 İhale Agent    → EKAP Yasaklı Listesi                  │
│     📺 Haber Agent    → İnternet Haberleri                    │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  AŞAMA 2: DEĞERLENDİRME KOMİTESİ (~35 dakika)                 │
│  ─────────────────────────────────────────────                │
│  6 kişilik sanal kredi komitesi, toplanan verileri            │
│  farklı perspektiflerden değerlendirip tartışıyor             │
│                                                                │
│     🔴 Risk Analisti      "Bu firma neden riskli?"            │
│     🟢 İş Analisti        "Bu firma neden fırsat?"            │
│     ⚖️ Hukuk Uzmanı       "Yasal durum ne?"                   │
│     📰 İtibar Analisti    "Piyasa ne düşünüyor?"              │
│     📊 Sektör Uzmanı      "Sektör nasıl gidiyor?"             │
│     👨‍⚖️ Komite Başkanı     "Final karar ne?"                  │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ÇIKTI: Kapsamlı İstihbarat Raporu                            │
│  ─────────────────────────────────                            │
│  • Risk Skoru (0-100)                                         │
│  • Komite Kararı + Gerekçe                                    │
│  • Tartışma Özeti                                             │
│  • Tüm destekleyici veriler                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Sistem Mimarisi

### Büyük Resim

```
                         ┌─────────────┐
                         │   Kullanıcı │
                         └──────┬──────┘
                                │
                         "ABC A.Ş. hakkında
                          rapor oluştur"
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                        WEB ARAYÜZÜ                            │
│                   (React + WebSocket)                         │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│                    🎼 ORKESTRATÖR                             │
│                                                               │
│   Tüm süreci yöneten ana kontrol merkezi                     │
│   Agent'ları başlatır, Council'ı toplar, raporu üretir       │
│                                                               │
└───────────────────────────────┬───────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   📰 TSG Agent  │ │  🚫 İhale Agent │ │  📺 Haber Agent │
│                 │ │                 │ │                 │
│ Ticaret Sicili  │ │ EKAP Sistemi    │ │ Haber Siteleri  │
│ PDF'leri okur   │ │ Yasak kontrol   │ │ Sentiment analiz│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │    📦 VERİ HAVUZU     │
                 │                       │
                 │  Tüm toplanan veriler │
                 │  yapılandırılmış halde│
                 └───────────┬───────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│                   🏛️ COUNCIL (KOMİTE)                         │
│                                                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │🔴    │ │🟢    │ │⚖️    │ │📰    │ │📊    │ │👨‍⚖️   │      │
│  │Risk  │ │ İş   │ │Hukuk │ │Medya │ │Sektör│ │Başkan│      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
│                                                               │
│  Sunum → Tartışma → Uzlaşma → Final Karar                    │
│                                                               │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   📋 FİNAL RAPOR      │
                    │                       │
                    │  Risk: 35/100         │
                    │  Karar: Şartlı Onay   │
                    │  + Tartışma Transcript│
                    └───────────────────────┘
```

---

## 🤖 Agent'lar

Sistemin ilk aşamasında 3 uzman agent paralel çalışarak veri topluyor.

### 📰 TSG Agent (Ticaret Sicili Gazetesi)

**Görevi:** Firmanın resmi sicil kayıtlarını bulmak ve analiz etmek

```
Girdi: Firma adı
          │
          ▼
    TSG web sitesinde arama
          │
          ▼
    İlgili ilanların PDF'lerini indirme
          │
          ▼
    Vision AI ile PDF okuma (qwen3-omni-30b)
          │
          ▼
Çıktı: Yapısal veri
       ├── Kuruluş tarihi
       ├── Sermaye (ve değişim geçmişi)
       ├── Ortaklar ve pay oranları
       ├── Yönetim kurulu üyeleri
       ├── Adres değişiklikleri
       └── Faaliyet konusu
```

**Neden Vision AI?**
TSG PDF'leri bazen taranmış görsel, bazen karmaşık tablo içeriyor. Vision modeli (qwen3-omni-30b) sayfayı "görüp" doğru veriyi çıkarabiliyor.

---

### 🚫 İhale Agent (EKAP)

**Görevi:** Firmanın kamu ihalelerinden yasaklı olup olmadığını kontrol etmek

```
Girdi: Firma adı / Vergi no
          │
          ▼
    EKAP sisteminde arama
          │
          ▼
    Yasaklılık durumu kontrolü
          │
          ▼
Çıktı: Yasak durumu
       ├── Aktif yasak var mı?
       ├── Yasak sebebi
       ├── Başlangıç/bitiş tarihi
       ├── Yasaklayan kurum
       └── Geçmiş yasaklar
```

**Neden önemli?**
İhale yasağı ciddi bir kırmızı bayrak. Yolsuzluk, sahtecilik, sözleşme ihlali gibi sebeplerden verilebilir.

---

### 📺 Haber Agent

**Görevi:** Firma hakkındaki haberleri toplamak ve duygu analizi yapmak

```
Girdi: Firma adı
          │
          ▼
    Haber sitelerinde arama
          │
          ▼
    Son 12 ayın haberlerini toplama
          │
          ▼
    Her haber için sentiment analizi (gpt-oss-120b)
          │
          ▼
Çıktı: Haber analizi
       ├── Toplam haber sayısı
       ├── Pozitif / Negatif / Nötr dağılımı
       ├── Öne çıkan haberler
       ├── Trend (iyileşiyor mu, kötüleşiyor mu?)
       └── Her haberin detayı
```

**Sentiment Analizi:**
```
"ABC Şirketi 100 kişiyi işten çıkardı" → 😟 Negatif
"ABC Şirketi yeni fabrika açtı"       → 😊 Pozitif  
"ABC Şirketi toplantı düzenledi"      → 😐 Nötr
```

---

## 🏛️ Council: Değerlendirme Komitesi

Sistemin kalbi. Agent'lar veri topladıktan sonra, 6 kişilik sanal bir kredi komitesi bu verileri değerlendiriyor.

### Neden Council?

| Tek LLM'e Sormak | Council Yaklaşımı |
|------------------|-------------------|
| "Bu firma riskli mi?" | 6 farklı perspektif |
| 1 cevap, 1 bakış açısı | Tartışma, çelişki, uzlaşma |
| Kara kutu karar | Şeffaf karar süreci |
| "AI böyle dedi" | "Komite şu gerekçeyle karar verdi" |

**Gerçek bankacılıkta da böyle çalışır:** Kredi kararları tek kişi tarafından değil, komite tarafından tartışılarak alınır.

### Komite Üyeleri

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  🔴 MEHMET BEY              🟢 AYŞE HANIM                  │
│  Baş Risk Analisti          İş Geliştirme Müdürü           │
│                                                             │
│  25 yıl deneyim             15 yıl deneyim                 │
│  Temkinli, şüpheci          Fırsatçı, iyimser              │
│                                                             │
│  "Bu firma neden            "Bu firma neden                │
│   batabilir?"                büyüyebilir?"                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⚖️ AV. ZEYNEP HANIM        📰 DENİZ BEY                   │
│  Hukuk Müşaviri             İtibar Analisti                │
│                                                             │
│  20 yıl deneyim             12 yıl deneyim                 │
│  Tarafsız, belgeci          Algı odaklı                    │
│                                                             │
│  "Yasal durum ne?"          "Piyasa ne düşünüyor?"         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 PROF. DR. ALİ BEY       👨‍⚖️ GENEL MÜDÜR YARDIMCISI     │
│  Sektör Uzmanı              Komite Başkanı                 │
│                                                             │
│  30 yıl deneyim             30+ yıl deneyim                │
│  Makro bakışlı              Sentezci, karar odaklı         │
│                                                             │
│  "Sektör ne durumda?"       "Final karar ne olmalı?"       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Toplantı Akışı

```
AŞAMA 1: AÇILIŞ (~2 dk)
─────────────────────────
👨‍⚖️ Moderatör toplantıyı açar
   Verileri özetler
   "Şimdi görüşlerinizi alalım..."

          │
          ▼

AŞAMA 2-6: UZMAN SUNUMLARI (~15 dk)
───────────────────────────────────
Her uzman sırayla sunum yapar:

🔴 Mehmet Bey: "65 puan veriyorum, çünkü..."
🟢 Ayşe Hanım: "25 puan veriyorum, çünkü..."
⚖️ Zeynep Hanım: "30 puan, yasal durum şöyle..."
📰 Deniz Bey: "30 puan, haberler olumlu..."
📊 Prof. Ali: "35 puan, sektör büyüyor..."

          │
          ▼

AŞAMA 7: TARTIŞMA (~15 dk)
──────────────────────────
En farklı görüşler (65 vs 25) karşı karşıya gelir:

🔴 "8 ayda 3 yönetici değişikliği normal mi?"
🟢 "Büyüyen şirketlerde bu normal!"
📰 "Haberlere baktım, ayrılık sebebi..."
⚖️ "TSG'de pay alan taraf yatırım şirketi..."
🔴 "Hmm, bu bilgiyi bilmiyordum. Revize edebilirim."

          │
          ▼

AŞAMA 8: FİNAL KARAR (~5 dk)
────────────────────────────
👨‍⚖️ Moderatör özetler:
   
   "Final skorlar: 45, 25, 30, 30, 35
    Ortalama: 33/100 - ORTA-DÜŞÜK RİSK
    
    Karar: ŞARTLI ONAY
    Şartlar: 6 aylık izleme, bildirim covenant'ı
    
    Muhalefet Notu: Risk analisti başlangıçta
    65 vermiş, tartışmada 45'e düşürmüştür."
```

### Örnek Diyalog

```
🔴 MEHMET BEY:
"Arkadaşlar, 8 ayda 3 genel müdür değişikliği var.
25 yıllık tecrübemle söylüyorum, bu pattern'i 
gördüğümde genellikle arkasında sorun çıkıyor.
Risk skorumu 65 olarak belirliyorum."

🟢 AYŞE HANIM:
"Mehmet Bey, değişikliklerin sebebine bakalım.
Firma yazılımdan AI'a pivot yapıyor. Büyüyen 
şirketlerde reorganizasyon normal. Ayrıca 
sermaye %67 artmış - yatırımcı güveni var.
Ben 25 puan veriyorum."

🔴 MEHMET BEY:
"Peki ama TSG'de değişiklik sebebi yazmıyor.
Nereden biliyoruz bunları?"

📰 DENİZ BEY:
"Haberlerde var aslında. İkinci GM için 
'kendi girişimini kurmak için ayrıldı' yazıyor.
Negatif bir ayrılık değilmiş gibi görünüyor."

🔴 MEHMET BEY:
"Bu bilgi önemli. Değerlendirmemi revize ediyorum.
65'ten 45'e düşürüyorum ama izleme şart."
```

---

## 📄 Çıktılar

### Ana Çıktı: Firma İstihbarat Raporu

```
╔═══════════════════════════════════════════════════════════════╗
║              FİRMA İSTİHBARAT RAPORU                          ║
║              ABC Teknoloji A.Ş.                               ║
║              03 Aralık 2024                                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────────────┐    ┌─────────────────────┐          ║
║  │   RİSK SKORU        │    │   KOMİTE UYUMU      │          ║
║  │                     │    │                     │          ║
║  │     33 / 100        │    │       %85           │          ║
║  │    🟡 ORTA-DÜŞÜK    │    │   ✅ KONSENSÜS      │          ║
║  └─────────────────────┘    └─────────────────────┘          ║
║                                                               ║
║  KOMİTE KARARI: ✅ ŞARTLI ONAY                               ║
║                                                               ║
║  Şartlar:                                                     ║
║  • 6 aylık izleme periyodu                                   ║
║  • Yönetim değişikliği bildirim yükümlülüğü                  ║
║  • Çeyreklik finansal rapor talebi                           ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║  FİRMA BİLGİLERİ                                             ║
║  ├── Kuruluş: 15.03.2018                                     ║
║  ├── Sermaye: 5.000.000 TL                                   ║
║  ├── Adres: İstanbul, Maslak                                 ║
║  └── Faaliyet: Yazılım, Yapay Zeka                           ║
║                                                               ║
║  ORTAKLIK YAPISI                                             ║
║  ├── Ahmet Yılmaz: %40                                       ║
║  ├── XYZ Yatırım A.Ş.: %20 (yeni)                           ║
║  └── Mehmet Demir: %40                                       ║
║                                                               ║
║  İHALE DURUMU: ✅ Yasak bulunmamaktadır                      ║
║                                                               ║
║  MEDYA ANALİZİ                                               ║
║  ├── Toplam: 24 haber                                        ║
║  ├── 😊 Pozitif: 15 (%62)                                    ║
║  ├── 😐 Nötr: 5 (%21)                                        ║
║  └── 😟 Negatif: 4 (%17)                                     ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║  KOMİTE DEĞERLENDİRME ÖZETİ                                  ║
║                                                               ║
║  🔴 Risk Analisti (Mehmet Bey): 65 → 45                      ║
║     "Yönetici değişikliği endişe verici ancak                ║
║      tartışmada ortaya çıkan bilgilerle revize ettim"        ║
║                                                               ║
║  🟢 İş Analisti (Ayşe Hanım): 25                             ║
║     "Sermaye artışı ve sektör potansiyeli olumlu"            ║
║                                                               ║
║  ⚖️ Hukuk Uzmanı (Zeynep Hanım): 30                          ║
║     "Yasal açıdan temiz, vergi yapılandırması geçmişi var"   ║
║                                                               ║
║  📰 İtibar Analisti (Deniz Bey): 30                          ║
║     "Medya algısı olumlu, trend yukarı yönlü"                ║
║                                                               ║
║  📊 Sektör Uzmanı (Prof. Ali): 35                            ║
║     "Sektör büyüyor, firma ortalamanın üstünde"              ║
║                                                               ║
║  ⚠️ MUHALEFET NOTU:                                          ║
║  Risk analisti başlangıçta yüksek risk görmüş (65),          ║
║  tartışma sonunda revize etmiştir (45). İzleme               ║
║  şartlarının kritik olduğunu vurgulamıştır.                  ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║  📋 KAYNAKLAR                                                 ║
║  • TSG: 8 ilan analiz edildi                                 ║
║  • EKAP: Kontrol edildi                                      ║
║  • Medya: 24 haber analiz edildi                             ║
║                                                               ║
║  ⏱️ Toplam Süre: 38 dakika                                   ║
║  📅 Rapor Tarihi: 03.12.2024 14:45                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Ek Çıktılar

| Çıktı | Açıklama |
|-------|----------|
| **Toplantı Transcript** | Komite toplantısının tam kaydı, tüm diyaloglar |
| **JSON Veri** | API entegrasyonu için yapısal veri formatı |
| **Zaman Çizelgesi** | Firma hakkındaki önemli olayların kronolojik görünümü |

---

## 🌟 Fark Yaratan Özellikler

### 1. Council: Komite Kararı
Tek bir AI'a sormak yerine, 6 farklı uzman perspektifinden değerlendirme. Gerçek bankacılık süreçlerini yansıtıyor.

### 2. Canlı Tartışma
Kullanıcı sadece skoru görmüyor, o skorun arkasındaki **tartışmayı** izliyor. Tam şeffaflık.

### 3. Dinamik Skor Revizyonu
Uzmanlar tartışmada birbirini ikna edebiliyor. Risk analisti 65 verdi, tartışma sonunda 45'e düşürdü. Gerçek bir değerlendirme bu.

### 4. Muhalefet Notu
Bankacılıkta yasal zorunluluk olan muhalefet notu bizde de var. Karar sürecinin şeffaflığı için kritik.

### 5. Vision AI ile PDF Okuma
Taranmış, tablolu, karmaşık PDF'leri doğru okuyabilme. qwen3-omni-30b multimodal modeli ile.

### 6. Konsensüs Skoru
Komite ne kadar uyumlu? %85 konsensüs = güvenilir karar. %50 konsensüs = tartışmalı, dikkat.

---

## 🎨 Ekranlar

### Ana Sayfa

```
┌─────────────────────────────────────────────────────────────────┐
│  🏢 Firma İstihbarat Sistemi                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔍 Firma Adı veya Vergi No                    [Ara]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📊 Son Raporlar                                               │
│                                                                 │
│  ┌──────────────────┬──────────────────┬──────────────────┐   │
│  │ XYZ Ltd. Şti.    │ ABC A.Ş.         │ DEF Holding      │   │
│  │ 🟢 Risk: 22      │ 🟡 Risk: 45      │ 🔴 Risk: 78      │   │
│  │ ✅ Onay          │ ⚠️ Şartlı        │ ❌ Red           │   │
│  │ 2 saat önce      │ 1 gün önce       │ 3 gün önce       │   │
│  └──────────────────┴──────────────────┴──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Veri Toplama Ekranı

```
┌─────────────────────────────────────────────────────────────────┐
│  📦 VERİ TOPLANIYOR                              ⏱️ 02:34       │
│  ABC Teknoloji A.Ş.                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Agent Durumları:                                               │
│                                                                 │
│  📰 TSG Agent          [██████████░░░░░░░░░░] 50%              │
│     └─ 4/8 PDF analiz edildi                                   │
│                                                                 │
│  🚫 İhale Agent        [████████████████████] 100% ✅          │
│     └─ Yasak bulunamadı                                        │
│                                                                 │
│  📺 Haber Agent        [████████████████░░░░] 80%              │
│     └─ 19/24 haber analiz edildi                               │
│                                                                 │
│  ⏳ Council            [░░░░░░░░░░░░░░░░░░░░] Bekliyor         │
│     └─ Veriler tamamlanınca başlayacak                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Council Toplantı Ekranı

```
┌─────────────────────────────────────────────────────────────────┐
│  🏛️ KOMİTE TOPLANTISI                              ⏱️ 12:34    │
│  ABC Teknoloji A.Ş.                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │              🔴 MEHMET BEY                              │   │
│  │              Baş Risk Analisti                          │   │
│  │                                                         │   │
│  │  "8 ayda 3 genel müdür değişikliği var. 25 yıllık      │   │
│  │   tecrübemle söylüyorum, bu pattern'i gördüğümde       │   │
│  │   genellikle arkasında sorun çıkıyor..."               │   │
│  │                                                 ▊       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Komite Skorları:                                              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │ 🔴   │ │ 🟢   │ │ ⚖️   │ │ 📰   │ │ 📊   │ │ 👨‍⚖️  │       │
│  │  65  │ │  --  │ │  --  │ │  --  │ │  --  │ │      │       │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│  Sunum    Bekliyor Bekliyor Bekliyor Bekliyor Dinliyor        │
│                                                                 │
│  İlerleme: [████████░░░░░░░░░░░░] Aşama 2/8: Risk Sunumu       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tartışma Ekranı

```
┌─────────────────────────────────────────────────────────────────┐
│  🏛️ TARTIŞMA                                       ⏱️ 28:15    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔥 Konu: Yönetici Değişikliği Riski                           │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │ 🔴 MEHMET BEY        │  │ 🟢 AYŞE HANIM        │            │
│  │ Risk: 65             │  │ Risk: 25             │            │
│  │                      │  │                      │            │
│  │ "8 ayda 3 değişim    │  │ "Büyüyen şirketlerde │            │
│  │  çok fazla!"         │  │  bu normal, AI'a     │            │
│  │                      │  │  pivot yapıyorlar"   │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                 │
│  💬 Deniz Bey: "Haberlerde ikinci GM için 'kendi girişimini    │
│     kurmak için ayrıldı' yazıyor..."                           │
│                                                                 │
│  🔴 Mehmet Bey: "Bu bilgi önemli. Revize edebilirim..."        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Final Karar Ekranı

```
┌─────────────────────────────────────────────────────────────────┐
│  🏛️ KOMİTE KARARI                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         ╔═════════════════════════════════════════╗            │
│         ║         ✅ ŞARTLI ONAY                  ║            │
│         ╚═════════════════════════════════════════╝            │
│                                                                 │
│    ┌─────────────────┐        ┌─────────────────┐              │
│    │  RİSK SKORU     │        │   KONSENSÜS     │              │
│    │     33/100      │        │      %85        │              │
│    │  🟡 ORTA-DÜŞÜK  │        │   ✅ YÜKSEK     │              │
│    └─────────────────┘        └─────────────────┘              │
│                                                                 │
│    Skor Değişimleri:                                           │
│    🔴 Mehmet Bey   65 → 45 📉 (revize)                         │
│    🟢 Ayşe Hanım   25 → 25                                     │
│    ⚖️ Zeynep H.    30 → 30                                     │
│    📰 Deniz Bey    30 → 30                                     │
│    📊 Prof. Ali    35 → 35                                     │
│                                                                 │
│    ⚠️ Muhalefet: Mehmet Bey başlangıçta yüksek risk görmüş     │
│                                                                 │
│              [📄 Rapor İndir]  [▶️ Toplantıyı İzle]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 👥 Takım

| Üye | Rol | Odak |
|-----|-----|------|
| **Kişi A** | Frontend | React, WebSocket, UI/UX |
| **Kişi B** | Backend + DevOps | FastAPI, DB, Docker |
| **Kişi C** | AI/ML | Agent'lar, Council, LLM |

### Çalışma Prensibi

- **Klasör Bazlı İzolasyon:** Herkes kendi alanında çalışıyor
- **Interface First:** Önce API sözleşmesi, sonra implementasyon
- **Günlük Sync:** 10 dakikalık standup
- **Feature Branch:** Her özellik ayrı branch'te

---

## 🗓️ Yol Haritası

### Hafta 1: Temel Yapı (2-8 Aralık)

| Gün | Frontend | Backend | AI/ML |
|-----|----------|---------|-------|
| 1 | Proje setup | Docker + FastAPI | LLM API test |
| 2 | Dashboard iskelet | DB + Models | PDF okuma |
| 3 | WebSocket client | WebSocket + Celery | İhale scraper |
| 4 | Rapor sayfası | RAG pipeline | TSG scraper |
| 5 | Council UI | Risk service | Haber scraper |
| 6 | Timeline | Rapor pipeline | Council service |
| 7 | PDF export | CI/CD | Prompt tuning |

### Hafta 2: Entegrasyon (9-14 Aralık)

| Gün | Görev |
|-----|-------|
| 8-10 | Full entegrasyon, bug fix, performans |
| 11-12 | Demo hazırlık, örnek veriler |
| 13-14 | Final test, sunum provası |

---

## 🎤 Demo Senaryosu

**Süre: 8 dakika**

```
0:00 - 1:00  │ Problem tanıtımı
             │ "Bankada firma araştırması 6-8 saat sürüyor..."
             │
1:00 - 2:00  │ Çözüm tanıtımı  
             │ "Biz bunu 40 dakikaya düşürdük, üstelik..."
             │
2:00 - 6:00  │ Canlı demo
             │ • Firma adı girişi
             │ • Agent'ların çalışması (hızlandırılmış)
             │ • Council toplantısı (önemli anlar)
             │ • Final rapor
             │
6:00 - 7:00  │ Teknik derinlik
             │ • Vision AI ile PDF okuma
             │ • Council tartışma mekanizması
             │
7:00 - 8:00  │ Kapanış
             │ • Potansiyel kullanım alanları
             │ • Sorular
```

---

## 🔮 Gelecek Vizyonu

| Özellik | Açıklama |
|---------|----------|
| **Ses Sentezi** | Her komite üyesinin farklı sesi |
| **Video Avatar** | Animasyonlu karakterler |
| **Öğrenen Sistem** | Gerçek sonuçlarla karşılaştırma |
| **Sektör Modülleri** | İnşaat, perakende, üretim için özel analiz |
| **Karşılaştırmalı Rapor** | İki firmayı yan yana değerlendirme |

---

<div align="center">

**🏆 KKB Agentic AI Hackathon 2024**

*Firma İstihbarat Raporu Sistemi*

*Agent'lar toplar, Council tartışır, siz karar verirsiniz.*

</div>
