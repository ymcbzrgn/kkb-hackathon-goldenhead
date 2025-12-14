/**
 * useReport Hook
 * Tek rapor detayı için React Query hook
 *
 * Processing durumunda 5 saniyede bir otomatik yenilenir
 */

import { useQuery } from '@tanstack/react-query';
import { getReport } from '@/services/api';
import type { ApiResponse, ReportDetail } from '@/types';

export function useReport(id: string | undefined) {
  const query = useQuery({
    queryKey: ['report', id],
    queryFn: () => getReport(id!),
    enabled: !!id,
    staleTime: 0, // Her zaman güncel veri
    refetchOnMount: 'always',   // Her mount'ta kesinlikle yenile
    refetchOnWindowFocus: 'always', // Sekmeye donunce kesinlikle yenile
    // Processing durumunda 5 saniyede bir yenile (agent yüzdeleri için)
    refetchInterval: (query) => {
      const status = (query.state.data as ApiResponse<ReportDetail> | undefined)?.data?.status;
      // Processing veya pending durumunda 5 saniyede bir yenile
      if (status === 'processing' || status === 'pending') {
        return 5000; // 5 saniye
      }
      return false; // Completed/failed durumunda polling durdur
    },
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error?.message || 'Rapor yüklenemedi');
    },
  });

  return query;
}
