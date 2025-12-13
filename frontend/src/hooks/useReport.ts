/**
 * useReport Hook
 * Tek rapor detayı için React Query hook
 */

import { useQuery } from '@tanstack/react-query';
import { getReport } from '@/services/api';

export function useReport(id: string | undefined) {
  const query = useQuery({
    queryKey: ['report', id],
    queryFn: () => getReport(id!),
    enabled: !!id,
    staleTime: 0, // Her zaman güncel veri
    refetchOnMount: 'always',   // Her mount'ta kesinlikle yenile
    refetchOnWindowFocus: 'always', // Sekmeye donunce kesinlikle yenile
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error?.message || 'Rapor yüklenemedi');
    },
  });

  // Processing durumundayken otomatik yenile (5 saniyede bir)
  useQuery({
    queryKey: ['report-polling', id],
    queryFn: () => getReport(id!),
    enabled: !!id && query.data?.status === 'processing',
    refetchInterval: 5000, // 5 saniyede bir
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    },
  });

  return query;
}
