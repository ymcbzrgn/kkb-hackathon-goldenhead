/**
 * Empty State
 * Rapor bulunamadığında gösterilen durum
 */

import { motion } from 'framer-motion';
import { FileSearch, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  title?: string;
  description?: string;
  showAction?: boolean;
}

export function EmptyState({
  title = 'Henüz rapor yok',
  description = 'İlk raporunuzu oluşturmak için ana sayfaya gidin.',
  showAction = true,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 px-4"
    >
      <div className="w-20 h-20 rounded-2xl bg-gray-100 flex items-center justify-center mb-6">
        <FileSearch className="w-10 h-10 text-gray-400" />
      </div>
      
      <h3 className="text-xl font-semibold text-gray-700 mb-2 text-center">
        {title}
      </h3>
      
      <p className="text-gray-500 text-center max-w-md mb-6">
        {description}
      </p>

      {showAction && (
        <Link to="/">
          <Button variant="primary" className="gap-2">
            <Plus className="w-4 h-4" />
            Yeni Rapor Oluştur
          </Button>
        </Link>
      )}
    </motion.div>
  );
}
