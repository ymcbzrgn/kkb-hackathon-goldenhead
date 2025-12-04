/**
 * Timer Component
 * Geçen süre sayacı
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { formatTimer } from '@/utils/formatters';

interface TimerProps {
  startTime?: Date;
  isRunning?: boolean;
  className?: string;
}

export function Timer({ startTime, isRunning = true, className = '' }: TimerProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isRunning) return;

    const start = startTime?.getTime() || Date.now();
    
    const interval = setInterval(() => {
      const now = Date.now();
      setElapsed(Math.floor((now - start) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, isRunning]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full ${className}`}
    >
      <Clock className="w-4 h-4 text-gray-500" />
      <span className="font-mono text-sm font-medium text-gray-700">
        {formatTimer(elapsed)}
      </span>
    </motion.div>
  );
}
