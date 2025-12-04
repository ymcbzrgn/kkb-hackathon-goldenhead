import { cn } from '@/utils/cn';

interface ProgressProps {
  value: number; // 0-100
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'gradient';
  showValue?: boolean;
  animated?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

const variantClasses = {
  default: 'bg-kkb-600',
  success: 'bg-decision-approved',
  warning: 'bg-decision-conditional',
  danger: 'bg-decision-rejected',
  gradient: 'bg-gradient-to-r from-kkb-600 to-accent-500',
};

export function Progress({
  value,
  max = 100,
  size = 'md',
  variant = 'default',
  showValue = false,
  animated = true,
  className,
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'w-full overflow-hidden rounded-full bg-gray-200',
          sizeClasses[size]
        )}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            variantClasses[variant],
            animated && 'origin-left'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <span className="mt-1 block text-xs font-medium text-gray-600">
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  );
}

// Score bar - özellikle Council skorları için
interface ScoreBarProps {
  score: number;
  maxScore?: number;
  label?: string;
  showScore?: boolean;
  className?: string;
}

export function ScoreBar({
  score,
  maxScore = 100,
  label,
  showScore = true,
  className,
}: ScoreBarProps) {
  const percentage = (score / maxScore) * 100;
  
  // Skora göre renk
  const getColor = () => {
    if (percentage >= 70) return 'bg-decision-approved';
    if (percentage >= 40) return 'bg-decision-conditional';
    return 'bg-decision-rejected';
  };

  return (
    <div className={cn('w-full', className)}>
      {(label || showScore) && (
        <div className="flex items-center justify-between mb-1">
          {label && (
            <span className="text-sm font-medium text-gray-700">{label}</span>
          )}
          {showScore && (
            <span className="text-sm font-semibold text-kkb-900">
              {score}/{maxScore}
            </span>
          )}
        </div>
      )}
      <div className="w-full h-2 overflow-hidden bg-gray-200 rounded-full">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-700 ease-out',
            getColor()
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
