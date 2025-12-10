/**
 * FinalDecision Component
 * Ana karar kartı
 */

import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, Shield, HelpCircle } from 'lucide-react';
import type { Decision, RiskLevel } from '@/types';
import { RiskGauge } from './RiskGauge';
import { ConsensusBar } from './ConsensusBar';
import { ConditionsList } from './ConditionsList';

interface FinalDecisionProps {
  decision: Decision;
  score: number;
  riskLevel: RiskLevel;
  consensus: number;
  conditions: string[];
  dissentNote?: string | null;
}

const decisionConfig: Record<string, {
  icon: typeof CheckCircle;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  onay: {
    icon: CheckCircle,
    label: 'ONAY',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
  sartli_onay: {
    icon: AlertTriangle,
    label: 'ŞARTLI ONAY',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  red: {
    icon: XCircle,
    label: 'RED',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  inceleme_gerek: {
    icon: AlertTriangle,
    label: 'İNCELEME GEREKLİ',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
};

// Default fallback for unknown decision types
const defaultDecisionConfig = {
  icon: HelpCircle,
  label: 'BİLİNMİYOR',
  color: 'text-gray-600',
  bgColor: 'bg-gray-50',
  borderColor: 'border-gray-200',
};

export function FinalDecision({
  decision,
  score,
  riskLevel,
  consensus,
  conditions,
  dissentNote,
}: FinalDecisionProps) {
  const config = decisionConfig[decision] || defaultDecisionConfig;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border-2 ${config.borderColor} ${config.bgColor} overflow-hidden`}
    >
      {/* Decision Header */}
      <div className={`px-6 py-4 ${config.bgColor} border-b ${config.borderColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${config.bgColor} border ${config.borderColor}`}>
              <Shield className={`w-6 h-6 ${config.color}`} />
            </div>
            <h2 className="text-lg font-semibold text-gray-800">Komite Kararı</h2>
          </div>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
            className={`flex items-center gap-2 px-4 py-2 rounded-full ${config.bgColor} border ${config.borderColor}`}
          >
            <Icon className={`w-5 h-5 ${config.color}`} />
            <span className={`font-bold ${config.color}`}>{config.label}</span>
          </motion.div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 bg-white">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Risk Gauge */}
          <div className="flex justify-center">
            <RiskGauge score={score} riskLevel={riskLevel} size="lg" />
          </div>

          {/* Consensus & Details */}
          <div className="lg:col-span-2 space-y-6">
            <ConsensusBar consensus={consensus} />
            
            <div className="border-t pt-4">
              <ConditionsList conditions={conditions} dissentNote={dissentNote} />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
