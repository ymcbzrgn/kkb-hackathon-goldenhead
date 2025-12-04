/**
 * useWebSocket Hook
 * WebSocket bağlantı ve event handling
 */

import { useEffect, useRef, useCallback } from 'react';
import { connectWebSocket, type WebSocketConnection } from '@/services/websocket';
import { useReportStore } from '@/stores/reportStore';
import { useAgentStore } from '@/stores/agentStore';
import { useCouncilStore } from '@/stores/councilStore';
import type { WebSocketEvent, AgentType } from '@/types';

interface UseWebSocketOptions {
  reportId: string;
  companyName: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

export function useWebSocket({ 
  reportId, 
  companyName, 
  onComplete, 
  onError,
  enabled = true,
}: UseWebSocketOptions) {
  const connectionRef = useRef<WebSocketConnection | null>(null);

  // Store actions
  const { 
    setWsConnectionState, 
    setWsError, 
    setLivePhase,
    endLiveSession 
  } = useReportStore();

  const { 
    startAgent, 
    updateProgress, 
    completeAgent, 
    failAgent,
    reset: resetAgents 
  } = useAgentStore();

  const {
    startCouncil,
    changePhase,
    changeSpeaker,
    appendSpeech,
    completeSpeech,
    reviseScore,
    setFinalDecision,
    reset: resetCouncil,
  } = useCouncilStore();

  // Event handler
  const handleEvent = useCallback((event: WebSocketEvent) => {
    switch (event.type) {
      // Job events
      case 'job_started':
        setLivePhase('agents');
        break;

      case 'job_completed':
        setLivePhase('completed');
        endLiveSession();
        onComplete?.();
        break;

      case 'job_failed':
        setLivePhase('failed');
        setWsError(event.payload.error_message);
        endLiveSession();
        onError?.(event.payload.error_message);
        break;

      // Agent events
      case 'agent_started':
        startAgent(event.payload.agent_id as AgentType, event.payload.agent_description);
        break;

      case 'agent_progress':
        updateProgress(
          event.payload.agent_id as AgentType,
          event.payload.progress,
          event.payload.message
        );
        break;

      case 'agent_completed':
        completeAgent(
          event.payload.agent_id as AgentType,
          event.payload.duration_seconds,
          event.payload.summary
        );
        break;

      case 'agent_failed':
        failAgent(
          event.payload.agent_id as AgentType,
          event.payload.error_code,
          event.payload.error_message
        );
        break;

      // Council events
      case 'council_started':
        setLivePhase('council');
        startCouncil(event.payload.members, event.payload.estimated_duration_seconds);
        break;

      case 'council_phase_changed':
        changePhase(
          event.payload.phase,
          event.payload.phase_number,
          event.payload.total_phases,
          event.payload.phase_title
        );
        break;

      case 'council_speaker_changed':
        changeSpeaker({
          id: event.payload.speaker_id,
          name: event.payload.speaker_name,
          role: event.payload.speaker_role,
          emoji: event.payload.speaker_emoji,
        });
        break;

      case 'council_speech':
        appendSpeech(event.payload.chunk);
        if (event.payload.is_complete) {
          completeSpeech(event.payload.risk_score);
        }
        break;

      case 'council_score_revision':
        reviseScore(
          event.payload.speaker_id,
          event.payload.old_score,
          event.payload.new_score
        );
        break;

      case 'council_decision':
        setFinalDecision({
          final_score: event.payload.final_score,
          risk_level: event.payload.risk_level,
          decision: event.payload.decision,
          consensus: event.payload.consensus,
          conditions: event.payload.conditions,
          dissent_note: event.payload.dissent_note,
        });
        break;
    }
  }, [
    setLivePhase,
    endLiveSession,
    setWsError,
    startAgent,
    updateProgress,
    completeAgent,
    failAgent,
    startCouncil,
    changePhase,
    changeSpeaker,
    appendSpeech,
    completeSpeech,
    reviseScore,
    setFinalDecision,
    onComplete,
    onError,
  ]);

  // Connect
  const connect = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.close();
    }

    // Reset stores
    resetAgents();
    resetCouncil();

    // Connect
    connectionRef.current = connectWebSocket(reportId, companyName, {
      onEvent: handleEvent,
      onOpen: () => {
        setWsConnectionState('connected');
        setWsError(null);
      },
      onClose: () => {
        setWsConnectionState('disconnected');
      },
      onError: (error) => {
        setWsConnectionState('error');
        setWsError(error);
        onError?.(error);
      },
    });
  }, [
    reportId,
    companyName,
    handleEvent,
    resetAgents,
    resetCouncil,
    setWsConnectionState,
    setWsError,
    onError,
  ]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.close();
      connectionRef.current = null;
    }
  }, []);

  // Auto-connect on mount when enabled
  useEffect(() => {
    if (enabled && companyName) {
      connect();
    }
    return () => disconnect();
  }, [connect, disconnect, enabled, companyName]);

  return {
    connect,
    disconnect,
    isConnected: connectionRef.current?.isConnected() ?? false,
  };
}
