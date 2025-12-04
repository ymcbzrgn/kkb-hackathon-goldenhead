/**
 * ConditionsList Component
 * Karar şartları listesi
 */

import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, Info } from 'lucide-react';

interface ConditionsListProps {
  conditions: string[];
  dissentNote?: string | null;
}

export function ConditionsList({ conditions, dissentNote }: ConditionsListProps) {
  if (conditions.length === 0 && !dissentNote) {
    return (
      <div className="flex items-center gap-2 text-gray-500 py-4">
        <CheckCircle2 className="w-5 h-5 text-green-500" />
        <span>Herhangi bir özel şart belirtilmemiştir.</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Conditions */}
      {conditions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500" />
            Şartlar ve Öneriler
          </h4>
          <ul className="space-y-2">
            {conditions.map((condition, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-100 rounded-lg"
              >
                <span className="flex-shrink-0 w-6 h-6 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center text-sm font-medium">
                  {index + 1}
                </span>
                <span className="text-sm text-amber-800">{condition}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Dissent Note */}
      {dissentNote && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: conditions.length * 0.1 + 0.2 }}
          className="p-4 bg-blue-50 border border-blue-100 rounded-lg"
        >
          <h4 className="text-sm font-medium text-blue-700 flex items-center gap-2 mb-2">
            <Info className="w-4 h-4" />
            Muhalefet Şerhi
          </h4>
          <p className="text-sm text-blue-800">{dissentNote}</p>
        </motion.div>
      )}
    </div>
  );
}
