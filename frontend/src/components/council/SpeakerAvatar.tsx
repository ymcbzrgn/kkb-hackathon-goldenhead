/**
 * SpeakerAvatar Component
 * Konuşmacı avatarı - emoji, isim, rol
 */

import { cn } from '@/utils/cn';

interface SpeakerAvatarProps {
  name: string;
  role: string;
  emoji: string;
  isActive?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SpeakerAvatar({ 
  name, 
  role, 
  emoji, 
  isActive = false,
  size = 'md' 
}: SpeakerAvatarProps) {
  const sizeClasses = {
    sm: 'w-10 h-10 text-xl',
    md: 'w-14 h-14 text-2xl',
    lg: 'w-20 h-20 text-4xl',
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div 
        className={cn(
          'rounded-full flex items-center justify-center transition-all duration-300',
          sizeClasses[size],
          isActive 
            ? 'bg-kkb-100 ring-4 ring-kkb-500 ring-offset-2 scale-110' 
            : 'bg-gray-100'
        )}
      >
        <span>{emoji}</span>
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
