import { Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout'
import { LandingPage, ReportsPage, ReportDetailPage, LiveSessionPage } from '@/pages'

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:id" element={<ReportDetailPage />} />
        <Route path="/reports/:id/live" element={<LiveSessionPage />} />
      </Route>
    </Routes>
  )
}

export default App
