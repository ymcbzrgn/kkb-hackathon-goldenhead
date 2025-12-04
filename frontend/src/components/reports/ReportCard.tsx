/**
 * Report Card
 * Tek bir raporu gösteren kart
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building2, Calendar, Clock, ArrowRight, Trash2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from './StatusBadge';
import { RiskBadge } from './RiskBadge';
import { formatDate, formatDuration } from '@/utils/formatters';
import type { ReportListItem } from '@/types';

interface ReportCardProps {
  report: ReportListItem;
  onDelete?: (id: string) => void;
}

export function ReportCard({ report, onDelete }: ReportCardProps) {
  const isProcessing = report.status === 'processing';
  const isCompleted = report.status === 'completed';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      <Card className="group relative overflow-hidden hover:shadow-lg transition-all duration-300">
        {/* Top gradient bar based on status */}
        <div
          className={`absolute top-0 left-0 right-0 h-1 ${
            report.status === 'completed'
              ? 'bg-gradient-to-r from-green-400 to-green-600'
              : report.status === 'processing'
              ? 'bg-gradient-to-r from-blue-400 to-blue-600'
              : report.status === 'failed'
              ? 'bg-gradient-to-r from-red-400 to-red-600'
              : 'bg-gradient-to-r from-gray-300 to-gray-400'
          }`}
        />

        <CardContent className="p-5">
          {/* Header: Company Name + Status */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-kkb-100 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-kkb-600" />
              </div>
              <div>
                <h3 className="font-semibold text-kkb-900 text-lg leading-tight">
                  {report.company_name}
                </h3>
                {report.company_tax_no && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    VKN: {report.company_tax_no}
                  </p>
                )}
              </div>
            </div>
            <StatusBadge status={report.status} size="sm" />
          </div>

          {/* Risk Level & Score (only for completed) */}
          {isCompleted && (
            <div className="flex items-center gap-3 mb-4">
              <RiskBadge 
                riskLevel={report.risk_level} 
                score={report.final_score}
                showScore 
                size="md"
              />
            </div>
          )}

          {/* Meta Info */}
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(report.created_at)}</span>
            </div>
            {report.duration_seconds && (
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                <span>{formatDuration(report.duration_seconds)}</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
            <Link
              to={isProcessing ? `/reports/${report.id}/live` : `/reports/${report.id}`}
              className="flex-1"
            >
              <Button
                variant={isProcessing ? 'primary' : 'secondary'}
                size="sm"
                className="w-full group-hover:shadow-md transition-shadow"
              >
                {isProcessing ? (
                  <>
                    <span className="relative flex h-2 w-2 mr-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
                    </span>
                    Canlı İzle
                  </>
                ) : (
                  <>
                    Detayları Gör
                    <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </Button>
            </Link>

            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(report.id)}
                className="text-gray-400 hover:text-red-500 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
