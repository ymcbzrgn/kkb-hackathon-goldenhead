/**
 * NewsResults Component
 * Haber/medya agent sonuçları
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
  Circle,
  HelpCircle
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import type { NewsData, HaberItem } from '@/types';
import { formatDate } from '@/utils/formatters';

interface NewsResultsProps {
  data: NewsData;
}

const trendConfig: Record<string, { icon: typeof TrendingUp; label: string; color: string; bg: string }> = {
  yukari: { icon: TrendingUp, label: 'Yükselen', color: 'text-green-600', bg: 'bg-green-100' },
  asagi: { icon: TrendingDown, label: 'Düşen', color: 'text-red-600', bg: 'bg-red-100' },
  stabil: { icon: Minus, label: 'Stabil', color: 'text-gray-600', bg: 'bg-gray-100' },
};

// Default fallback for unknown trend
const defaultTrendConfig = { icon: Minus, label: 'Bilinmiyor', color: 'text-gray-600', bg: 'bg-gray-100' };

const sentimentConfig: Record<string, { icon: typeof ThumbsUp; color: string; bg: string; border: string }> = {
  pozitif: { icon: ThumbsUp, color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
  negatif: { icon: ThumbsDown, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
  notr: { icon: Circle, color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200' },
};

// Default fallback for unknown sentiment
const defaultSentimentConfig = { icon: HelpCircle, color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200' };

function NewsCard({ haber }: { haber: HaberItem }) {
  const config = sentimentConfig[haber?.sentiment] || defaultSentimentConfig;
  const Icon = config.icon;

  return (
    <motion.a
      href={haber.url}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      className={`block p-4 rounded-lg border ${config.border} ${config.bg} hover:shadow-md transition-shadow`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-full ${config.bg} border ${config.border}`}>
          <Icon className={`w-4 h-4 ${config.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h5 className="font-medium text-gray-800 mb-1 line-clamp-2">{haber.baslik}</h5>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>{haber.kaynak}</span>
            <span>•</span>
            <span>{formatDate(haber.tarih)}</span>
          </div>
        </div>
        <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
    </motion.a>
  );
}

export function NewsResults({ data }: NewsResultsProps) {
  const trend = trendConfig[data?.trend] || defaultTrendConfig;
  const TrendIcon = trend.icon;
  const sentimentPercentage = Math.round(((data?.sentiment_score ?? 0) + 1) / 2 * 100);

  return (
    <div className="space-y-6">
      {/* Özet İstatistikler */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-kkb-700">{data.toplam_haber}</span>
          <span className="text-xs text-gray-500 block mt-1">Toplam Haber</span>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-green-600">{data.pozitif}</span>
          <span className="text-xs text-gray-500 block mt-1">Pozitif</span>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-gray-600">{data.notr}</span>
          <span className="text-xs text-gray-500 block mt-1">Nötr</span>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-2xl font-bold text-red-600">{data.negatif}</span>
          <span className="text-xs text-gray-500 block mt-1">Negatif</span>
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
              <span>Negatif</span>
              <span className="font-semibold text-kkb-700">
                {data.sentiment_score > 0 ? '+' : ''}{data.sentiment_score.toFixed(2)}
              </span>
              <span>Pozitif</span>
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

      {/* Önemli Haberler */}
      {(data?.onemli_haberler || []).length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-kkb-600" />
            Önemli Haberler ({(data?.onemli_haberler || []).length})
          </h4>
          <div className="space-y-3">
            {(data?.onemli_haberler || []).map((haber, index) => (
              <NewsCard key={index} haber={haber} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
