/**
 * RiskGauge Component
 * Circular risk score gauge
 */

import { motion } from 'framer-motion';
import type { RiskLevel } from '@/types';

interface RiskGaugeProps {
  score: number;
  riskLevel: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
}

const riskColors: Record<RiskLevel, { primary: string; secondary: string; text: string }> = {
  dusuk: {
    primary: '#22c55e',
    secondary: '#dcfce7',
    text: 'text-green-600',
  },
  orta_dusuk: {
    primary: '#84cc16',
    secondary: '#ecfccb',
    text: 'text-lime-600',
  },
  orta: {
    primary: '#f59e0b',
    secondary: '#fef3c7',
    text: 'text-amber-600',
  },
  orta_yuksek: {
    primary: '#f97316',
    secondary: '#ffedd5',
    text: 'text-orange-600',
  },
  yuksek: {
    primary: '#ef4444',
    secondary: '#fee2e2',
    text: 'text-red-600',
  },
};

const riskLabels: Record<RiskLevel, string> = {
  dusuk: 'Düşük Risk',
  orta_dusuk: 'Orta-Düşük Risk',
  orta: 'Orta Risk',
  orta_yuksek: 'Orta-Yüksek Risk',
  yuksek: 'Yüksek Risk',
};

const sizeConfig = {
  sm: { width: 120, stroke: 8, fontSize: 'text-xl' },
  md: { width: 160, stroke: 10, fontSize: 'text-3xl' },
  lg: { width: 200, stroke: 12, fontSize: 'text-4xl' },
};

export function RiskGauge({ score, riskLevel, size = 'md' }: RiskGaugeProps) {
  const config = sizeConfig[size];
  const colors = riskColors[riskLevel];
  
  const radius = (config.width - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const dashOffset = circumference - progress;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: config.width, height: config.width }}>
        {/* Background Circle */}
        <svg
          className="transform -rotate-90"
          width={config.width}
          height={config.width}
        >
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke={colors.secondary}
            strokeWidth={config.stroke}
          />
          <motion.circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke={colors.primary}
            strokeWidth={config.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          />
        </svg>

        {/* Score Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className={`font-bold ${config.fontSize} ${colors.text}`}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            {score}
          </motion.span>
          <span className="text-xs text-gray-400 uppercase tracking-wider">puan</span>
        </div>
      </div>

      {/* Risk Level Label */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className={`mt-3 px-4 py-1.5 rounded-full text-sm font-semibold ${colors.text}`}
        style={{ backgroundColor: colors.secondary }}
      >
        {riskLabels[riskLevel]}
      </motion.div>
    </div>
  );
}
