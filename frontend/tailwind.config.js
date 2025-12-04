/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // KKB Primary - Navy Blue (Logo ana rengi)
        'kkb': {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#627d98',
          600: '#486581',
          700: '#334e68',
          800: '#243b53',
          900: '#1B365D', // Ana primary renk
          950: '#0F1F3D',
        },
        // KKB Accent - Orange (Logo vurgu rengi)
        'accent': {
          50: '#fff8f1',
          100: '#feecdc',
          200: '#fcd9bd',
          300: '#fdba8c',
          400: '#ff8a4c',
          500: '#F7941D', // Ana accent renk
          600: '#E07B00',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // Risk Levels
        'risk': {
          low: '#22C55E',        // Düşük - Yeşil
          'low-medium': '#84CC16', // Orta-Düşük - Açık Yeşil
          medium: '#F59E0B',     // Orta - Sarı
          'medium-high': '#F97316', // Orta-Yüksek - Turuncu
          high: '#EF4444',       // Yüksek - Kırmızı
        },
        // Decision Colors
        'decision': {
          approved: '#22C55E',   // Onay - Yeşil
          conditional: '#F59E0B', // Şartlı Onay - Sarı
          rejected: '#EF4444',   // Red - Kırmızı
          review: '#3B82F6',     // İnceleme Gerekli - Mavi
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
    },
  },
  plugins: [],
}
