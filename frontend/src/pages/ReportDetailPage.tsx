/**
 * Report Detail Page
 * Tek bir raporun detaylı görünümü
 */

import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  Building2, 
  Calendar, 
  Clock, 
  Download, 
  Trash2, 
  Radio,
  FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/loading';
import { StatusBadge } from '@/components/reports';
import {
  FinalDecision,
  AgentResults,
  TranscriptAccordion,
} from '@/components/report-detail';
import { useReport } from '@/hooks/useReport';
import { transformAgentResults } from '@/utils/agentAdapter';
import { useDeleteReport } from '@/hooks/useDeleteReport';
import { fadeInUp, staggerContainer } from '@/utils/animations';
import { formatDate, formatDuration } from '@/utils/formatters';

export function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: report, isLoading, isError } = useReport(id!);
  const { mutate: deleteReport, isPending: isDeleting } = useDeleteReport();

  const handleDelete = () => {
    if (window.confirm('Bu raporu silmek istediğinizden emin misiniz?')) {
      deleteReport(id!, {
        onSuccess: () => navigate('/reports'),
      });
    }
  };

  const handleDownloadPdf = async () => {
    try {
      // API çağrısı
      const response = await fetch(`/api/reports/${id}/pdf`, {
        method: 'GET',
        headers: {
          'Accept': 'application/pdf',
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'PDF indirilemedi');
      }

      // PDF blob'unu al
      const blob = await response.blob();

      // Dosya adını response header'dan al
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'rapor.pdf';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Blob'u indir
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('PDF indirme hatası:', error);
      alert(error instanceof Error ? error.message : 'PDF indirilemedi');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Spinner size="lg" />
          <p className="text-gray-500">Rapor yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="p-8 text-center max-w-md">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Rapor Bulunamadı</h2>
          <p className="text-gray-500 mb-6">
            İstenen rapor mevcut değil veya silinmiş olabilir.
          </p>
          <Link to="/reports">
            <Button variant="primary">Raporlara Dön</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const isProcessing = report.status === 'processing';
  const isCompleted = report.status === 'completed';

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="container mx-auto px-4 max-w-6xl"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="mb-8">
          {/* Back Button */}
          <Link
            to="/reports"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-kkb-700 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Raporlara Dön</span>
          </Link>

          {/* Title & Actions */}
          <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl md:text-3xl font-bold text-kkb-900">
                  {report.company_name}
                </h1>
                <StatusBadge status={report.status} />
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                {report.company_tax_no && (
                  <span className="flex items-center gap-1.5">
                    <Building2 className="w-4 h-4" />
                    VKN: {report.company_tax_no}
                  </span>
                )}
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" />
                  {formatDate(report.created_at)}
                </span>
                {report.duration_seconds && (
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    {formatDuration(report.duration_seconds)}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {isProcessing && (
                <Link to={`/reports/${id}/live`}>
                  <Button variant="primary" className="gap-2">
                    <Radio className="w-4 h-4" />
                    Canlı İzle
                  </Button>
                </Link>
              )}
              {isCompleted && (
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={handleDownloadPdf}
                >
                  <Download className="w-4 h-4" />
                  PDF İndir
                </Button>
              )}
              <Button
                variant="ghost"
                className="gap-2 text-red-600 hover:bg-red-50"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                <Trash2 className="w-4 h-4" />
                Sil
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Processing State */}
        {isProcessing && (
          <motion.div variants={fadeInUp}>
            <Card className="p-8 text-center mb-8">
              <div className="w-16 h-16 rounded-full bg-kkb-100 flex items-center justify-center mx-auto mb-4">
                <Spinner size="lg" />
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Rapor Hazırlanıyor
              </h3>
              <p className="text-gray-500 mb-4">
                Ajanlar veri topluyor ve komite değerlendirmesi yapılıyor.
              </p>
              <Link to={`/reports/${id}/live`}>
                <Button variant="primary" className="gap-2">
                  <Radio className="w-4 h-4" />
                  Canlı Oturumu İzle
                </Button>
              </Link>
            </Card>
          </motion.div>
        )}

        {/* Completed Report Content */}
        {isCompleted && report.council_decision && (
          <>
            {/* Final Decision */}
            <motion.div variants={fadeInUp} className="mb-8">
              <FinalDecision
                decision={report.council_decision.decision}
                score={report.council_decision.final_score}
                riskLevel={report.council_decision.risk_level}
                consensus={report.council_decision.consensus}
                conditions={report.council_decision.conditions}
                dissentNote={report.council_decision.dissent_note}
              />
            </motion.div>

            {/* Agent Results */}
            <motion.div variants={fadeInUp} className="mb-8">
              <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-kkb-600" />
                Ajan Bulguları
              </h2>
              <AgentResults results={transformAgentResults(report.agent_results)} />
            </motion.div>

            {/* Transcript */}
            <motion.div variants={fadeInUp}>
              <TranscriptAccordion transcript={report.council_decision.transcript} />
            </motion.div>
          </>
        )}

        {/* Failed State */}
        {report.status === 'failed' && (
          <motion.div variants={fadeInUp}>
            <Card className="p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-red-500" />
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Rapor Oluşturulamadı
              </h3>
              <p className="text-gray-500 mb-4">
                Rapor hazırlanırken bir hata oluştu. Lütfen tekrar deneyin.
              </p>
              <Link to="/">
                <Button variant="primary">Yeni Rapor Oluştur</Button>
              </Link>
            </Card>
          </motion.div>
        )}

        {/* Pending State */}
        {report.status === 'pending' && (
          <motion.div variants={fadeInUp}>
            <Card className="p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-4">
                <Clock className="w-8 h-8 text-amber-500" />
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Rapor Beklemede
              </h3>
              <p className="text-gray-500">
                Rapor kuyruğa alındı ve en kısa sürede işlenecek.
              </p>
            </Card>
          </motion.div>
        )}

        {/* Deleting overlay */}
        {isDeleting && (
          <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl flex flex-col items-center gap-3">
              <Spinner size="md" />
              <p className="text-gray-600">Rapor siliniyor...</p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
