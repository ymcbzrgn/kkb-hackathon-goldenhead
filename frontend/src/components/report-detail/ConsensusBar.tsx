/**
 * ConsensusBar Component
 * Komite konsensüs yüzdesi bar
 */

import { motion } from 'framer-motion';
import { Users } from 'lucide-react';

interface ConsensusBarProps {
  consensus: number; // 0-1 arası
  className?: string;
}

function getConsensusInfo(consensus: number) {
  const percentage = Math.round(consensus * 100);
  
  if (percentage >= 90) {
    return { label: 'Tam Mutabakat', color: 'bg-green-500', textColor: 'text-green-600' };
  } else if (percentage >= 70) {
    return { label: 'Güçlü Mutabakat', color: 'bg-blue-500', textColor: 'text-blue-600' };
  } else if (percentage >= 50) {
    return { label: 'Çoğunluk Mutabakatı', color: 'bg-amber-500', textColor: 'text-amber-600' };
  } else {
    return { label: 'Düşük Mutabakat', color: 'bg-red-500', textColor: 'text-red-600' };
  }
}

export function ConsensusBar({ consensus, className = '' }: ConsensusBarProps) {
  const percentage = Math.round(consensus * 100);
  const info = getConsensusInfo(consensus);

  return (
    <div className={`${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Users className="w-4 h-4" />
          <span>Komite Mutabakatı</span>
        </div>
        <span className={`text-sm font-semibold ${info.textColor}`}>
          {info.label}
        </span>
      </div>

      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${info.color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
        />
      </div>

      <div className="flex justify-between mt-1.5">
        <span className="text-xs text-gray-400">0%</span>
        <motion.span
          className={`text-sm font-bold ${info.textColor}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          %{percentage}
        </motion.span>
        <span className="text-xs text-gray-400">100%</span>
      </div>
    </div>
  );
}
