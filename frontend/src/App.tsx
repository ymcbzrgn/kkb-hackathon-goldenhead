import { Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout'

// Pages (şimdilik placeholder - Faz 3'te detaylı yapılacak)
function Landing() {
  return (
    <div className="container px-4 py-12 mx-auto">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 mb-6 rounded-2xl bg-gradient-to-br from-kkb-800 to-kkb-900 shadow-xl shadow-kkb-900/30">
          <span className="text-3xl font-bold text-white">K</span>
        </div>
        <h1 className="text-4xl font-bold text-kkb-900 mb-4">
          Firma İstihbarat Raporu
        </h1>
        <p className="text-gray-600 text-lg mb-8 max-w-xl mx-auto">
          AI destekli firma risk analizi ve 6 kişilik sanal kredi komitesi değerlendirmesi
        </p>
        <div className="bg-white rounded-xl border border-gray-200 p-8 max-w-md mx-auto shadow-sm">
          <div className="flex items-center justify-center gap-2 text-decision-approved font-semibold mb-4">
            <span className="text-2xl">✅</span>
            <span>Proje Kurulumu Başarılı!</span>
          </div>
          <div className="space-y-2 text-sm text-gray-500">
            <p>Vite + React + TypeScript + Tailwind</p>
            <p>Framer Motion + React Router + Zustand</p>
            <p>shadcn/ui Components + KKB Theme</p>
          </div>
        </div>
        <p className="mt-8 text-sm text-gray-400">
          🏆 GoldenHead Team | KKB Agentic AI Hackathon 2025
        </p>
      </div>
    </div>
  )
}

function ReportsPage() {
  return (
    <div className="container px-4 py-12 mx-auto">
      <h1 className="text-2xl font-bold text-kkb-900 mb-4">Raporlar</h1>
      <p className="text-gray-600">Rapor listesi - Faz 4'te gelecek</p>
    </div>
  )
}

function ReportDetailPage() {
  return (
    <div className="container px-4 py-12 mx-auto">
      <h1 className="text-2xl font-bold text-kkb-900 mb-4">Rapor Detayı</h1>
      <p className="text-gray-600">Rapor detay sayfası - Faz 5'te gelecek</p>
    </div>
  )
}

function LiveReportPage() {
  return (
    <div className="container px-4 py-12 mx-auto">
      <h1 className="text-2xl font-bold text-kkb-900 mb-4">Canlı Rapor</h1>
      <p className="text-gray-600">Canlı rapor sayfası - Faz 6'da gelecek</p>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:id" element={<ReportDetailPage />} />
        <Route path="/reports/:id/live" element={<LiveReportPage />} />
      </Route>
    </Routes>
  )
}

export default App
