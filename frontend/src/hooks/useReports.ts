/**
 * useReports Hook
 * Rapor listesi için React Query hook
 */

import { useQuery } from '@tanstack/react-query';
import { getReports } from '@/services/api';
import type { ApiResponse, PaginatedResponse, ReportListItem, ReportsQueryParams } from '@/types';

export function useReports(params?: ReportsQueryParams) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => getReports(params),
    staleTime: 0, // Her zaman güncel veri
    refetchOnMount: 'always',
    refetchOnWindowFocus: 'always',
    refetchInterval: (query) => {
      // Processing rapor varsa 10 saniyede bir yenile
      const items = (query.state.data as ApiResponse<PaginatedResponse<ReportListItem>> | undefined)?.data?.items ?? [];
      const hasProcessing = items.some((r) => r.status === 'processing');
      return hasProcessing ? 10000 : false;
    },
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error?.message || 'Raporlar yüklenemedi');
    },
  });
}
