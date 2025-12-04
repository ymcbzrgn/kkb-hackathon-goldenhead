/**
 * Report List
 * Rapor kartlarının grid listesi
 */

import { AnimatePresence } from 'framer-motion';
import { ReportCard } from './ReportCard';
import type { ReportListItem } from '@/types';

interface ReportListProps {
  reports: ReportListItem[];
  onDelete?: (id: string) => void;
}

export function ReportList({ reports, onDelete }: ReportListProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <AnimatePresence mode="popLayout">
        {reports.map((report) => (
          <ReportCard
            key={report.id}
            report={report}
            onDelete={onDelete}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
