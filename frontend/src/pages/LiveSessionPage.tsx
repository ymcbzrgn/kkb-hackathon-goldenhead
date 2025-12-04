/**
 * Live Session Page
 * Canlı rapor işleme sayfası - Agent progress + Council UI
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Building2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/loading';
import {
  LiveIndicator,
  Timer,
  PhaseStepper,
  AgentProgress,
} from '@/components/live';
import { useReport } from '@/hooks/useReport';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgentStore } from '@/stores/agentStore';
import { useReportStore } from '@/stores/reportStore';
import { fadeInUp, staggerContainer } from '@/utils/animations';
import type { AgentProgress as AgentProgressType, AgentType } from '@/types';

type Phase = 'agents' | 'council' | 'completed' | 'failed';

export function LiveSessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [startTime] = useState(() => new Date());

  // Fetch report data
  const { data: report, isLoading: isLoadingReport } = useReport(id!);

  // Stores
  const { agents, reset: resetAgents } = useAgentStore();
  const { livePhase, wsError } = useReportStore();

  // Determine phase from store - map 'idle' to 'agents'
  const phase: Phase = livePhase === 'idle' ? 'agents' : livePhase;

  // WebSocket connection - hooks into stores automatically
  useWebSocket({
    reportId: id!,
    companyName: report?.company_name || '',
    onComplete: () => {
      // Redirect to report detail after delay
      setTimeout(() => {
        navigate(`/reports/${id}`);
      }, 2000);
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
  });

  // Reset agents on mount
  useEffect(() => {
    resetAgents();
  }, [resetAgents]);

  // Convert agents object to array for AgentProgress component
  const agentList: AgentProgressType[] = (Object.keys(agents) as AgentType[]).map(key => agents[key]);

  // If report is already completed, redirect
  useEffect(() => {
    if (report?.status === 'completed') {
      navigate(`/reports/${id}`);
    }
  }, [report, id, navigate]);

  if (isLoadingReport) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Spinner size="lg" />
          <p className="text-gray-500">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="p-8 text-center max-w-md">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Rapor Bulunamadı</h2>
          <p className="text-gray-500 mb-6">İstenen rapor mevcut değil.</p>
          <Link to="/reports">
            <Button variant="primary">Raporlara Dön</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-kkb-50 to-gray-50 py-8">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="container mx-auto px-4 max-w-4xl"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="mb-8">
          <Link
            to="/reports"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-kkb-700 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Raporlara Dön</span>
          </Link>

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-kkb-100 border border-kkb-200">
                <Building2 className="w-6 h-6 text-kkb-700" />
              </div>
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-kkb-900">
                  {report.company_name}
                </h1>
                <p className="text-sm text-gray-500">Canlı Rapor İşleme</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Timer startTime={startTime} isRunning={phase !== 'completed' && phase !== 'failed'} />
              <LiveIndicator isLive={phase !== 'completed' && phase !== 'failed'} />
            </div>
          </div>
        </motion.div>

        {/* Phase Stepper */}
        <motion.div variants={fadeInUp} className="mb-8">
          <PhaseStepper currentPhase={phase} />
        </motion.div>

        {/* Connection Status */}
        {wsError && (
          <motion.div
            variants={fadeInUp}
            className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg"
          >
            <p className="text-red-600 text-sm">
              ⚠️ Bağlantı hatası: {wsError}. Sayfa yenilemeyi deneyin.
            </p>
          </motion.div>
        )}

        {/* Main Content */}
        <motion.div variants={fadeInUp}>
          <Card className="p-6">
            {/* Agents Phase */}
            {phase === 'agents' && (
              <AgentProgress agents={agentList} />
            )}

            {/* Council Phase - Placeholder */}
            {phase === 'council' && (
              <div className="text-center py-12">
                <div className="w-20 h-20 rounded-full bg-kkb-100 flex items-center justify-center mx-auto mb-4">
                  <Spinner size="lg" />
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  Komite Toplantısı Başlıyor
                </h3>
                <p className="text-gray-500">
                  6 kişilik sanal kredi komitesi değerlendirme yapıyor...
                </p>
                <p className="text-sm text-gray-400 mt-4">
                  (Council UI - Faz 8'de eklenecek)
                </p>
              </div>
            )}

            {/* Completed Phase */}
            {phase === 'completed' && (
              <div className="text-center py-12">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200 }}
                  className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4"
                >
                  <span className="text-4xl">✓</span>
                </motion.div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  Rapor Tamamlandı!
                </h3>
                <p className="text-gray-500 mb-6">
                  Rapor detay sayfasına yönlendiriliyorsunuz...
                </p>
                <Link to={`/reports/${id}`}>
                  <Button variant="primary">Raporu Görüntüle</Button>
                </Link>
              </div>
            )}

            {/* Failed Phase */}
            {phase === 'failed' && (
              <div className="text-center py-12">
                <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                  <span className="text-4xl">✕</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  İşlem Başarısız
                </h3>
                <p className="text-gray-500 mb-6">
                  Rapor oluşturulurken bir hata oluştu.
                </p>
                <div className="flex items-center justify-center gap-3">
                  <Link to="/reports">
                    <Button variant="secondary">Raporlara Dön</Button>
                  </Link>
                  <Link to="/">
                    <Button variant="primary">Yeni Rapor Oluştur</Button>
                  </Link>
                </div>
              </div>
            )}
          </Card>
        </motion.div>
      </motion.div>
    </div>
  );
}
