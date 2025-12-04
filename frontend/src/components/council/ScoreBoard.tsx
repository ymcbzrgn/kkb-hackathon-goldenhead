/**
 * ScoreBoard Component
 * Üyelerin skorlarını gösteren tablo
 */

import { cn } from '@/utils/cn';

export interface MemberScore {
  name: string;
  score: number | null;
}

interface ScoreBoardProps {
  members: MemberScore[];
}

export function ScoreBoard({ members }: ScoreBoardProps) {
  // Ortalama skor hesapla
  const validScores = members.filter(m => m.score !== null).map(m => m.score!);
  const average = validScores.length > 0 
    ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
    : null;

  return (
    <div className="bg-gray-50 rounded-xl border p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Üye Skorları</h3>
        {average !== null && (
          <span className={cn(
            'px-3 py-1 rounded-full text-sm font-bold',
            average >= 70 ? 'bg-green-100 text-green-700' :
            average >= 50 ? 'bg-yellow-100 text-yellow-700' :
            average >= 30 ? 'bg-orange-100 text-orange-700' :
            'bg-red-100 text-red-700'
          )}>
            Ort: {average}
          </span>
        )}
      </div>
      
      <div className="grid grid-cols-5 gap-2">
        {members.map((member) => (
          <div 
            key={member.name} 
            className="text-center p-2 bg-white rounded-lg border"
          >
            <p className="text-xs text-gray-500 truncate mb-1">{member.name}</p>
            {member.score !== null ? (
              <span className={cn(
                'inline-block px-2 py-0.5 rounded text-sm font-bold',
                member.score >= 70 ? 'bg-green-100 text-green-700' :
                member.score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                member.score >= 30 ? 'bg-orange-100 text-orange-700' :
                'bg-red-100 text-red-700'
              )}>
                {member.score}
              </span>
            ) : (
              <span className="text-gray-300 text-sm">-</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
