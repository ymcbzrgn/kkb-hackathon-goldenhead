/**
 * useReports Hook
 * Rapor listesi için React Query hook
 */

import { useQuery } from '@tanstack/react-query';
import { getReports } from '@/services/api';
import type { ReportsQueryParams } from '@/types';

export function useReports(params?: ReportsQueryParams) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => getReports(params),
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error?.message || 'Raporlar yüklenemedi');
    },
  });
}
