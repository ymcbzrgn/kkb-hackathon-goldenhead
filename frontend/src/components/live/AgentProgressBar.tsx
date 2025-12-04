/**
 * AgentProgressBar Component
 * Animated progress bar for agents
 */

import { motion } from 'framer-motion';

interface AgentProgressBarProps {
  progress: number; // 0-100
  status: 'pending' | 'running' | 'completed' | 'failed';
  color?: string;
}

const statusColors = {
  pending: 'bg-gray-300',
  running: 'bg-kkb-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

export function AgentProgressBar({ progress, status, color }: AgentProgressBarProps) {
  const barColor = color || statusColors[status];

  return (
    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
      <motion.div
        className={`h-full ${barColor} rounded-full`}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(progress, 100)}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  );
}
