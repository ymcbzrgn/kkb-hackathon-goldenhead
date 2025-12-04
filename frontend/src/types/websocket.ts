/**
 * WebSocket Event Types
 * API.md'deki tanımlardan alınmıştır
 */

import type { RiskLevel, Decision, AgentType } from './api';
import type { CouncilMember, CouncilPhase, CouncilMemberId } from './council';

// ==================== Base Event ====================

export interface BaseEvent {
  type: string;
  timestamp: string;
}

// ==================== Job Events ====================

export interface JobStartedEvent extends BaseEvent {
  type: 'job_started';
  payload: {
    report_id: string;
    company_name: string;
    estimated_duration_seconds: number;
  };
}

export interface JobCompletedEvent extends BaseEvent {
  type: 'job_completed';
  payload: {
    report_id: string;
    duration_seconds: number;
    final_score: number;
    risk_level: RiskLevel;
    decision: Decision;
  };
}

export interface JobFailedEvent extends BaseEvent {
  type: 'job_failed';
  payload: {
    report_id: string;
    error_code: string;
    error_message: string;
  };
}

// ==================== Agent Events ====================

export interface AgentStartedEvent extends BaseEvent {
  type: 'agent_started';
  payload: {
    agent_id: AgentType;
    agent_name: string;
    agent_description: string;
  };
}

export interface AgentProgressEvent extends BaseEvent {
  type: 'agent_progress';
  payload: {
    agent_id: AgentType;
    progress: number; // 0-100
    message: string;
  };
}

export interface AgentCompletedEvent extends BaseEvent {
  type: 'agent_completed';
  payload: {
    agent_id: AgentType;
    duration_seconds: number;
    summary: {
      records_found?: number;
      key_findings?: string[];
    };
  };
}

export interface AgentFailedEvent extends BaseEvent {
  type: 'agent_failed';
  payload: {
    agent_id: AgentType;
    error_code: string;
    error_message: string;
    will_retry: boolean;
  };
}

// ==================== Council Events ====================

export interface CouncilStartedEvent extends BaseEvent {
  type: 'council_started';
  payload: {
    estimated_duration_seconds: number;
    members: CouncilMember[];
  };
}

export interface CouncilPhaseChangedEvent extends BaseEvent {
  type: 'council_phase_changed';
  payload: {
    phase: CouncilPhase;
    phase_number: number;
    total_phases: number;
    phase_title: string;
  };
}

export interface CouncilSpeakerChangedEvent extends BaseEvent {
  type: 'council_speaker_changed';
  payload: {
    speaker_id: CouncilMemberId;
    speaker_name: string;
    speaker_role: string;
    speaker_emoji: string;
  };
}

export interface CouncilSpeechEvent extends BaseEvent {
  type: 'council_speech';
  payload: {
    speaker_id: CouncilMemberId;
    chunk: string;
    is_complete: boolean;
    risk_score?: number; // sadece is_complete: true olduğunda gelir
  };
}

export interface CouncilScoreRevisionEvent extends BaseEvent {
  type: 'council_score_revision';
  payload: {
    speaker_id: CouncilMemberId;
    speaker_name: string;
    old_score: number;
    new_score: number;
    reason: string;
  };
}

export interface CouncilDecisionEvent extends BaseEvent {
  type: 'council_decision';
  payload: {
    final_score: number;
    risk_level: RiskLevel;
    decision: Decision;
    consensus: number;
    conditions: string[];
    dissent_note: string | null;
    final_scores: {
      risk_analyst: number;
      business_analyst: number;
      legal_expert: number;
      media_analyst: number;
      sector_expert: number;
    };
  };
}

// ==================== All WebSocket Events ====================

export type WebSocketEvent =
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

// ==================== Event Type Guard Helpers ====================

export function isJobEvent(event: WebSocketEvent): event is JobStartedEvent | JobCompletedEvent | JobFailedEvent {
  return event.type.startsWith('job_');
}

export function isAgentEvent(event: WebSocketEvent): event is AgentStartedEvent | AgentProgressEvent | AgentCompletedEvent | AgentFailedEvent {
  return event.type.startsWith('agent_');
}

export function isCouncilEvent(event: WebSocketEvent): event is CouncilStartedEvent | CouncilPhaseChangedEvent | CouncilSpeakerChangedEvent | CouncilSpeechEvent | CouncilScoreRevisionEvent | CouncilDecisionEvent {
  return event.type.startsWith('council_');
}

// ==================== WebSocket Connection State ====================

export type WebSocketConnectionState = 
  | 'connecting' 
  | 'connected' 
  | 'disconnected' 
  | 'error';

export interface WebSocketState {
  connectionState: WebSocketConnectionState;
  reportId: string | null;
  lastEventTimestamp: string | null;
  error: string | null;
}
