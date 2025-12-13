/**
 * CouncilContainer Component
 * Komite görüşmesi ana container
 */

import { SpeakerAvatar } from './SpeakerAvatar';
import { SpeechBubble } from './SpeechBubble';
import { ScoreBoard } from './ScoreBoard';
import { PhaseIndicator } from './PhaseIndicator';
import { FinalDecisionCard } from './FinalDecisionCard';
import { useCouncilStore } from '@/stores';
import type { CouncilMemberId } from '@/types';

// Komite üyeleri
const councilMembers: Array<{
  id: CouncilMemberId;
  name: string;
  role: string;
}> = [
  { id: 'moderator', name: 'Komite Başkanı', role: 'Genel Müdür Yardımcısı' },
  { id: 'risk_analyst', name: 'Mehmet Bey', role: 'Baş Risk Analisti' },
  { id: 'business_analyst', name: 'Ayşe Hanım', role: 'İş Geliştirme Müdürü' },
  { id: 'legal_expert', name: 'Av. Zeynep Hanım', role: 'Hukuk Müşaviri' },
  { id: 'media_analyst', name: 'Deniz Bey', role: 'İtibar Analisti' },
  { id: 'sector_expert', name: 'Prof. Dr. Ali Bey', role: 'Sektör Uzmanı' },
];

export function CouncilContainer() {
  // Council store state
  const transcript = useCouncilStore((s) => s.transcript);
  const currentSpeaker = useCouncilStore((s) => s.currentSpeaker);
  const currentSpeech = useCouncilStore((s) => s.currentSpeech);
  const isTyping = useCouncilStore((s) => s.isTyping);
  const currentPhase = useCouncilStore((s) => s.currentPhase);
  const phaseNumber = useCouncilStore((s) => s.phaseNumber);
  const totalPhases = useCouncilStore((s) => s.totalPhases);
  const phaseTitle = useCouncilStore((s) => s.phaseTitle);
  const scores = useCouncilStore((s) => s.scores);
  const finalDecision = useCouncilStore((s) => s.finalDecision);

  // Member scores for ScoreBoard
  const memberScores = councilMembers.map((member) => ({
    name: member.name,
    score: scores[member.id] ?? null,
  }));

  // Phase label
  const displayPhaseTitle = phaseTitle || (
    currentPhase === 'opening' ? 'Açılış'
    : currentPhase === 'presentation' ? 'Sunum'
    : currentPhase === 'discussion' ? 'Tartışma'
    : currentPhase === 'decision' ? 'Karar'
    : 'Komite'
  );

  const isComplete = currentPhase === 'decision' && finalDecision !== null;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <span className="text-2xl">🏛️</span>
          Kredi Komitesi Görüşmesi
        </h2>
        <PhaseIndicator 
          currentPhase={phaseNumber || 1} 
          totalPhases={totalPhases || 8} 
          phaseTitle={displayPhaseTitle} 
        />
      </div>

      {/* Council Members */}
      <div className="flex justify-center gap-3 py-4 border-b border-gray-200 flex-wrap">
        {councilMembers.map((member) => (
          <SpeakerAvatar
            key={member.id}
            id={member.id}
            name={member.name}
            role={member.role}
            isActive={currentSpeaker?.id === member.id}
            size="sm"
          />
        ))}
      </div>

      {/* Speech Bubbles / Transcript */}
      <div className="space-y-4 max-h-96 overflow-y-auto px-2">
        {transcript.length === 0 && !isTyping ? (
          <div className="text-center py-8 text-gray-500 space-y-2">
            <p className="animate-pulse text-lg">Komite toplanıyor...</p>
            <p className="text-sm">İlk konuşmacı hazırlanıyor</p>
          </div>
        ) : (
          <>
            {/* Past speeches */}
            {transcript.map((entry, idx) => (
              <SpeechBubble
                key={`${entry.speaker_id}-${idx}`}
                speakerId={entry.speaker_id}
                speakerName={entry.speaker_name}
                text={entry.content}
                isStreaming={false}
                score={entry.risk_score ?? undefined}
              />
            ))}

            {/* Current streaming speech */}
            {isTyping && currentSpeaker && (
              <SpeechBubble
                speakerId={currentSpeaker.id}
                speakerName={currentSpeaker.name}
                text={currentSpeech}
                isStreaming={true}
              />
            )}
          </>
        )}
      </div>

      {/* Score Board (show when there are scores) */}
      {Object.keys(scores).length > 0 && (
        <ScoreBoard members={memberScores} />
      )}

      {/* Final Decision */}
      {isComplete && finalDecision && (
        <FinalDecisionCard
          decision={finalDecision.decision}
          riskLevel={finalDecision.risk_level}
          finalScore={finalDecision.final_score}
          consensus={finalDecision.consensus}
          conditions={finalDecision.conditions}
          dissentNote={finalDecision.dissent_note ?? undefined}
        />
      )}
    </div>
  );
}
