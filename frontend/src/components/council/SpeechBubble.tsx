/**
 * SpeechBubble Component
 * Konuşma balonu - streaming text ile
 */

import { StreamingText } from './StreamingText';
import { cn } from '@/utils/cn';
import type { CouncilMemberId } from '@/types';

interface SpeechBubbleProps {
  speakerId: CouncilMemberId;
  speakerName: string;
  text: string;
  isStreaming?: boolean;
  score?: number;
}

export function SpeechBubble({ 
  speakerId,
  speakerName, 
  text, 
  isStreaming = false,
  score,
}: SpeechBubbleProps) {
  return (
    <div className={cn(
      'flex gap-4 p-4 rounded-xl transition-all duration-300',
      isStreaming ? 'bg-kkb-50 border-2 border-kkb-200' : 'bg-gray-50 border border-gray-200'
    )}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        <div className={cn(
          'w-12 h-12 rounded-full overflow-hidden',
          isStreaming ? 'ring-2 ring-kkb-400' : 'ring-1 ring-gray-200'
        )}>
          <img 
            src={`/council/${speakerId}.png`} 
            alt={speakerName}
            className="w-full h-full object-cover"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-2">
          <span className={cn(
            'font-semibold text-sm',
            isStreaming ? 'text-kkb-700' : 'text-gray-700'
          )}>
            {speakerName}
          </span>
          {score !== undefined && (
            <span className={cn(
              'px-3 py-1 rounded-full text-sm font-bold',
              score >= 70 ? 'bg-green-100 text-green-700' :
              score >= 50 ? 'bg-yellow-100 text-yellow-700' :
              score >= 30 ? 'bg-orange-100 text-orange-700' :
              'bg-red-100 text-red-700'
            )}>
              {score}/100
            </span>
          )}
        </div>
        <p className="text-gray-700 leading-relaxed">
          <StreamingText text={text} isComplete={!isStreaming} />
        </p>
      </div>
    </div>
  );
}
