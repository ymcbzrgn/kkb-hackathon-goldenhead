/**
 * StreamingText Component
 * Yazı yazılır gibi gelen text - typing effect
 */

import { useEffect, useState } from 'react';

interface StreamingTextProps {
  text: string;
  isComplete: boolean;
  speed?: number; // ms per character
}

export function StreamingText({ text, isComplete, speed = 30 }: StreamingTextProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // Eğer complete ise tüm text'i göster
    if (isComplete) {
      setDisplayedText(text);
      setCurrentIndex(text.length);
      return;
    }

    // Typing effect
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText(text.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, speed);
      
      return () => clearTimeout(timeout);
    }
  }, [text, currentIndex, isComplete, speed]);

  // Text değiştiğinde (yeni chunk geldiğinde) devam et
  useEffect(() => {
    if (text.length > currentIndex && !isComplete) {
      // Yeni text geldi, devam et
    }
  }, [text, currentIndex, isComplete]);

  return (
    <span>
      {displayedText}
      {!isComplete && currentIndex < text.length && (
        <span className="inline-block w-2 h-4 bg-kkb-600 ml-0.5 animate-pulse" />
      )}
    </span>
  );
}
