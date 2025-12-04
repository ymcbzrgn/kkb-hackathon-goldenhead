import { Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout'
import { LandingPage, ReportsPage, ReportDetailPage } from '@/pages'

function LiveReportPage() {
  return (
    <div className="container px-4 py-12 mx-auto">
      <h1 className="text-2xl font-bold text-kkb-900 mb-4">Canlı Rapor</h1>
      <p className="text-gray-600">Canlı rapor sayfası - Faz 7'de gelecek</p>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:id" element={<ReportDetailPage />} />
        <Route path="/reports/:id/live" element={<LiveReportPage />} />
      </Route>
    </Routes>
  )
}

export default App
