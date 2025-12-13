/**
 * Report Types
 * API.md'deki tanımlardan alınmıştır
 */

import type { 
  ReportStatus, 
  RiskLevel, 
  Decision 
} from './api';
import type { AgentResults } from './agent';
import type { CouncilDecision } from './council';

// ==================== Report List Item ====================

/**
 * GET /api/reports endpoint'inden dönen liste item'ı
 */
export interface ReportListItem {
  id: string;
  company_name: string;
  company_tax_no: string | null;
  status: ReportStatus;
  final_score: number | null;
  risk_level: RiskLevel | null;
  decision: Decision | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

// ==================== Report Detail ====================

/**
 * Agent progress bilgisi (DB'den gelen)
 */
export interface AgentProgressInfo {
  status: string;
  progress: number;
  message: string;
  updated_at: string;
}

/**
 * GET /api/reports/:id endpoint'inden dönen detaylı rapor
 */
export interface ReportDetail extends ReportListItem {
  agent_results: AgentResults;
  council_decision: CouncilDecision | null;
  // Agent progress'leri (canlı ilerleme takibi için)
  agent_progresses?: {
    tsg_agent?: AgentProgressInfo;
    ihale_agent?: AgentProgressInfo;
    news_agent?: AgentProgressInfo;
  } | null;
}

// ==================== Frontend State ====================

/**
 * Frontend'de kullanılan rapor durumu
 * WebSocket eventleri ile güncellenir
 */
export interface ReportState {
  report: ReportDetail | null;
  isLoading: boolean;
  error: string | null;
  
  // Live session state
  isLive: boolean;
  elapsedSeconds: number;
  currentPhase: 'agents' | 'council' | 'completed' | 'failed';
}
