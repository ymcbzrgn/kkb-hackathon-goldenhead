/**
 * Council (Komite) Types
 * API.md'deki tanımlardan alınmıştır
 */

import type { RiskLevel, Decision } from './api';

// ==================== Council Enums ====================

export type CouncilPhase = 'opening' | 'presentation' | 'discussion' | 'decision';

export type CouncilMemberId = 
  | 'risk_analyst' 
  | 'business_analyst' 
  | 'legal_expert' 
  | 'media_analyst' 
  | 'sector_expert' 
  | 'moderator';

// ==================== Council Member ====================

export interface CouncilMember {
  id: CouncilMemberId;
  name: string;
  role: string;
  emoji: string;
}

// ==================== Council Scores ====================

export interface CouncilScores {
  risk_analyst: number;
  business_analyst: number;
  legal_expert: number;
  media_analyst: number;
  sector_expert: number;
}

// ==================== Transcript Entry ====================

export interface TranscriptEntry {
  timestamp: string;
  phase: CouncilPhase;
  speaker_id: CouncilMemberId;
  speaker_name: string;
  speaker_emoji: string;
  content: string;
  risk_score: number | null;
}

// ==================== Council Decision ====================

/**
 * GET /api/reports/:id response'undaki council_decision objesi
 */
export interface CouncilDecision {
  final_score: number;
  risk_level: RiskLevel;
  decision: Decision;
  consensus: number; // 0-1 arası
  conditions: string[];
  dissent_note: string | null;
  scores: {
    initial: CouncilScores;
    final: CouncilScores;
  };
  duration_seconds: number;
  transcript: TranscriptEntry[];
}

// ==================== Council Live State ====================

/**
 * Frontend'de live council takibi için
 */
export interface CouncilState {
  isActive: boolean;
  currentPhase: CouncilPhase;
  phaseNumber: number;
  totalPhases: number;
  phaseTitle: string;
  
  // Mevcut konuşmacı
  currentSpeaker: CouncilMember | null;
  
  // Streaming konuşma
  currentSpeech: string;
  isTyping: boolean;
  
  // Skorlar
  scores: Record<CouncilMemberId, number>;
  initialScores: Record<CouncilMemberId, number>;
  
  // Transcript (tamamlanan konuşmalar)
  transcript: TranscriptEntry[];
  
  // Final karar
  finalDecision: {
    final_score: number;
    risk_level: RiskLevel;
    decision: Decision;
    consensus: number;
    conditions: string[];
    dissent_note: string | null;
  } | null;
  
  // Timing
  startedAt: string | null;
  estimatedDuration: number;
}

// ==================== Score Revision ====================

export interface ScoreRevision {
  speaker_id: CouncilMemberId;
  speaker_name: string;
  old_score: number;
  new_score: number;
  reason: string;
  timestamp: string;
}
