/**
 * Agent Types
 * API.md'deki tanımlardan alınmıştır
 */

import type { AgentStatus, AgentType } from './api';

// ==================== Agent Result Types ====================

export interface AgentResult<T> {
  status: AgentStatus;
  duration_seconds: number | null;
  data: T | null;
}

export interface AgentResults {
  tsg: AgentResult<TsgData>;
  ihale: AgentResult<IhaleData>;
  news: AgentResult<NewsData>;
}

// ==================== TSG Agent Data ====================

export interface TsgData {
  kurulus_tarihi: string;
  sermaye: number;
  sermaye_para_birimi: string;
  adres: string;
  faaliyet_konusu: string;
  ortaklar: Ortak[];
  yonetim_kurulu: YonetimKuruluUyesi[];
  sermaye_degisiklikleri: SermayeDegisikligi[];
  yonetici_degisiklikleri: YoneticiDegisikligi[];
}

export interface Ortak {
  ad: string;
  pay_orani: number;
}

export interface YonetimKuruluUyesi {
  ad: string;
  gorev: string;
}

export interface SermayeDegisikligi {
  tarih: string;
  eski: number;
  yeni: number;
}

export interface YoneticiDegisikligi {
  tarih: string;
  eski: string;
  yeni: string;
  gorev: string;
}

// ==================== İhale Agent Data ====================

export interface IhaleData {
  yasak_durumu: boolean;
  aktif_yasak: YasakBilgisi | null;
  gecmis_yasaklar: YasakBilgisi[];
}

export interface YasakBilgisi {
  sebep: string;
  baslangic: string;
  bitis: string;
  kurum: string;
}

// ==================== News Agent Data ====================

export interface NewsData {
  toplam_haber: number;
  pozitif: number;
  negatif: number;
  notr: number;
  sentiment_score: number;
  trend: 'yukari' | 'asagi' | 'stabil';
  onemli_haberler: HaberItem[];
}

export interface HaberItem {
  baslik: string;
  kaynak: string;
  tarih: string;
  sentiment: 'pozitif' | 'negatif' | 'notr';
  url: string;
}

// ==================== Agent Progress State ====================

/**
 * Frontend'de agent progress takibi için
 */
export interface AgentProgress {
  agent_id: AgentType;
  agent_name: string;
  status: AgentStatus;
  progress: number; // 0-100
  message: string;
  startedAt: string | null;
  completedAt: string | null;
  duration_seconds: number | null;
  summary?: {
    records_found?: number;
    key_findings?: string[];
  };
  error?: {
    code: string;
    message: string;
  };
}

export interface AgentsState {
  agents: Record<AgentType, AgentProgress>;
  allCompleted: boolean;
  anyFailed: boolean;
}
