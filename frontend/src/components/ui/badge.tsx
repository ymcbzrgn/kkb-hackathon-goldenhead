import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-gray-100 text-gray-800',
        primary: 'bg-kkb-100 text-kkb-900',
        secondary: 'bg-accent-100 text-accent-700',
        success: 'bg-decision-approved/10 text-decision-approved',
        warning: 'bg-decision-conditional/10 text-decision-conditional',
        danger: 'bg-decision-rejected/10 text-decision-rejected',
        // Risk seviyeleri
        'risk-low': 'bg-risk-low/10 text-risk-low',
        'risk-medium': 'bg-risk-medium/10 text-risk-medium',
        'risk-high': 'bg-risk-high/10 text-risk-high',
        'risk-critical': 'bg-risk-critical/10 text-risk-critical',
        // Karar durumları
        approved: 'bg-decision-approved/10 text-decision-approved border border-decision-approved/20',
        conditional: 'bg-decision-conditional/10 text-decision-conditional border border-decision-conditional/20',
        rejected: 'bg-decision-rejected/10 text-decision-rejected border border-decision-rejected/20',
        // Status
        pending: 'bg-amber-100 text-amber-800',
        processing: 'bg-blue-100 text-blue-800 animate-pulse',
        completed: 'bg-green-100 text-green-800',
        error: 'bg-red-100 text-red-800',
      },
      size: {
        sm: 'px-2 py-0.5 text-[10px]',
        md: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, size, dot, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant, size }), className)}
        {...props}
      >
        {dot && (
          <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
        )}
        {children}
      </div>
    );
  }
);
Badge.displayName = 'Badge';

export { Badge, badgeVariants };
