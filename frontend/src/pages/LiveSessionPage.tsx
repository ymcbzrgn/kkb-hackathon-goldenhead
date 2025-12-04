/**
 * Live Session Page
 * Canlı rapor işleme sayfası - Agent progress + Council UI
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Building2, Clock, FileText, Gavel, Newspaper, CheckCircle, Loader2 } from 'lucide-react';
import { useReport } from '@/hooks/useReport';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgentStore } from '@/stores/agentStore';
import { useReportStore } from '@/stores/reportStore';
import { CouncilContainer } from '@/components/council';

export function LiveSessionPage() {
  const { id } = useParams<{ id: string }>();
  const [elapsedTime, setElapsedTime] = useState(0);
  
  // Report data
  const { data: report, isLoading } = useReport(id!);
  
  // Store state - shallow compare ile
  const agents = useAgentStore((s) => s.agents);
  const livePhase = useReportStore((s) => s.livePhase);
  const wsError = useReportStore((s) => s.wsError);

  // Phase mapping
  const phase = livePhase === 'idle' ? 'agents' : livePhase;

  // Timer
  useEffect(() => {
    if (phase === 'completed' || phase === 'failed') return;
    
    const interval = setInterval(() => {
      setElapsedTime((t) => t + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [phase]);

  // WebSocket - sadece report yüklendikten sonra
  useWebSocket({
    reportId: id || '',
    companyName: report?.company_name || '',
    enabled: !!report && report.status !== 'completed',
  });

  // Format time
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-kkb-600" />
          <span className="text-gray-600">Yükleniyor...</span>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center max-w-md">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Rapor Bulunamadı</h2>
          <p className="text-gray-500 mb-6">İstenen rapor mevcut değil.</p>
          <Link to="/reports" className="inline-block px-6 py-2 bg-kkb-600 text-white rounded-lg hover:bg-kkb-700">
            Raporlara Dön
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-kkb-50 to-gray-100 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        
        {/* Back Link */}
        <Link to="/reports" className="inline-flex items-center gap-2 text-gray-500 hover:text-kkb-700 mb-6">
          <ArrowLeft className="w-4 h-4" />
          <span>Raporlara Dön</span>
        </Link>

        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-kkb-100">
                <Building2 className="w-6 h-6 text-kkb-700" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{report.company_name}</h1>
                <p className="text-sm text-gray-500">Canlı Rapor İşleme</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Timer */}
              <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
                <Clock className="w-4 h-4 text-gray-500" />
                <span className="font-mono text-gray-700">{formatTime(elapsedTime)}</span>
              </div>
              
              {/* Live Badge */}
              {phase !== 'completed' && phase !== 'failed' && (
                <div className="flex items-center gap-2 px-4 py-2 bg-red-50 rounded-lg">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  <span className="text-red-600 font-medium text-sm">CANLI</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Phase Indicator */}
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className={`flex-1 text-center ${phase === 'agents' ? 'text-kkb-600' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center ${phase === 'agents' ? 'bg-kkb-100 border-2 border-kkb-500' : 'bg-gray-100'}`}>
                1
              </div>
              <span className="text-sm font-medium">Veri Toplama</span>
            </div>
            <div className="flex-1 h-1 bg-gray-200 mx-2" />
            <div className={`flex-1 text-center ${phase === 'council' ? 'text-kkb-600' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center ${phase === 'council' ? 'bg-kkb-100 border-2 border-kkb-500' : 'bg-gray-100'}`}>
                2
              </div>
              <span className="text-sm font-medium">Komite</span>
            </div>
            <div className="flex-1 h-1 bg-gray-200 mx-2" />
            <div className={`flex-1 text-center ${phase === 'completed' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center ${phase === 'completed' ? 'bg-green-100 border-2 border-green-500' : 'bg-gray-100'}`}>
                ✓
              </div>
              <span className="text-sm font-medium">Tamamlandı</span>
            </div>
          </div>
        </div>

        {/* Error */}
        {wsError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <p className="text-red-600 text-sm">⚠️ Bağlantı hatası: {wsError}</p>
          </div>
        )}

        {/* Agent Cards */}
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Veri Toplama Aşaması</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* TSG Agent */}
            <div className="border-2 border-blue-200 bg-blue-50 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <span className="font-semibold text-blue-700">TSG Agent</span>
              </div>
              <div className="h-2 bg-blue-100 rounded-full overflow-hidden mb-2">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${agents.tsg_agent?.progress || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-blue-600">
                  {agents.tsg_agent?.status === 'completed' ? (
                    <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Tamamlandı</span>
                  ) : agents.tsg_agent?.status === 'running' ? (
                    <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" /> Çalışıyor</span>
                  ) : (
                    'Bekliyor'
                  )}
                </span>
                <span className="text-blue-500">{agents.tsg_agent?.progress || 0}%</span>
              </div>
            </div>

            {/* İhale Agent */}
            <div className="border-2 border-purple-200 bg-purple-50 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Gavel className="w-5 h-5 text-purple-600" />
                </div>
                <span className="font-semibold text-purple-700">İhale Agent</span>
              </div>
              <div className="h-2 bg-purple-100 rounded-full overflow-hidden mb-2">
                <div 
                  className="h-full bg-purple-500 transition-all duration-300"
                  style={{ width: `${agents.ihale_agent?.progress || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-purple-600">
                  {agents.ihale_agent?.status === 'completed' ? (
                    <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Tamamlandı</span>
                  ) : agents.ihale_agent?.status === 'running' ? (
                    <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" /> Çalışıyor</span>
                  ) : (
                    'Bekliyor'
                  )}
                </span>
                <span className="text-purple-500">{agents.ihale_agent?.progress || 0}%</span>
              </div>
            </div>

            {/* News Agent */}
            <div className="border-2 border-amber-200 bg-amber-50 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <Newspaper className="w-5 h-5 text-amber-600" />
                </div>
                <span className="font-semibold text-amber-700">News Agent</span>
              </div>
              <div className="h-2 bg-amber-100 rounded-full overflow-hidden mb-2">
                <div 
                  className="h-full bg-amber-500 transition-all duration-300"
                  style={{ width: `${agents.news_agent?.progress || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-amber-600">
                  {agents.news_agent?.status === 'completed' ? (
                    <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Tamamlandı</span>
                  ) : agents.news_agent?.status === 'running' ? (
                    <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" /> Çalışıyor</span>
                  ) : (
                    'Bekliyor'
                  )}
                </span>
                <span className="text-amber-500">{agents.news_agent?.progress || 0}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Council Phase Placeholder */}
        {phase === 'council' && (
          <CouncilContainer />
        )}

        {/* Completed */}
        {phase === 'completed' && (
          <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">Rapor Tamamlandı!</h3>
            <p className="text-gray-500 mb-6">Rapor hazır, detayları görüntüleyebilirsiniz.</p>
            <Link 
              to={`/reports/${id}`}
              className="inline-block px-6 py-3 bg-kkb-600 text-white rounded-lg hover:bg-kkb-700 font-medium"
            >
              Raporu Görüntüle
            </Link>
          </div>
        )}

      </div>
    </div>
  );
}
