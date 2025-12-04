/**
 * Mock Data
 * Test ve geliştirme için örnek veriler
 */

import type { 
  ReportListItem, 
  ReportDetail,
  TsgData,
  IhaleData,
  NewsData,
  CouncilDecision,
  CouncilMember,
  TranscriptEntry,
} from '@/types';

// ==================== Council Members ====================

export const MOCK_COUNCIL_MEMBERS: CouncilMember[] = [
  { id: 'moderator', name: 'Genel Müdür Yardımcısı', role: 'Komite Başkanı', emoji: '👔' },
  { id: 'risk_analyst', name: 'Mehmet Bey', role: 'Baş Risk Analisti', emoji: '🛡️' },
  { id: 'business_analyst', name: 'Ayşe Hanım', role: 'İş Geliştirme Müdürü', emoji: '💼' },
  { id: 'legal_expert', name: 'Av. Zeynep Hanım', role: 'Hukuk Müşaviri', emoji: '⚖️' },
  { id: 'media_analyst', name: 'Deniz Bey', role: 'İtibar Analisti', emoji: '📡' },
  { id: 'sector_expert', name: 'Prof. Dr. Ali Bey', role: 'Sektör Uzmanı', emoji: '🎓' },
];

// ==================== Agent Data ====================

export const MOCK_TSG_DATA: TsgData = {
  kurulus_tarihi: '2018-03-15',
  sermaye: 5000000,
  sermaye_para_birimi: 'TRY',
  adres: 'Maslak, İstanbul',
  faaliyet_konusu: 'Yazılım geliştirme, yapay zeka',
  ortaklar: [
    { ad: 'Ahmet Yılmaz', pay_orani: 40 },
    { ad: 'XYZ Yatırım A.Ş.', pay_orani: 20 },
    { ad: 'Mehmet Demir', pay_orani: 40 },
  ],
  yonetim_kurulu: [
    { ad: 'Ahmet Yılmaz', gorev: 'Başkan' },
    { ad: 'Ayşe Kaya', gorev: 'Üye' },
  ],
  sermaye_degisiklikleri: [
    { tarih: '2024-03-01', eski: 3000000, yeni: 5000000 },
  ],
  yonetici_degisiklikleri: [
    { tarih: '2024-01-15', eski: 'Ali Veli', yeni: 'Ayşe Kaya', gorev: 'Genel Müdür' },
  ],
};

export const MOCK_IHALE_DATA: IhaleData = {
  yasak_durumu: false,
  aktif_yasak: null,
  gecmis_yasaklar: [],
};

export const MOCK_NEWS_DATA: NewsData = {
  toplam_haber: 24,
  pozitif: 15,
  negatif: 4,
  notr: 5,
  sentiment_score: 0.62,
  trend: 'yukari',
  onemli_haberler: [
    {
      baslik: 'ABC Teknoloji 50 kişilik istihdam sağlayacak',
      kaynak: 'ekonomi.com',
      tarih: '2024-10-15',
      sentiment: 'pozitif',
      url: 'https://ekonomi.com/haber/1',
    },
    {
      baslik: 'ABC Teknoloji AI alanında büyük yatırım yaptı',
      kaynak: 'teknoloji.net',
      tarih: '2024-09-20',
      sentiment: 'pozitif',
      url: 'https://teknoloji.net/haber/2',
    },
    {
      baslik: 'ABC Teknoloji vergi yapılandırması yaptı',
      kaynak: 'finans.com',
      tarih: '2023-09-20',
      sentiment: 'negatif',
      url: 'https://finans.com/haber/3',
    },
  ],
};

// ==================== Transcript ====================

export const MOCK_TRANSCRIPT: TranscriptEntry[] = [
  {
    timestamp: '2024-12-03T14:32:00Z',
    phase: 'opening',
    speaker_id: 'moderator',
    speaker_name: 'Genel Müdür Yardımcısı',
    speaker_emoji: '👔',
    content: 'Değerli komite üyeleri, bugün ABC Teknoloji A.Ş. hakkında değerlendirme yapacağız. Her üyemiz sırasıyla görüşlerini paylaşacak ve ardından tartışma aşamasına geçeceğiz.',
    risk_score: null,
  },
  {
    timestamp: '2024-12-03T14:35:00Z',
    phase: 'presentation',
    speaker_id: 'risk_analyst',
    speaker_name: 'Mehmet Bey',
    speaker_emoji: '🛡️',
    content: 'Teşekkürler Başkanım. TSG kayıtlarını inceledim. Şirket 2018 yılında kurulmuş, görece genç bir firma. Sermaye artışı pozitif bir sinyal ancak yönetim kurulunda son 1 yılda değişiklik olması dikkat çekici. Risk değerlendirmem: 65/100.',
    risk_score: 65,
  },
  {
    timestamp: '2024-12-03T14:40:00Z',
    phase: 'presentation',
    speaker_id: 'business_analyst',
    speaker_name: 'Ayşe Hanım',
    speaker_emoji: '💼',
    content: 'İş modeli açısından değerlendirdiğimde, AI ve yazılım sektörü son derece dinamik. Firmanın sermaye artışı yapması büyüme iştahını gösteriyor. Ortaklık yapısı dengeli görünüyor. Risk değerlendirmem: 25/100.',
    risk_score: 25,
  },
  {
    timestamp: '2024-12-03T14:45:00Z',
    phase: 'presentation',
    speaker_id: 'legal_expert',
    speaker_name: 'Av. Zeynep Hanım',
    speaker_emoji: '⚖️',
    content: 'Hukuki açıdan incelediğimde, EKAP kayıtlarında herhangi bir ihale yasağı bulunmuyor. Şirketin temiz bir sicili var. Ancak yönetici değişiklikleri takip edilmeli. Risk değerlendirmem: 30/100.',
    risk_score: 30,
  },
  {
    timestamp: '2024-12-03T14:50:00Z',
    phase: 'presentation',
    speaker_id: 'media_analyst',
    speaker_name: 'Deniz Bey',
    speaker_emoji: '📡',
    content: 'Medya taramasında 24 haber tespit ettim. Sentiment analizi %62 pozitif çıktı. İstihdam haberleri öne çıkıyor. Tek negatif sinyal vergi yapılandırması haberi, ancak bu yaygın bir uygulama. Risk değerlendirmem: 30/100.',
    risk_score: 30,
  },
  {
    timestamp: '2024-12-03T14:55:00Z',
    phase: 'presentation',
    speaker_id: 'sector_expert',
    speaker_name: 'Prof. Dr. Ali Bey',
    speaker_emoji: '🎓',
    content: 'Sektörel açıdan bakıldığında, AI ve yazılım sektörü Türkiye\'de hızla büyüyor. Bu firmalar genellikle düşük sabit varlık, yüksek insan kaynağı ile çalışır. Şirketin profili sektör normlarına uygun. Risk değerlendirmem: 35/100.',
    risk_score: 35,
  },
  {
    timestamp: '2024-12-03T15:00:00Z',
    phase: 'discussion',
    speaker_id: 'moderator',
    speaker_name: 'Genel Müdür Yardımcısı',
    speaker_emoji: '👔',
    content: 'Teşekkürler herkese. Mehmet Bey\'in 65 puanlık risk değerlendirmesi diğerlerinden yüksek. Mehmet Bey, bu konuda görüşlerinizi alabilir miyiz?',
    risk_score: null,
  },
  {
    timestamp: '2024-12-03T15:02:00Z',
    phase: 'discussion',
    speaker_id: 'risk_analyst',
    speaker_name: 'Mehmet Bey',
    speaker_emoji: '🛡️',
    content: 'Haklısınız Başkanım. Diğer üyelerin sunumlarını dinledikten sonra bazı endişelerim hafifledi. Özellikle EKAP\'ta temiz sicil ve pozitif medya yansıması önemli. Ancak izleme şartı koymamızı öneririm. Puanımı 45\'e revize ediyorum.',
    risk_score: null,
  },
  {
    timestamp: '2024-12-03T15:05:00Z',
    phase: 'decision',
    speaker_id: 'moderator',
    speaker_name: 'Genel Müdür Yardımcısı',
    speaker_emoji: '👔',
    content: 'Tartışmayı değerlendirdiğimizde, konsensüs oluşmuştur. Final skor 33/100, risk seviyesi orta-düşük. Kararımız ŞARTLI ONAY\'dır. Şartlarımız: 6 aylık izleme periyodu, yönetim değişikliği bildirim yükümlülüğü ve çeyreklik finansal rapor talebi.',
    risk_score: null,
  },
];

// ==================== Council Decision ====================

export const MOCK_COUNCIL_DECISION: CouncilDecision = {
  final_score: 33,
  risk_level: 'orta_dusuk',
  decision: 'sartli_onay',
  consensus: 0.85,
  conditions: [
    '6 aylık izleme periyodu',
    'Yönetim değişikliği bildirim yükümlülüğü',
    'Çeyreklik finansal rapor talebi',
  ],
  dissent_note: 'Risk analisti başlangıçta yüksek risk görmüş (65), tartışma sonunda revize etmiştir (45). İzleme şartlarının kritik olduğunu vurgulamıştır.',
  scores: {
    initial: {
      risk_analyst: 65,
      business_analyst: 25,
      legal_expert: 30,
      media_analyst: 30,
      sector_expert: 35,
    },
    final: {
      risk_analyst: 45,
      business_analyst: 25,
      legal_expert: 30,
      media_analyst: 30,
      sector_expert: 35,
    },
  },
  duration_seconds: 2100,
  transcript: MOCK_TRANSCRIPT,
};

// ==================== Reports ====================

export const MOCK_REPORTS: ReportListItem[] = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    company_name: 'ABC Teknoloji A.Ş.',
    company_tax_no: '1234567890',
    status: 'completed',
    final_score: 33,
    risk_level: 'orta_dusuk',
    decision: 'sartli_onay',
    created_at: '2024-12-03T14:30:00Z',
    completed_at: '2024-12-03T15:08:00Z',
    duration_seconds: 2280,
  },
  {
    id: '660e8400-e29b-41d4-a716-446655440001',
    company_name: 'XYZ Holding A.Ş.',
    company_tax_no: null,
    status: 'processing',
    final_score: null,
    risk_level: null,
    decision: null,
    created_at: '2024-12-03T15:00:00Z',
    completed_at: null,
    duration_seconds: null,
  },
  {
    id: '770e8400-e29b-41d4-a716-446655440002',
    company_name: 'DEF İnşaat Ltd. Şti.',
    company_tax_no: '9876543210',
    status: 'completed',
    final_score: 72,
    risk_level: 'orta_yuksek',
    decision: 'red',
    created_at: '2024-12-02T10:00:00Z',
    completed_at: '2024-12-02T10:45:00Z',
    duration_seconds: 2700,
  },
  {
    id: '880e8400-e29b-41d4-a716-446655440003',
    company_name: 'GHI Lojistik A.Ş.',
    company_tax_no: '5555555555',
    status: 'completed',
    final_score: 18,
    risk_level: 'dusuk',
    decision: 'onay',
    created_at: '2024-12-01T09:00:00Z',
    completed_at: '2024-12-01T09:35:00Z',
    duration_seconds: 2100,
  },
  {
    id: '990e8400-e29b-41d4-a716-446655440004',
    company_name: 'JKL Enerji A.Ş.',
    company_tax_no: '1111111111',
    status: 'failed',
    final_score: null,
    risk_level: null,
    decision: null,
    created_at: '2024-11-30T14:00:00Z',
    completed_at: null,
    duration_seconds: null,
  },
];

// ==================== Report Detail ====================

export const MOCK_REPORT_DETAIL: ReportDetail = {
  ...MOCK_REPORTS[0],
  agent_results: {
    tsg: {
      status: 'completed',
      duration_seconds: 180,
      data: MOCK_TSG_DATA,
    },
    ihale: {
      status: 'completed',
      duration_seconds: 45,
      data: MOCK_IHALE_DATA,
    },
    news: {
      status: 'completed',
      duration_seconds: 120,
      data: MOCK_NEWS_DATA,
    },
  },
  council_decision: MOCK_COUNCIL_DECISION,
};

// ==================== Delayed Response Helper ====================

export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
