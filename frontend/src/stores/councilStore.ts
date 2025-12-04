/**
 * Council Store
 * Council (Komite) state yönetimi - Streaming speech, skorlar
 */

import { create } from 'zustand';
import type {
  CouncilPhase,
  CouncilMemberId,
  CouncilMember,
  TranscriptEntry,
  RiskLevel,
  Decision,
} from '@/types';

// ==================== Types ====================

interface CouncilState {
  // Session
  isActive: boolean;
  startedAt: string | null;
  estimatedDuration: number;

  // Phase
  currentPhase: CouncilPhase;
  phaseNumber: number;
  totalPhases: number;
  phaseTitle: string;

  // Speaker
  currentSpeaker: CouncilMember | null;
  members: CouncilMember[];

  // Streaming speech
  currentSpeech: string;
  isTyping: boolean;

  // Scores
  scores: Partial<Record<CouncilMemberId, number>>;
  initialScores: Partial<Record<CouncilMemberId, number>>;

  // Transcript
  transcript: TranscriptEntry[];

  // Final decision
  finalDecision: {
    final_score: number;
    risk_level: RiskLevel;
    decision: Decision;
    consensus: number;
    conditions: string[];
    dissent_note: string | null;
  } | null;

  // Actions
  startCouncil: (members: CouncilMember[], estimatedDuration: number) => void;
  changePhase: (phase: CouncilPhase, phaseNumber: number, totalPhases: number, phaseTitle: string) => void;
  changeSpeaker: (speaker: CouncilMember) => void;
  appendSpeech: (chunk: string) => void;
  completeSpeech: (riskScore?: number) => void;
  updateScore: (memberId: CouncilMemberId, score: number, isInitial?: boolean) => void;
  reviseScore: (memberId: CouncilMemberId, oldScore: number, newScore: number) => void;
  setFinalDecision: (decision: CouncilState['finalDecision']) => void;
  reset: () => void;
}

// ==================== Initial State ====================

const initialState = {
  isActive: false,
  startedAt: null,
  estimatedDuration: 0,
  currentPhase: 'opening' as CouncilPhase,
  phaseNumber: 0,
  totalPhases: 8,
  phaseTitle: '',
  currentSpeaker: null,
  members: [],
  currentSpeech: '',
  isTyping: false,
  scores: {},
  initialScores: {},
  transcript: [],
  finalDecision: null,
};

// ==================== Store ====================

export const useCouncilStore = create<CouncilState>((set, get) => ({
  ...initialState,

  startCouncil: (members, estimatedDuration) =>
    set({
      isActive: true,
      startedAt: new Date().toISOString(),
      estimatedDuration,
      members,
      scores: {},
      initialScores: {},
      transcript: [],
      finalDecision: null,
    }),

  changePhase: (phase, phaseNumber, totalPhases, phaseTitle) =>
    set({
      currentPhase: phase,
      phaseNumber,
      totalPhases,
      phaseTitle,
    }),

  changeSpeaker: (speaker) =>
    set({
      currentSpeaker: speaker,
      currentSpeech: '',
      isTyping: true,
    }),

  appendSpeech: (chunk) =>
    set((state) => ({
      currentSpeech: state.currentSpeech + chunk,
    })),

  completeSpeech: (riskScore) => {
    const state = get();
    
    // Mevcut konuşmayı transcript'e ekle
    if (state.currentSpeaker && state.currentSpeech) {
      const entry: TranscriptEntry = {
        timestamp: new Date().toISOString(),
        phase: state.currentPhase,
        speaker_id: state.currentSpeaker.id,
        speaker_name: state.currentSpeaker.name,
        speaker_emoji: state.currentSpeaker.emoji,
        content: state.currentSpeech,
        risk_score: riskScore ?? null,
      };

      set((s) => ({
        transcript: [...s.transcript, entry],
        isTyping: false,
        // İlk skor ise kaydet
        ...(riskScore !== undefined && {
          scores: { ...s.scores, [state.currentSpeaker!.id]: riskScore },
          initialScores: { ...s.initialScores, [state.currentSpeaker!.id]: riskScore },
        }),
      }));
    } else {
      set({ isTyping: false });
    }
  },

  updateScore: (memberId, score, isInitial = false) =>
    set((state) => ({
      scores: { ...state.scores, [memberId]: score },
      ...(isInitial && {
        initialScores: { ...state.initialScores, [memberId]: score },
      }),
    })),

  reviseScore: (memberId, _oldScore, newScore) =>
    set((state) => ({
      scores: { ...state.scores, [memberId]: newScore },
    })),

  setFinalDecision: (decision) =>
    set({
      finalDecision: decision,
      isActive: false,
    }),

  reset: () => set(initialState),
}));
