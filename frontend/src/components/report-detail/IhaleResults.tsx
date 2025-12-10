/**
 * IhaleResults Component
 * İhale yasaklılık agent sonuçları
 */

import { motion } from 'framer-motion';
import { Gavel, CheckCircle2, AlertTriangle, Calendar, Building, FileWarning } from 'lucide-react';
import { Card } from '@/components/ui/card';
import type { IhaleData, YasakBilgisi } from '@/types';
import { formatDate } from '@/utils/formatters';

interface IhaleResultsProps {
  data: IhaleData;
}

function YasakCard({ yasak, isActive }: { yasak: YasakBilgisi; isActive?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-lg border ${
        isActive 
          ? 'bg-red-50 border-red-200' 
          : 'bg-gray-50 border-gray-200'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-full ${isActive ? 'bg-red-100' : 'bg-gray-200'}`}>
          <FileWarning className={`w-4 h-4 ${isActive ? 'text-red-600' : 'text-gray-500'}`} />
        </div>
        <div className="flex-1 space-y-2">
          <p className={`font-medium ${isActive ? 'text-red-800' : 'text-gray-700'}`}>
            {yasak.sebep}
          </p>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-1.5 text-gray-600">
              <Building className="w-3.5 h-3.5" />
              <span>{yasak.kurum}</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-600">
              <Calendar className="w-3.5 h-3.5" />
              <span>{formatDate(yasak.baslangic)} - {formatDate(yasak.bitis)}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function IhaleResults({ data }: IhaleResultsProps) {
  return (
    <div className="space-y-6">
      {/* Aktif Durum */}
      <Card className="p-5">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-full ${
            data.yasak_durumu ? 'bg-red-100' : 'bg-green-100'
          }`}>
            {data.yasak_durumu ? (
              <AlertTriangle className="w-6 h-6 text-red-600" />
            ) : (
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            )}
          </div>
          <div>
            <h4 className="text-lg font-semibold">
              {data.yasak_durumu ? 'Aktif İhale Yasağı Mevcut' : 'İhale Yasağı Bulunmuyor'}
            </h4>
            <p className="text-sm text-gray-500">
              {data.yasak_durumu 
                ? 'Firma şu anda kamu ihalelerine katılma yasağı altındadır.'
                : 'Firma kamu ihalelerine katılabilir durumda.'}
            </p>
          </div>
        </div>
      </Card>

      {/* Aktif Yasak */}
      {data.aktif_yasak && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-red-700 mb-4 flex items-center gap-2">
            <Gavel className="w-4 h-4" />
            Aktif Yasak Detayı
          </h4>
          <YasakCard yasak={data.aktif_yasak} isActive />
        </Card>
      )}

      {/* Geçmiş Yasaklar */}
      {(data?.gecmis_yasaklar || []).length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Gavel className="w-4 h-4 text-gray-500" />
            Geçmiş Yasaklar ({(data?.gecmis_yasaklar || []).length})
          </h4>
          <div className="space-y-3">
            {(data?.gecmis_yasaklar || []).map((yasak, index) => (
              <YasakCard key={index} yasak={yasak} />
            ))}
          </div>
        </Card>
      )}

      {/* Temiz Geçmiş */}
      {!data?.yasak_durumu && (data?.gecmis_yasaklar || []).length === 0 && (
        <Card className="p-5">
          <div className="text-center py-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h4 className="font-semibold text-gray-800 mb-1">Temiz Sicil</h4>
            <p className="text-sm text-gray-500">
              Firmanın geçmişinde herhangi bir ihale yasağı kaydı bulunmamaktadır.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
