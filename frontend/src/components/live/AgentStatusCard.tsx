/**
 * AgentStatusCard Component
 * Tek agent durumu kartı
 */

import { motion } from 'framer-motion';
import { FileText, Gavel, Newspaper, CheckCircle, XCircle, Loader2, Clock } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { AgentProgressBar } from './AgentProgressBar';
import type { AgentType, AgentStatus } from '@/types';

interface AgentStatusCardProps {
  agentType: AgentType;
  status: AgentStatus;
  progress: number;
  message?: string;
  duration?: number;
}

const agentConfig: Record<AgentType, { 
  icon: typeof FileText; 
  name: string; 
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  tsg_agent: {
    icon: FileText,
    name: 'TSG Agent',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  ihale_agent: {
    icon: Gavel,
    name: 'İhale Agent',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  news_agent: {
    icon: Newspaper,
    name: 'News Agent',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
};

const statusConfig: Record<AgentStatus, { icon: typeof Clock; label: string; color: string }> = {
  pending: { icon: Clock, label: 'Bekliyor', color: 'text-gray-500' },
  running: { icon: Loader2, label: 'Çalışıyor', color: 'text-blue-500' },
  completed: { icon: CheckCircle, label: 'Tamamlandı', color: 'text-green-500' },
  failed: { icon: XCircle, label: 'Başarısız', color: 'text-red-500' },
};

export function AgentStatusCard({
  agentType,
  status,
  progress,
  message,
  duration,
}: AgentStatusCardProps) {
  const agent = agentConfig[agentType];
  const statusInfo = statusConfig[status];
  const AgentIcon = agent.icon;
  const StatusIcon = statusInfo.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <Card className={`p-4 border-2 ${agent.borderColor} ${agent.bgColor}`}>
        <div className="flex items-start gap-4">
          {/* Agent Icon */}
          <div className={`p-3 rounded-xl ${agent.bgColor} border ${agent.borderColor}`}>
            <AgentIcon className={`w-6 h-6 ${agent.color}`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <h4 className={`font-semibold ${agent.color}`}>{agent.name}</h4>
              <div className={`flex items-center gap-1.5 ${statusInfo.color}`}>
                <StatusIcon className={`w-4 h-4 ${status === 'running' ? 'animate-spin' : ''}`} />
                <span className="text-sm font-medium">{statusInfo.label}</span>
              </div>
            </div>

            {/* Progress Bar */}
            <AgentProgressBar progress={progress} status={status} />

            {/* Message & Duration */}
            <div className="flex items-center justify-between mt-2">
              <p className="text-xs text-gray-500 truncate flex-1">
                {message || (status === 'pending' ? 'Başlamak için bekliyor...' : '')}
              </p>
              {duration !== undefined && status === 'completed' && (
                <span className="text-xs text-gray-400 ml-2">
                  {duration.toFixed(1)}s
                </span>
              )}
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
