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

interface ApiAgentProgress {
  status: string;
  progress: number;
  message: string;
  updated_at: string;
}

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
  initializeFromApi: (agentProgresses: Record<string, ApiAgentProgress> | null | undefined) => void;
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

  initializeFromApi: (agentProgresses) => {
    if (!agentProgresses) return;

    set((state) => {
      const newAgents = { ...state.agents };

      // Her agent için API'den gelen progress'i uygula
      const agentIds: AgentType[] = ['tsg_agent', 'ihale_agent', 'news_agent'];

      for (const agentId of agentIds) {
        const apiProgress = agentProgresses[agentId];
        if (apiProgress) {
          // API status'unu AgentStatus'a map et
          let status: AgentStatus = 'pending';
          if (apiProgress.status === 'running') {
            status = apiProgress.progress >= 100 ? 'completed' : 'running';
          } else if (apiProgress.status === 'completed') {
            status = 'completed';
          } else if (apiProgress.status === 'failed') {
            status = 'failed';
          }

          newAgents[agentId] = {
            ...newAgents[agentId],
            status,
            progress: apiProgress.progress,
            message: apiProgress.message,
          };
        }
      }

      return { agents: newAgents };
    });
  },

  reset: () =>
    set({
      agents: {
        tsg_agent: createInitialAgentProgress('tsg_agent'),
        ihale_agent: createInitialAgentProgress('ihale_agent'),
        news_agent: createInitialAgentProgress('news_agent'),
      },
    }),
}));
