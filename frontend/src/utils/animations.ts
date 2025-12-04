import type { Variants } from 'framer-motion';

// Fade in from bottom
export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

// Fade in from left
export const fadeInLeft: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
};

// Fade in from right
export const fadeInRight: Variants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
};

// Scale up
export const scaleUp: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.9 },
};

// Scale bump (for score changes)
export const scaleBump: Variants = {
  initial: { scale: 1 },
  animate: { 
    scale: [1, 1.15, 1],
    transition: { duration: 0.3 }
  },
};

// Stagger container
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

// Stagger item
export const staggerItem: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

// Speech bubble drop (for council messages)
export const speechDrop: Variants = {
  initial: { opacity: 0, y: -10, scale: 0.95 },
  animate: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: { duration: 0.2 }
  },
};

// Score revision flash
export const scoreRevision: Variants = {
  initial: { scale: 1, backgroundColor: 'transparent' },
  animate: { 
    scale: [1, 1.1, 1],
    transition: { duration: 0.4 }
  },
};

// Progress bar fill
export const progressFill: Variants = {
  initial: { width: 0 },
  animate: (progress: number) => ({
    width: `${progress}%`,
    transition: { duration: 0.5, ease: 'easeOut' }
  }),
};

// Pulse animation
export const pulse: Variants = {
  initial: { opacity: 1 },
  animate: {
    opacity: [1, 0.5, 1],
    transition: { duration: 1.5, repeat: Infinity }
  },
};

// Typing cursor blink
export const cursorBlink: Variants = {
  initial: { opacity: 1 },
  animate: {
    opacity: [1, 0, 1],
    transition: { duration: 0.8, repeat: Infinity }
  },
};

// Card hover
export const cardHover: Variants = {
  initial: { scale: 1 },
  hover: { 
    scale: 1.02,
    transition: { duration: 0.2 }
  },
  tap: { scale: 0.98 },
};

// Default transition
export const defaultTransition = {
  duration: 0.3,
  ease: [0.4, 0, 0.2, 1],
};

// Spring transition (for bouncy effects)
export const springTransition = {
  type: 'spring',
  stiffness: 300,
  damping: 20,
};
