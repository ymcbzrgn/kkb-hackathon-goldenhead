/**
 * Risk Badge
 * Risk seviyesini gösteren badge (dusuk, orta_dusuk, orta, orta_yuksek, yuksek)
 */

import { motion } from 'framer-motion';
import { Shield, ShieldAlert, ShieldCheck, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { RiskLevel } from '@/types';

interface RiskBadgeProps {
  riskLevel: RiskLevel | null;
  score?: number | null;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
  showScore?: boolean;
}

const riskConfig = {
  dusuk: {
    label: 'Düşük Risk',
    shortLabel: 'Düşük',
    icon: ShieldCheck,
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    iconColor: 'text-green-500',
    borderColor: 'border-green-200',
    scoreColor: 'text-green-600',
  },
  orta_dusuk: {
    label: 'Orta-Düşük Risk',
    shortLabel: 'Orta-Düşük',
    icon: Shield,
    bgColor: 'bg-lime-50',
    textColor: 'text-lime-700',
    iconColor: 'text-lime-500',
    borderColor: 'border-lime-200',
    scoreColor: 'text-lime-600',
  },
  orta: {
    label: 'Orta Risk',
    shortLabel: 'Orta',
    icon: Shield,
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    iconColor: 'text-yellow-500',
    borderColor: 'border-yellow-200',
    scoreColor: 'text-yellow-600',
  },
  orta_yuksek: {
    label: 'Orta-Yüksek Risk',
    shortLabel: 'Orta-Yüksek',
    icon: AlertTriangle,
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-700',
    iconColor: 'text-orange-500',
    borderColor: 'border-orange-200',
    scoreColor: 'text-orange-600',
  },
  yuksek: {
    label: 'Yüksek Risk',
    shortLabel: 'Yüksek',
    icon: ShieldAlert,
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    iconColor: 'text-red-500',
    borderColor: 'border-red-200',
    scoreColor: 'text-red-600',
  },
};

const sizeConfig = {
  sm: {
    padding: 'px-2 py-0.5',
    text: 'text-xs',
    icon: 'w-3 h-3',
    gap: 'gap-1',
  },
  md: {
    padding: 'px-2.5 py-1',
    text: 'text-sm',
    icon: 'w-4 h-4',
    gap: 'gap-1.5',
  },
  lg: {
    padding: 'px-3 py-1.5',
    text: 'text-base',
    icon: 'w-5 h-5',
    gap: 'gap-2',
  },
};

export function RiskBadge({
  riskLevel,
  score,
  size = 'md',
  showIcon = true,
  showLabel = true,
  showScore = false,
}: RiskBadgeProps) {
  // Risk level yoksa gösterme
  if (!riskLevel) {
    return (
      <span className="text-gray-400 text-sm">-</span>
    );
  }

  const config = riskConfig[riskLevel];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        'inline-flex items-center font-medium rounded-full border',
        config.bgColor,
        config.textColor,
        config.borderColor,
        sizes.padding,
        sizes.text,
        sizes.gap
      )}
    >
      {showIcon && (
        <Icon className={cn(sizes.icon, config.iconColor)} />
      )}
      {showLabel && (
        <span>{size === 'sm' ? config.shortLabel : config.label}</span>
      )}
      {showScore && score !== null && score !== undefined && (
        <span className={cn('font-bold', config.scoreColor)}>
          {score}
        </span>
      )}
    </motion.span>
  );
}
