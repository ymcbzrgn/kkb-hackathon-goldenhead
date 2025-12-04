/**
 * Reports Page
 * Tüm raporların listelendiği sayfa
 */

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FileText, Plus, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/loading';
import {
  ReportList,
  ReportFilters,
  Pagination,
  EmptyState,
  type FilterState,
} from '@/components/reports';
import { useReports } from '@/hooks/useReports';
import { useDeleteReport } from '@/hooks/useDeleteReport';
import { fadeInUp } from '@/utils/animations';
import type { ReportStatus } from '@/types';

export function ReportsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterState>({ status: 'all' });
  const [searchQuery, setSearchQuery] = useState('');

  // Build query params
  const queryParams = useMemo(() => {
    const params: { page: number; limit: number; status?: ReportStatus } = {
      page,
      limit: 9,
    };
    if (filters.status !== 'all') {
      params.status = filters.status;
    }
    return params;
  }, [page, filters]);

  const { data, isLoading, isError, refetch } = useReports(queryParams);
  const { mutate: deleteReport, isPending: isDeleting } = useDeleteReport();

  // Client-side search filter
  const filteredReports = useMemo(() => {
    if (!data?.items) return [];
    if (!searchQuery.trim()) return data.items;

    const query = searchQuery.toLowerCase();
    return data.items.filter((report) =>
      report.company_name.toLowerCase().includes(query)
    );
  }, [data?.items, searchQuery]);

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1); // Reset page on filter change
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Bu raporu silmek istediğinizden emin misiniz?')) {
      deleteReport(id);
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-kkb-700 to-kkb-900 flex items-center justify-center shadow-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-kkb-900">
                Raporlar
              </h1>
              <p className="text-gray-500 text-sm">
                Tüm firma istihbarat raporlarınız
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Yenile
            </Button>
            <Link to="/">
              <Button variant="primary" className="gap-2">
                <Plus className="w-4 h-4" />
                Yeni Rapor
              </Button>
            </Link>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          className="mb-6"
        >
          <ReportFilters
            onFilterChange={handleFilterChange}
            onSearch={handleSearch}
          />
        </motion.div>

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Spinner size="lg" />
            <p className="text-gray-500">Raporlar yükleniyor...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-20">
            <p className="text-red-500 mb-4">Raporlar yüklenirken hata oluştu.</p>
            <Button variant="secondary" onClick={() => refetch()}>
              Tekrar Dene
            </Button>
          </div>
        ) : filteredReports.length === 0 ? (
          <EmptyState
            title={searchQuery ? 'Sonuç bulunamadı' : 'Henüz rapor yok'}
            description={
              searchQuery
                ? `"${searchQuery}" için sonuç bulunamadı. Farklı bir arama deneyin.`
                : 'İlk raporunuzu oluşturmak için yukarıdaki butona tıklayın.'
            }
            showAction={!searchQuery}
          />
        ) : (
          <>
            {/* Report List */}
            <ReportList
              reports={filteredReports}
              onDelete={handleDelete}
            />

            {/* Pagination */}
            {data?.pagination && (
              <Pagination
                currentPage={data.pagination.page}
                totalPages={data.pagination.total_pages}
                totalItems={data.pagination.total_items}
                itemsPerPage={data.pagination.limit}
                onPageChange={handlePageChange}
              />
            )}
          </>
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
      </div>
    </div>
  );
}
