/**
 * FinalDecisionCard Component
 * Final karar kartı - dramatik reveal
 */

import { cn } from '@/utils/cn';
import { CheckCircle, XCircle, AlertCircle, HelpCircle } from 'lucide-react';
import type { Decision, RiskLevel } from '@/types';

interface FinalDecisionCardProps {
  decision: Decision;
  riskLevel: RiskLevel;
  finalScore: number;
  consensus: number;
  conditions?: string[];
  dissentNote?: string;
}

const decisionConfig: Record<Decision, {
  icon: typeof CheckCircle;
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
  onay: {
    icon: CheckCircle,
    label: 'ONAY',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-300',
  },
  sartli_onay: {
    icon: AlertCircle,
    label: 'ŞARTLI ONAY',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-300',
  },
  red: {
    icon: XCircle,
    label: 'RED',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-300',
  },
  inceleme_gerek: {
    icon: HelpCircle,
    label: 'İNCELEME GEREKLİ',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-300',
  },
};

const riskLabels: Record<RiskLevel, string> = {
  dusuk: 'Düşük Risk',
  orta_dusuk: 'Orta-Düşük Risk',
  orta: 'Orta Risk',
  orta_yuksek: 'Orta-Yüksek Risk',
  yuksek: 'Yüksek Risk',
};

export function FinalDecisionCard({
  decision,
  riskLevel,
  finalScore,
  consensus,
  conditions,
  dissentNote,
}: FinalDecisionCardProps) {
  const config = decisionConfig[decision];
  const Icon = config.icon;

  return (
    <div className={cn(
      'rounded-2xl border-2 p-6 transition-all duration-500',
      config.bgColor,
      config.borderColor
    )}>
      {/* Header */}
      <div className="flex items-center justify-center gap-3 mb-6">
        <Icon className={cn('w-10 h-10', config.textColor)} />
        <h2 className={cn('text-3xl font-bold', config.textColor)}>
          {config.label}
        </h2>
      </div>

      {/* Score & Risk */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-4 bg-white/50 rounded-xl">
          <p className="text-sm text-gray-500 mb-1">Final Skor</p>
          <p className={cn('text-3xl font-bold', config.textColor)}>{finalScore}</p>
        </div>
        <div className="text-center p-4 bg-white/50 rounded-xl">
          <p className="text-sm text-gray-500 mb-1">Risk Seviyesi</p>
          <p className={cn('text-lg font-semibold', config.textColor)}>{riskLabels[riskLevel]}</p>
        </div>
        <div className="text-center p-4 bg-white/50 rounded-xl">
          <p className="text-sm text-gray-500 mb-1">Konsensüs</p>
          <p className={cn('text-3xl font-bold', config.textColor)}>%{consensus}</p>
        </div>
      </div>

      {/* Conditions */}
      {conditions && conditions.length > 0 && (
        <div className="mb-4 p-4 bg-white/50 rounded-xl">
          <p className="text-sm font-semibold text-gray-700 mb-2">Şartlar:</p>
          <ul className="space-y-1">
            {conditions.map((condition, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-kkb-600">•</span>
                {condition}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dissent Note */}
      {dissentNote && (
        <div className="p-4 bg-white/50 rounded-xl border-l-4 border-amber-400">
          <p className="text-sm font-semibold text-amber-700 mb-1">Muhalefet Şerhi:</p>
          <p className="text-sm text-gray-600">{dissentNote}</p>
        </div>
      )}
    </div>
  );
}
