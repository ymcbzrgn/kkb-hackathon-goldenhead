/**
 * AgentProgress Component
 * 3 agent container - tüm agentların progress'ini gösterir
 */

import { motion } from 'framer-motion';
import { AgentStatusCard } from './AgentStatusCard';
import { staggerContainer, fadeInUp } from '@/utils/animations';
import type { AgentProgress as AgentProgressType } from '@/types';

interface AgentProgressProps {
  agents: AgentProgressType[];
}

export function AgentProgress({ agents }: AgentProgressProps) {
  // Default agent order
  const orderedAgents = ['tsg_agent', 'ihale_agent', 'news_agent'];
  
  // Sort agents by predefined order
  const sortedAgents = [...agents].sort((a, b) => {
    return orderedAgents.indexOf(a.agent_id) - orderedAgents.indexOf(b.agent_id);
  });

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      className="space-y-4"
    >
      <motion.h3
        variants={fadeInUp}
        className="text-lg font-semibold text-gray-800 mb-4"
      >
        Veri Toplama Aşaması
      </motion.h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {sortedAgents.map((agent) => (
          <motion.div key={agent.agent_id} variants={fadeInUp}>
            <AgentStatusCard
              agentType={agent.agent_id}
              status={agent.status}
              progress={agent.progress}
              message={agent.message}
              duration={agent.duration_seconds || undefined}
            />
          </motion.div>
        ))}
      </div>

      {/* All completed indicator */}
      {agents.every((a) => a.status === 'completed') && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center py-4"
        >
          <p className="text-green-600 font-medium">
            ✓ Tüm veriler toplandı. Komite değerlendirmesine geçiliyor...
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
