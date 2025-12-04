/**
 * TsgResults Component
 * TSG (Ticaret Sicil Gazetesi) agent sonuçları
 */

import { motion } from 'framer-motion';
import { Building2, Users, Briefcase, TrendingUp, Calendar, MapPin } from 'lucide-react';
import { Card } from '@/components/ui/card';
import type { TsgData } from '@/types';
import { formatMoney, formatDate } from '@/utils/formatters';

interface TsgResultsProps {
  data: TsgData;
}

export function TsgResults({ data }: TsgResultsProps) {
  return (
    <div className="space-y-6">
      {/* Şirket Bilgileri */}
      <Card className="p-5">
        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-kkb-600" />
          Şirket Bilgileri
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start gap-3">
            <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <span className="text-xs text-gray-500 block">Kuruluş Tarihi</span>
              <span className="text-sm font-medium">{formatDate(data.kurulus_tarihi)}</span>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <TrendingUp className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <span className="text-xs text-gray-500 block">Sermaye</span>
              <span className="text-sm font-medium">
                {formatMoney(data.sermaye, data.sermaye_para_birimi)}
              </span>
            </div>
          </div>
          <div className="flex items-start gap-3 md:col-span-2">
            <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <span className="text-xs text-gray-500 block">Adres</span>
              <span className="text-sm font-medium">{data.adres}</span>
            </div>
          </div>
          <div className="flex items-start gap-3 md:col-span-2">
            <Briefcase className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <span className="text-xs text-gray-500 block">Faaliyet Konusu</span>
              <span className="text-sm font-medium">{data.faaliyet_konusu}</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Ortaklar */}
      <Card className="p-5">
        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Users className="w-4 h-4 text-kkb-600" />
          Ortaklık Yapısı
        </h4>
        <div className="space-y-3">
          {data.ortaklar.map((ortak, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <span className="font-medium text-gray-800">{ortak.ad}</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-kkb-500 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${ortak.pay_orani}%` }}
                    transition={{ delay: 0.3 + index * 0.1, duration: 0.5 }}
                  />
                </div>
                <span className="text-sm font-semibold text-kkb-700 w-12 text-right">
                  %{ortak.pay_orani}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </Card>

      {/* Yönetim Kurulu */}
      <Card className="p-5">
        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-kkb-600" />
          Yönetim Kurulu
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.yonetim_kurulu.map((uye, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-3 bg-gray-50 rounded-lg"
            >
              <span className="font-medium text-gray-800 block">{uye.ad}</span>
              <span className="text-xs text-gray-500">{uye.gorev}</span>
            </motion.div>
          ))}
        </div>
      </Card>

      {/* Sermaye Değişiklikleri */}
      {data.sermaye_degisiklikleri.length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-kkb-600" />
            Sermaye Değişiklikleri
          </h4>
          <div className="space-y-2">
            {data.sermaye_degisiklikleri.map((degisiklik, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm"
              >
                <span className="text-gray-600">{formatDate(degisiklik.tarih)}</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">
                    {formatMoney(degisiklik.eski, 'TRY')}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="font-semibold text-kkb-700">
                    {formatMoney(degisiklik.yeni, 'TRY')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
