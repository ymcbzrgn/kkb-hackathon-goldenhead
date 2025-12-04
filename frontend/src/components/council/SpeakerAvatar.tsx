/**
 * SpeakerAvatar Component
 * Konuşmacı avatarı - resim, isim, rol
 */

import { cn } from '@/utils/cn';
import type { CouncilMemberId } from '@/types';

interface SpeakerAvatarProps {
  id: CouncilMemberId;
  name: string;
  role: string;
  isActive?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SpeakerAvatar({ 
  id,
  name, 
  role, 
  isActive = false,
  size = 'md' 
}: SpeakerAvatarProps) {
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-16 h-16',
    lg: 'w-24 h-24',
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div 
        className={cn(
          'rounded-full overflow-hidden transition-all duration-300',
          sizeClasses[size],
          isActive 
            ? 'ring-4 ring-kkb-500 ring-offset-2 scale-110' 
            : 'ring-2 ring-gray-200'
        )}
      >
        <img 
          src={`/council/${id}.png`} 
          alt={name}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="text-center">
        <p className={cn(
          'font-medium text-sm transition-colors',
          isActive ? 'text-kkb-700' : 'text-gray-700'
        )}>
          {name}
        </p>
        <p className="text-xs text-gray-500">{role}</p>
      </div>
    </div>
  );
}
