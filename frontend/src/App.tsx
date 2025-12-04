import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { MainLayout } from '@/components/layout'
import { LandingPage, ReportsPage, ReportDetailPage, LiveSessionPage } from '@/pages'

// Scroll to top on route change
function ScrollToTop() {
  const { pathname } = useLocation()
  
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  
  return null
}

function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/:id" element={<ReportDetailPage />} />
          <Route path="/reports/:id/live" element={<LiveSessionPage />} />
        </Route>
      </Routes>
    </>
  )
}

export default App
