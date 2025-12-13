/**
 * Status Badge
 * Rapor durumunu gösteren badge (pending, processing, completed, failed)
 */

import { motion } from 'framer-motion';
import { Clock, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { ReportStatus } from '@/types';

interface StatusBadgeProps {
  status: ReportStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
  animated?: boolean;
}

const statusConfig: Record<ReportStatus, {
  label: string;
  icon: typeof Clock;
  bgColor: string;
  textColor: string;
  iconColor: string;
  borderColor: string;
}> = {
  pending: {
    label: 'Bekliyor',
    icon: Clock,
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-600',
    iconColor: 'text-gray-500',
    borderColor: 'border-gray-200',
  },
  processing: {
    label: 'İşleniyor',
    icon: Loader2,
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    iconColor: 'text-blue-500',
    borderColor: 'border-blue-200',
  },
  completed: {
    label: 'Tamamlandı',
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    iconColor: 'text-green-500',
    borderColor: 'border-green-200',
  },
  failed: {
    label: 'Hata',
    icon: XCircle,
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    iconColor: 'text-red-500',
    borderColor: 'border-red-200',
  },
  cancelled: {
    label: 'İptal Edildi',
    icon: XCircle,
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-600',
    iconColor: 'text-gray-400',
    borderColor: 'border-gray-200',
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

export function StatusBadge({
  status,
  size = 'md',
  showIcon = true,
  showLabel = true,
  animated = true,
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  return (
    <motion.span
      initial={animated ? { scale: 0.9, opacity: 0 } : false}
      animate={animated ? { scale: 1, opacity: 1 } : false}
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
        <Icon
          className={cn(
            sizes.icon,
            config.iconColor,
            status === 'processing' && 'animate-spin'
          )}
        />
      )}
      {showLabel && <span>{config.label}</span>}
    </motion.span>
  );
}
