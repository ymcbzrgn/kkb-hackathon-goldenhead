/**
 * PhaseIndicator Component
 * Komite aşama göstergesi
 */

import { cn } from '@/utils/cn';

interface PhaseIndicatorProps {
  currentPhase: number;
  totalPhases: number;
  phaseTitle: string;
}

export function PhaseIndicator({ currentPhase, totalPhases, phaseTitle }: PhaseIndicatorProps) {
  return (
    <div className="flex items-center gap-4">
      {/* Phase dots */}
      <div className="flex items-center gap-1">
        {Array.from({ length: totalPhases }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'w-2 h-2 rounded-full transition-all duration-300',
              i + 1 === currentPhase 
                ? 'w-6 bg-kkb-600' 
                : i + 1 < currentPhase 
                  ? 'bg-kkb-400' 
                  : 'bg-gray-300'
            )}
          />
        ))}
      </div>
      
      {/* Phase title */}
      <div className="text-sm">
        <span className="text-gray-500">Aşama {currentPhase}/{totalPhases}:</span>
        <span className="ml-2 font-medium text-kkb-700">{phaseTitle}</span>
      </div>
    </div>
  );
}
