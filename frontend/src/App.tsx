import { Routes, Route } from 'react-router-dom'

// Pages (şimdilik placeholder)
function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-kkb-900 to-kkb-800 flex items-center justify-center">
      <div className="text-center text-white">
        <h1 className="text-4xl font-bold mb-4">🏢 Firma İstihbarat Raporu</h1>
        <p className="text-kkb-200 text-lg mb-8">AI destekli firma risk analizi ve kredi değerlendirmesi</p>
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-8 max-w-md mx-auto">
          <p className="text-accent-500 font-semibold">✅ Proje Kurulumu Başarılı!</p>
          <p className="text-sm text-kkb-300 mt-2">Vite + React + TypeScript + Tailwind</p>
          <p className="text-sm text-kkb-300">Framer Motion + React Router + Zustand</p>
        </div>
        <p className="mt-8 text-sm text-kkb-400">
          GoldenHead Team | KKB Agentic AI Hackathon 2024
        </p>
      </div>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/reports" element={<div>Reports Page - Coming Soon</div>} />
      <Route path="/reports/:id" element={<div>Report Detail - Coming Soon</div>} />
      <Route path="/reports/:id/live" element={<div>Live Report - Coming Soon</div>} />
    </Routes>
  )
}

export default App
