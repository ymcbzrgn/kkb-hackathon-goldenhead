/**
 * Report Store
 * Aktif rapor ve live session state yönetimi
 */

import { create } from 'zustand';
import type { ReportDetail, WebSocketConnectionState } from '@/types';

// ==================== Types ====================

type LivePhase = 'idle' | 'agents' | 'council' | 'completed' | 'failed';

interface ReportState {
  // Aktif rapor
  currentReport: ReportDetail | null;
  
  // Live session
  isLive: boolean;
  livePhase: LivePhase;
  elapsedSeconds: number;
  estimatedDuration: number;
  
  // WebSocket
  wsConnectionState: WebSocketConnectionState;
  wsError: string | null;

  // Actions
  setCurrentReport: (report: ReportDetail | null) => void;
  
  // Live session actions
  startLiveSession: (reportId: string, companyName: string, estimatedDuration: number) => void;
  setLivePhase: (phase: LivePhase) => void;
  incrementElapsedTime: () => void;
  endLiveSession: () => void;
  
  // WebSocket actions
  setWsConnectionState: (state: WebSocketConnectionState) => void;
  setWsError: (error: string | null) => void;

  // Reset
  reset: () => void;
}

// ==================== Initial State ====================

const initialState = {
  currentReport: null,
  isLive: false,
  livePhase: 'idle' as LivePhase,
  elapsedSeconds: 0,
  estimatedDuration: 0,
  wsConnectionState: 'disconnected' as WebSocketConnectionState,
  wsError: null,
};

// ==================== Store ====================

export const useReportStore = create<ReportState>((set) => ({
  ...initialState,

  setCurrentReport: (report) => set({ currentReport: report }),

  startLiveSession: (reportId, companyName, estimatedDuration) =>
    set({
      isLive: true,
      livePhase: 'agents',
      elapsedSeconds: 0,
      estimatedDuration,
      wsConnectionState: 'connecting',
      wsError: null,
      currentReport: {
        id: reportId,
        company_name: companyName,
        company_tax_no: null,
        status: 'processing',
        final_score: null,
        risk_level: null,
        decision: null,
        created_at: new Date().toISOString(),
        completed_at: null,
        duration_seconds: null,
        agent_results: {
          tsg: { status: 'pending', duration_seconds: null, data: null },
          ihale: { status: 'pending', duration_seconds: null, data: null },
          news: { status: 'pending', duration_seconds: null, data: null },
        },
        council_decision: null,
      },
    }),

  setLivePhase: (phase) => set({ livePhase: phase }),

  incrementElapsedTime: () =>
    set((state) => ({ elapsedSeconds: state.elapsedSeconds + 1 })),

  endLiveSession: () =>
    set({
      isLive: false,
      wsConnectionState: 'disconnected',
    }),

  setWsConnectionState: (wsConnectionState) => set({ wsConnectionState }),

  setWsError: (wsError) => set({ wsError }),

  reset: () => set(initialState),
}));
