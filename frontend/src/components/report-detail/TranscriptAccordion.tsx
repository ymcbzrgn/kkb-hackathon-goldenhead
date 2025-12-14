/**
 * TranscriptAccordion Component
 * Komite toplantısı transcript'i accordion yapısında
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, MessageSquare, Clock } from 'lucide-react';
import { Card } from '@/components/ui/card';
import type { TranscriptEntry, CouncilPhase, CouncilMemberId } from '@/types';
import { formatShortDate } from '@/utils/formatters';

// Hook to track image load failures (React pattern instead of DOM manipulation)
function useImageFallback() {
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

  const handleImageError = useCallback((speakerId: string) => {
    setFailedImages((prev) => new Set(prev).add(speakerId));
  }, []);

  const hasImageFailed = useCallback(
    (speakerId: string) => failedImages.has(speakerId),
    [failedImages]
  );

  return { handleImageError, hasImageFailed };
}

interface TranscriptAccordionProps {
  transcript: TranscriptEntry[];
}

// Council üye fotoğrafları - CouncilIntro ile aynı mapping
const councilPhotos: Record<CouncilMemberId, string> = {
  risk_analyst: '/council/risk_analyst.png',
  business_analyst: '/council/business_analyst.png',
  legal_expert: '/council/legal_expert.png',
  media_analyst: '/council/media_analyst.png',
  sector_expert: '/council/sector_expert.png',
  moderator: '/council/moderator.png',
};

// Backend'den gelen tüm phase değerlerini destekle
const phaseLabels: Record<string, string> = {
  opening: 'Açılış',
  presentation: 'Sunum',
  risk_presentation: 'Risk Değerlendirmesi',
  business_presentation: 'İş Potansiyeli',
  legal_presentation: 'Hukuki Değerlendirme',
  media_presentation: 'Medya Analizi',
  sector_presentation: 'Sektör Değerlendirmesi',
  discussion: 'Tartışma',
  decision: 'Karar',
};

// Backend'den gelen tüm phase değerlerini destekle
const phaseColors: Record<string, { bg: string; text: string; border: string }> = {
  opening: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  presentation: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  risk_presentation: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  business_presentation: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  legal_presentation: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  media_presentation: { bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-200' },
  sector_presentation: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  discussion: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  decision: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
};

// Default renk (bilinmeyen phase için)
const defaultPhaseColor = { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };

// Group transcript entries by phase
function groupByPhase(transcript: TranscriptEntry[]) {
  const groups: { phase: CouncilPhase; entries: TranscriptEntry[] }[] = [];
  let currentPhase: CouncilPhase | null = null;

  for (const entry of transcript) {
    if (entry.phase !== currentPhase) {
      currentPhase = entry.phase;
      groups.push({ phase: currentPhase, entries: [] });
    }
    groups[groups.length - 1].entries.push(entry);
  }

  return groups;
}

function TranscriptEntryItem({
  entry,
  hasImageFailed,
  onImageError,
}: {
  entry: TranscriptEntry;
  hasImageFailed: (speakerId: string) => boolean;
  onImageError: (speakerId: string) => void;
}) {
  const photoUrl = councilPhotos[entry.speaker_id as CouncilMemberId];
  const showFallback = !photoUrl || hasImageFailed(entry.speaker_id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-4 py-4 border-b last:border-0"
    >
      {/* Avatar with Photo - React state-based fallback (no DOM manipulation) */}
      <div className="flex-shrink-0">
        {photoUrl && !showFallback ? (
          <img
            src={photoUrl}
            alt={entry.speaker_name}
            className="w-10 h-10 rounded-full object-cover border-2 border-kkb-200 shadow-sm"
            onError={() => onImageError(entry.speaker_id)}
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-kkb-100 flex items-center justify-center text-xl">
            {entry.speaker_emoji}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-800">{entry.speaker_name}</span>
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatShortDate(entry.timestamp)}
          </span>
          {entry.risk_score !== null && (
            <span className="text-xs px-2 py-0.5 bg-kkb-100 text-kkb-700 rounded-full">
              Skor: {entry.risk_score}
            </span>
          )}
        </div>
        <p className="text-gray-600 text-sm whitespace-pre-wrap">{entry.content}</p>
      </div>
    </motion.div>
  );
}

function PhaseSection({
  phase,
  entries,
  isOpen,
  onToggle,
  hasImageFailed,
  onImageError,
}: {
  phase: CouncilPhase;
  entries: TranscriptEntry[];
  isOpen: boolean;
  onToggle: () => void;
  hasImageFailed: (speakerId: string) => boolean;
  onImageError: (speakerId: string) => void;
}) {
  // Bilinmeyen phase için default renk kullan
  const colors = phaseColors[phase] || defaultPhaseColor;
  const label = phaseLabels[phase] || phase;

  return (
    <div className={`border rounded-lg overflow-hidden ${colors.border}`}>
      <button
        onClick={onToggle}
        className={`w-full flex items-center justify-between px-4 py-3 ${colors.bg} hover:opacity-90 transition-opacity`}
      >
        <div className="flex items-center gap-3">
          <MessageSquare className={`w-4 h-4 ${colors.text}`} />
          <span className={`font-semibold ${colors.text}`}>
            {label}
          </span>
          <span className="text-xs text-gray-500">
            ({entries.length} konuşma)
          </span>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className={`w-5 h-5 ${colors.text}`} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 bg-white">
              {entries.map((entry, index) => (
                <TranscriptEntryItem
                  key={index}
                  entry={entry}
                  hasImageFailed={hasImageFailed}
                  onImageError={onImageError}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function TranscriptAccordion({ transcript }: TranscriptAccordionProps) {
  const groups = groupByPhase(transcript);
  const [openPhases, setOpenPhases] = useState<Set<CouncilPhase>>(
    new Set(['decision']) // Default: only decision phase open
  );

  // React state-based image fallback handler (replaces DOM manipulation)
  const { handleImageError, hasImageFailed } = useImageFallback();

  const togglePhase = (phase: CouncilPhase) => {
    setOpenPhases((prev) => {
      const next = new Set(prev);
      if (next.has(phase)) {
        next.delete(phase);
      } else {
        next.add(phase);
      }
      return next;
    });
  };

  if (!transcript || transcript.length === 0) {
    return (
      <Card className="p-8 text-center">
        <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <h4 className="font-semibold text-gray-600 mb-1">Transcript Bulunamadı</h4>
        <p className="text-sm text-gray-400">Komite toplantısı kaydı mevcut değil.</p>
      </Card>
    );
  }

  return (
    <Card className="p-5">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-kkb-600" />
        Komite Toplantısı Transcript
      </h3>
      <div className="space-y-3">
        {groups.map((group, index) => (
          <PhaseSection
            key={index}
            phase={group.phase}
            entries={group.entries}
            isOpen={openPhases.has(group.phase)}
            onToggle={() => togglePhase(group.phase)}
            hasImageFailed={hasImageFailed}
            onImageError={handleImageError}
          />
        ))}
      </div>
    </Card>
  );
}
