// Risk Level Labels
export const RISK_LEVEL_LABELS = {
  dusuk: 'Düşük Risk',
  orta_dusuk: 'Orta-Düşük Risk',
  orta: 'Orta Risk',
  orta_yuksek: 'Orta-Yüksek Risk',
  yuksek: 'Yüksek Risk',
} as const;

// Risk Level Colors (Tailwind classes)
export const RISK_LEVEL_COLORS = {
  dusuk: 'bg-risk-low text-white',
  orta_dusuk: 'bg-risk-low-medium text-white',
  orta: 'bg-risk-medium text-white',
  orta_yuksek: 'bg-risk-medium-high text-white',
  yuksek: 'bg-risk-high text-white',
} as const;

// Decision Labels
export const DECISION_LABELS = {
  onay: 'Onay',
  sartli_onay: 'Şartlı Onay',
  red: 'Red',
  inceleme_gerek: 'İnceleme Gerekli',
} as const;

// Decision Colors
export const DECISION_COLORS = {
  onay: 'bg-decision-approved text-white',
  sartli_onay: 'bg-decision-conditional text-white',
  red: 'bg-decision-rejected text-white',
  inceleme_gerek: 'bg-decision-review text-white',
} as const;

// Status Labels
export const STATUS_LABELS = {
  pending: 'Bekliyor',
  processing: 'İşleniyor',
  completed: 'Tamamlandı',
  failed: 'Hata',
} as const;

// Status Colors
export const STATUS_COLORS = {
  pending: 'bg-gray-400 text-white',
  processing: 'bg-blue-500 text-white',
  completed: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white',
} as const;

// Council Members
export const COUNCIL_MEMBERS = {
  risk_analyst: {
    id: 'risk_analyst',
    name: 'Mehmet Bey',
    role: 'Baş Risk Analisti',
    emoji: '🔴',
  },
  business_analyst: {
    id: 'business_analyst',
    name: 'Ayşe Hanım',
    role: 'İş Geliştirme Müdürü',
    emoji: '🟢',
  },
  legal_expert: {
    id: 'legal_expert',
    name: 'Av. Zeynep Hanım',
    role: 'Hukuk Müşaviri',
    emoji: '⚖️',
  },
  media_analyst: {
    id: 'media_analyst',
    name: 'Deniz Bey',
    role: 'İtibar Analisti',
    emoji: '📰',
  },
  sector_expert: {
    id: 'sector_expert',
    name: 'Prof. Dr. Ali Bey',
    role: 'Sektör Uzmanı',
    emoji: '📊',
  },
  moderator: {
    id: 'moderator',
    name: 'Genel Müdür Yardımcısı',
    role: 'Komite Başkanı',
    emoji: '👨‍⚖️',
  },
} as const;

// Agent Info
export const AGENTS = {
  tsg_agent: {
    id: 'tsg_agent',
    name: 'TSG Agent',
    description: 'Ticaret Sicili Gazetesi taranıyor',
    icon: '📰',
  },
  ihale_agent: {
    id: 'ihale_agent',
    name: 'İhale Agent',
    description: 'EKAP ihale yasağı kontrolü',
    icon: '🚫',
  },
  news_agent: {
    id: 'news_agent',
    name: 'Haber Agent',
    description: 'İnternet haberleri analizi',
    icon: '📺',
  },
} as const;

// API Config
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
  USE_MOCK: import.meta.env.VITE_USE_MOCK === 'true',
} as const;
