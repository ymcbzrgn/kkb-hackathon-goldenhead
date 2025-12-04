/**
 * LiveIndicator Component
 * 🔴 CANLI badge with pulsing animation
 */

import { motion } from 'framer-motion';
import { Radio } from 'lucide-react';

interface LiveIndicatorProps {
  isLive?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const sizeConfig = {
  sm: { text: 'text-xs', padding: 'px-2 py-0.5', dot: 'w-1.5 h-1.5', icon: 'w-3 h-3' },
  md: { text: 'text-sm', padding: 'px-3 py-1', dot: 'w-2 h-2', icon: 'w-4 h-4' },
  lg: { text: 'text-base', padding: 'px-4 py-1.5', dot: 'w-2.5 h-2.5', icon: 'w-5 h-5' },
};

export function LiveIndicator({ isLive = true, size = 'md' }: LiveIndicatorProps) {
  const config = sizeConfig[size];

  if (!isLive) {
    return (
      <div className={`inline-flex items-center gap-1.5 ${config.padding} bg-gray-100 text-gray-500 rounded-full ${config.text} font-medium`}>
        <div className={`${config.dot} bg-gray-400 rounded-full`} />
        <span>Çevrimdışı</span>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center gap-1.5 ${config.padding} bg-red-500 text-white rounded-full ${config.text} font-bold shadow-lg`}
    >
      {/* Pulsing dot */}
      <span className="relative flex">
        <motion.span
          animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className={`absolute inline-flex ${config.dot} rounded-full bg-white opacity-75`}
        />
        <span className={`relative inline-flex ${config.dot} rounded-full bg-white`} />
      </span>
      
      <Radio className={config.icon} />
      <span>CANLI</span>
    </motion.div>
  );
}
