/**
 * Agent Store
 * Agent progress state yönetimi (Live session için)
 */

import { create } from 'zustand';
import type { AgentType, AgentStatus, AgentProgress } from '@/types';

// ==================== Initial State ====================

const createInitialAgentProgress = (agentId: AgentType): AgentProgress => ({
  agent_id: agentId,
  agent_name: getAgentName(agentId),
  status: 'pending',
  progress: 0,
  message: '',
  startedAt: null,
  completedAt: null,
  duration_seconds: null,
});

function getAgentName(agentId: AgentType): string {
  const names: Record<AgentType, string> = {
    tsg_agent: 'TSG Agent',
    ihale_agent: 'İhale Agent',
    news_agent: 'News Agent',
  };
  return names[agentId];
}

// ==================== Types ====================

interface AgentState {
  agents: Record<AgentType, AgentProgress>;
  
  // Computed
  allCompleted: boolean;
  anyFailed: boolean;
  overallProgress: number;

  // Actions
  startAgent: (agentId: AgentType, description: string) => void;
  updateProgress: (agentId: AgentType, progress: number, message: string) => void;
  completeAgent: (agentId: AgentType, duration: number, summary?: { records_found?: number; key_findings?: string[] }) => void;
  failAgent: (agentId: AgentType, errorCode: string, errorMessage: string) => void;
  reset: () => void;
}

// ==================== Store ====================

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: {
    tsg_agent: createInitialAgentProgress('tsg_agent'),
    ihale_agent: createInitialAgentProgress('ihale_agent'),
    news_agent: createInitialAgentProgress('news_agent'),
  },

  // Computed
  get allCompleted() {
    const agents = get().agents;
    return Object.values(agents).every(
      (a) => a.status === 'completed' || a.status === 'failed'
    );
  },

  get anyFailed() {
    const agents = get().agents;
    return Object.values(agents).some((a) => a.status === 'failed');
  },

  get overallProgress() {
    const agents = get().agents;
    const total = Object.values(agents).reduce((sum, a) => sum + a.progress, 0);
    return Math.round(total / 3);
  },

  // Actions
  startAgent: (agentId, description) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [agentId]: {
          ...state.agents[agentId],
          status: 'running' as AgentStatus,
          message: description,
          startedAt: new Date().toISOString(),
        },
      },
    })),

  updateProgress: (agentId, progress, message) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [agentId]: {
          ...state.agents[agentId],
          progress,
          message,
        },
      },
    })),

  completeAgent: (agentId, duration, summary) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [agentId]: {
          ...state.agents[agentId],
          status: 'completed' as AgentStatus,
          progress: 100,
          completedAt: new Date().toISOString(),
          duration_seconds: duration,
          summary,
        },
      },
    })),

  failAgent: (agentId, errorCode, errorMessage) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [agentId]: {
          ...state.agents[agentId],
          status: 'failed' as AgentStatus,
          error: { code: errorCode, message: errorMessage },
        },
      },
    })),

  reset: () =>
    set({
      agents: {
        tsg_agent: createInitialAgentProgress('tsg_agent'),
        ihale_agent: createInitialAgentProgress('ihale_agent'),
        news_agent: createInitialAgentProgress('news_agent'),
      },
    }),
}));
