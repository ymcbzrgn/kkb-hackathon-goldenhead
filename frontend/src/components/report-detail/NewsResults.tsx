/**
 * NewsResults Component
 * Haber/medya agent sonuçları
 *
 * Backend'den gelen veri yapısı:
 * {
 *   haberler: [{
 *     id: string,
 *     baslik: string,
 *     kaynak: string,
 *     tarih: string,
 *     url: string,
 *     metin: string,
 *     sentiment: "olumlu" | "olumsuz",
 *     screenshot_path: string,
 *     relevance_confidence: number
 *   }],
 *   ozet: {
 *     toplam: number,
 *     olumlu: number,
 *     olumsuz: number,
 *     sentiment_score: number,
 *     trend: "pozitif" | "negatif" | "notr"
 *   },
 *   toplam_haber: number,
 *   kaynak_dagilimi: {...}
 * }
 */

import { motion } from 'framer-motion';
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  ImageIcon
} from 'lucide-react';
import { Card } from '@/components/ui/card';

// Backend'den gelen gerçek veri yapısı
interface NewsBackendHaber {
  id?: string;
  baslik?: string;
  kaynak?: string;
  tarih?: string;
  url?: string;
  metin?: string;
  sentiment?: 'olumlu' | 'olumsuz';
  screenshot_path?: string;
  relevance_confidence?: number;
}

interface NewsBackendData {
  haberler?: NewsBackendHaber[];
  ozet?: {
    toplam?: number;
    olumlu?: number;
    olumsuz?: number;
    sentiment_score?: number;
    trend?: 'pozitif' | 'negatif' | 'notr';
  };
  toplam_haber?: number;
  kaynak_dagilimi?: Record<string, { total: number; olumlu: number; olumsuz: number }>;
  message?: string;
}

interface NewsResultsProps {
  data: NewsBackendData;
}

const trendConfig: Record<string, { icon: typeof TrendingUp; label: string; color: string; bg: string }> = {
  pozitif: { icon: TrendingUp, label: 'Yükselen', color: 'text-green-600', bg: 'bg-green-100' },
  negatif: { icon: TrendingDown, label: 'Düşen', color: 'text-red-600', bg: 'bg-red-100' },
  notr: { icon: Minus, label: 'Stabil', color: 'text-gray-600', bg: 'bg-gray-100' },
};

// Default fallback for unknown trend
const defaultTrendConfig = { icon: Minus, label: 'Bilinmiyor', color: 'text-gray-600', bg: 'bg-gray-100' };

// Backend "olumlu"/"olumsuz", frontend display config
const sentimentConfig: Record<string, { icon: typeof ThumbsUp; color: string; bg: string; border: string; label: string }> = {
  olumlu: { icon: ThumbsUp, color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200', label: 'Olumlu' },
  olumsuz: { icon: ThumbsDown, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Olumsuz' },
};

// Default fallback for unknown sentiment
const defaultSentimentConfig = { icon: HelpCircle, color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200', label: 'Belirsiz' };

function NewsCard({ haber }: { haber: NewsBackendHaber }) {
  const config = sentimentConfig[haber?.sentiment || ''] || defaultSentimentConfig;
  const Icon = config.icon;

  // URL kontrolü - boşsa tıklanamaz yap
  const hasValidUrl = haber.url && haber.url.startsWith('http');

  const content = (
    <div className="flex items-start gap-3">
      <div className={`p-2 rounded-full ${config.bg} border ${config.border}`}>
        <Icon className={`w-4 h-4 ${config.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <h5 className="font-medium text-gray-800 mb-1 line-clamp-2">{haber.baslik || 'Başlık yok'}</h5>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{haber.kaynak || 'Kaynak bilinmiyor'}</span>
          <span>•</span>
          <span>{haber.tarih || 'Tarih bilinmiyor'}</span>
          <span>•</span>
          <span className={config.color}>{config.label}</span>
        </div>
        {/* Haber özet metni */}
        {haber.metin && (
          <p className="text-xs text-gray-500 mt-2 line-clamp-2">{haber.metin}</p>
        )}
      </div>
      {hasValidUrl && <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0" />}
      {haber.screenshot_path && <ImageIcon className="w-4 h-4 text-blue-400 flex-shrink-0" />}
    </div>
  );

  if (hasValidUrl) {
    return (
      <motion.a
        href={haber.url}
        target="_blank"
        rel="noopener noreferrer"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ scale: 1.01 }}
        className={`block p-4 rounded-lg border ${config.border} ${config.bg} hover:shadow-md transition-shadow cursor-pointer`}
      >
        {content}
      </motion.a>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-lg border ${config.border} ${config.bg}`}
    >
      {content}
    </motion.div>
  );
}

export function NewsResults({ data }: NewsResultsProps) {
  // Backend veri yapısından değerleri çıkar
  const ozet = data?.ozet || {};
  const haberler = data?.haberler || [];
  const toplamHaber = data?.toplam_haber || ozet.toplam || haberler.length || 0;
  const olumlu = ozet.olumlu || 0;
  const olumsuz = ozet.olumsuz || 0;
  const sentimentScore = ozet.sentiment_score ?? 0;
  const trendKey = ozet.trend || 'notr';

  const trend = trendConfig[trendKey] || defaultTrendConfig;
  const TrendIcon = trend.icon;
  const sentimentPercentage = Math.round((sentimentScore + 1) / 2 * 100);

  // Haber bulunamadıysa mesaj göster
  if (toplamHaber === 0 || haberler.length === 0) {
    return (
      <div className="text-center py-12">
        <Newspaper className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h4 className="font-semibold text-gray-800 mb-1">Haber Bulunamadı</h4>
        <p className="text-sm text-gray-500">
          {data?.message || 'Bu firma hakkında güncel haber bulunamadı.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Özet İstatistikler */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-kkb-700">{toplamHaber}</span>
          <span className="text-xs text-gray-500 block mt-1">Toplam Haber</span>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-green-600">{olumlu}</span>
          <span className="text-xs text-gray-500 block mt-1">Olumlu</span>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-red-600">{olumsuz}</span>
          <span className="text-xs text-gray-500 block mt-1">Olumsuz</span>
        </Card>
      </div>

      {/* Sentiment Score & Trend */}
      <Card className="p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Sentiment Score */}
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Newspaper className="w-4 h-4 text-kkb-600" />
              Medya Algı Skoru
            </h4>
            <div className="relative h-4 bg-gradient-to-r from-red-200 via-gray-200 to-green-200 rounded-full overflow-hidden">
              <motion.div
                initial={{ left: '50%' }}
                animate={{ left: `${sentimentPercentage}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 bg-white border-2 border-kkb-500 rounded-full shadow-md"
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-gray-500">
              <span>Olumsuz</span>
              <span className="font-semibold text-kkb-700">
                {sentimentScore > 0 ? '+' : ''}{sentimentScore.toFixed(2)}
              </span>
              <span>Olumlu</span>
            </div>
          </div>

          {/* Trend */}
          <div className={`flex items-center gap-3 px-4 py-3 rounded-lg ${trend.bg}`}>
            <TrendIcon className={`w-6 h-6 ${trend.color}`} />
            <div>
              <span className="text-xs text-gray-500 block">Trend</span>
              <span className={`font-semibold ${trend.color}`}>
                {trend.label}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Kaynak Dağılımı */}
      {data?.kaynak_dagilimi && Object.keys(data.kaynak_dagilimi).length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-kkb-600" />
            Kaynak Dağılımı
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.kaynak_dagilimi).map(([kaynak, stats]) => (
              <span key={kaynak} className="text-xs bg-gray-100 px-3 py-1.5 rounded-full">
                {kaynak}: {stats.total} haber
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Haberler Listesi */}
      {haberler.length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-kkb-600" />
            Haberler ({haberler.length})
          </h4>
          <div className="space-y-3">
            {haberler.map((haber, index) => (
              <NewsCard key={haber.id || index} haber={haber} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
