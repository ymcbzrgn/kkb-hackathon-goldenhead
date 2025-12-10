/**
 * Backend agent_results formatini frontend AgentResults formatina donusturur
 *
 * Backend'den gelen format (wrapped):
 * {
 *   "tsg": { "status": "completed", "duration_seconds": 50, "data": {...} },
 *   "ihale": { "status": "completed", "duration_seconds": 1, "data": {...} },
 *   "news": { "status": "completed", "duration_seconds": 2, "data": {...} }
 * }
 */
import type { AgentResults, TsgData, IhaleData, NewsData, AgentResult } from '@/types';

// Backend'den gelen wrapper format
interface WrappedAgentResult<T> {
  status?: string;
  duration_seconds?: number;
  data?: T;
  summary?: string;
  key_findings?: string[];
  warning_flags?: string[];
}

// Backend'den gelen raw TSG verisi (data icinde)
interface RawTsgData {
  firma_adi?: string;
  tsg_sonuc?: {
    toplam_ilan?: number;
    sicil_bilgisi?: { sicil_no?: string; sicil_mudurlugu?: string };
    gazete_bilgisi?: { tarih?: string };
    yapilandirilmis_veri?: {
      Sermaye?: number | null;
      Yoneticiler?: Array<{ ad?: string; gorev?: string }>;
      Firma_Unvani?: string;
      Kurulus_Tarihi?: string | null;
      Faaliyet_Konusu?: string | null;
    };
  };
}

// Backend'den gelen raw News verisi (data icinde)
interface RawNewsData {
  ozet?: {
    trend?: string;
    olumlu?: number;
    olumsuz?: number;
    toplam?: number;
    sentiment_score?: number;
  };
  haberler?: Array<{
    baslik?: string;
    kaynak?: string;
    tarih?: string;
    sentiment?: string;
    url?: string;
  }>;
  toplam_haber?: number;
}

// Backend'den gelen raw Ihale verisi (data icinde)
interface RawIhaleData {
  yasak_durumu?: boolean;
  yasakli_mi?: boolean; // K8s format
  aktif_yasak?: {
    sebep?: string;
    baslangic?: string;
    bitis?: string;
    kurum?: string;
  } | null;
  gecmis_yasaklar?: Array<{
    sebep?: string;
    baslangic?: string;
    bitis?: string;
    kurum?: string;
  }>;
  yasaklamalar?: Array<{
    sebep?: string;
    baslangic?: string;
    bitis?: string;
    kurum?: string;
  }>;
  toplam_karar?: number;
  eslesen_karar?: number;
}

// Backend'den gelen tam response
interface RawAgentResults {
  tsg?: WrappedAgentResult<RawTsgData> | null;
  ihale?: WrappedAgentResult<RawIhaleData> | null;
  news?: WrappedAgentResult<RawNewsData> | null;
}

/**
 * TSG verisini frontend formatina donustur
 */
function transformTsg(wrapped: WrappedAgentResult<RawTsgData> | null | undefined): AgentResult<TsgData> {
  if (!wrapped) {
    return { status: 'pending', duration_seconds: null, data: null };
  }

  // Wrapper'dan status ve duration_seconds al
  const status = (wrapped.status as 'pending' | 'running' | 'completed' | 'failed') || 'pending';
  const duration_seconds = wrapped.duration_seconds || null;

  // Data yoksa sadece status dondur
  const raw = wrapped.data;
  if (!raw) {
    return { status, duration_seconds, data: null };
  }

  const yapi = raw.tsg_sonuc?.yapilandirilmis_veri;

  const data: TsgData = {
    kurulus_tarihi: yapi?.Kurulus_Tarihi || '',
    sermaye: yapi?.Sermaye || 0,
    sermaye_para_birimi: 'TRY',
    adres: '',
    faaliyet_konusu: yapi?.Faaliyet_Konusu || '',
    ortaklar: [],
    yonetim_kurulu: (yapi?.Yoneticiler || []).map(y => ({
      ad: y.ad || '',
      gorev: y.gorev || ''
    })),
    sermaye_degisiklikleri: [],
    yonetici_degisiklikleri: []
  };

  return { status, duration_seconds, data };
}

/**
 * News verisini frontend formatina donustur
 */
function transformNews(wrapped: WrappedAgentResult<RawNewsData> | null | undefined): AgentResult<NewsData> {
  if (!wrapped) {
    return { status: 'pending', duration_seconds: null, data: null };
  }

  // Wrapper'dan status ve duration_seconds al
  const status = (wrapped.status as 'pending' | 'running' | 'completed' | 'failed') || 'pending';
  const duration_seconds = wrapped.duration_seconds || null;

  // Data yoksa sadece status dondur
  const raw = wrapped.data;
  if (!raw) {
    return { status, duration_seconds, data: null };
  }

  // Trend mapping: backend "pozitif/negatif/notr" -> frontend "yukari/asagi/stabil"
  const trendMap: Record<string, 'yukari' | 'asagi' | 'stabil'> = {
    'pozitif': 'yukari',
    'negatif': 'asagi',
    'notr': 'stabil',
    'yukari': 'yukari',
    'asagi': 'asagi',
    'stabil': 'stabil'
  };

  // Sentiment mapping: backend "olumlu/olumsuz" -> frontend "pozitif/negatif/notr"
  const sentimentMap: Record<string, 'pozitif' | 'negatif' | 'notr'> = {
    'olumlu': 'pozitif',
    'olumsuz': 'negatif',
    'pozitif': 'pozitif',
    'negatif': 'negatif',
    'notr': 'notr'
  };

  const toplam = raw.toplam_haber || raw.ozet?.toplam || 0;
  const olumlu = raw.ozet?.olumlu || 0;
  const olumsuz = raw.ozet?.olumsuz || 0;

  const data: NewsData = {
    toplam_haber: toplam,
    pozitif: olumlu,
    negatif: olumsuz,
    notr: Math.max(0, toplam - olumlu - olumsuz),
    sentiment_score: raw.ozet?.sentiment_score || 0,
    trend: trendMap[raw.ozet?.trend || ''] || 'stabil',
    onemli_haberler: (raw.haberler || []).map(h => ({
      baslik: h.baslik || '',
      kaynak: h.kaynak || '',
      tarih: h.tarih || '',
      sentiment: sentimentMap[h.sentiment || ''] || 'notr',
      url: h.url || ''
    }))
  };

  return { status, duration_seconds, data };
}

/**
 * Ihale verisini frontend formatina donustur
 */
function transformIhale(wrapped: WrappedAgentResult<RawIhaleData> | null | undefined): AgentResult<IhaleData> {
  if (!wrapped) {
    return { status: 'pending', duration_seconds: null, data: null };
  }

  // Wrapper'dan status ve duration_seconds al
  const status = (wrapped.status as 'pending' | 'running' | 'completed' | 'failed') || 'pending';
  const duration_seconds = wrapped.duration_seconds || null;

  // Data yoksa sadece status dondur
  const raw = wrapped.data;
  if (!raw) {
    return { status, duration_seconds, data: null };
  }

  // K8s ve local formatlarini destekle
  const yasak_durumu = raw.yasakli_mi ?? raw.yasak_durumu ?? false;
  const yasaklamalar = raw.yasaklamalar || raw.gecmis_yasaklar || [];

  const data: IhaleData = {
    yasak_durumu: yasak_durumu,
    aktif_yasak: raw.aktif_yasak ? {
      sebep: raw.aktif_yasak.sebep || '',
      baslangic: raw.aktif_yasak.baslangic || '',
      bitis: raw.aktif_yasak.bitis || '',
      kurum: raw.aktif_yasak.kurum || ''
    } : null,
    gecmis_yasaklar: yasaklamalar.map(y => ({
      sebep: y.sebep || '',
      baslangic: y.baslangic || '',
      bitis: y.bitis || '',
      kurum: y.kurum || ''
    }))
  };

  return { status, duration_seconds, data };
}

/**
 * Ana transform fonksiyonu - Backend agent_results'i frontend formatina donusturur
 */
export function transformAgentResults(raw: RawAgentResults | null | undefined): AgentResults {
  return {
    tsg: transformTsg(raw?.tsg),
    ihale: transformIhale(raw?.ihale),
    news: transformNews(raw?.news)
  };
}
