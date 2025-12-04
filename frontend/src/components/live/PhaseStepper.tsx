/**
 * PhaseStepper Component
 * Aşama göstergesi (Agents → Council → Complete)
 */

import { motion } from 'framer-motion';
import { Search, Users, CheckCircle, Loader2 } from 'lucide-react';

type Phase = 'agents' | 'council' | 'completed' | 'failed';

interface PhaseStepperProps {
  currentPhase: Phase;
}

const phases = [
  { id: 'agents', label: 'Veri Toplama', icon: Search },
  { id: 'council', label: 'Komite Değerlendirmesi', icon: Users },
  { id: 'completed', label: 'Tamamlandı', icon: CheckCircle },
];

export function PhaseStepper({ currentPhase }: PhaseStepperProps) {
  const currentIndex = phases.findIndex((p) => p.id === currentPhase);

  return (
    <div className="flex items-center justify-center gap-2">
      {phases.map((phase, index) => {
        const isActive = phase.id === currentPhase;
        const isCompleted = index < currentIndex;
        const Icon = phase.icon;

        return (
          <div key={phase.id} className="flex items-center">
            {/* Step */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full transition-colors ${
                isActive
                  ? 'bg-kkb-600 text-white shadow-lg'
                  : isCompleted
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-400'
              }`}
            >
              {isActive && currentPhase !== 'completed' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Icon className="w-4 h-4" />
              )}
              <span className="text-sm font-medium hidden sm:inline">{phase.label}</span>
            </motion.div>

            {/* Connector */}
            {index < phases.length - 1 && (
              <div className="w-8 h-0.5 mx-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: isCompleted ? 1 : 0 }}
                  transition={{ duration: 0.3 }}
                  className="h-full bg-green-500 origin-left"
                />
                <div className="h-full bg-gray-200 -mt-0.5" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
