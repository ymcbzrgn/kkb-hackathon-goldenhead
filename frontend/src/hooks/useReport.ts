/**
 * useReport Hook
 * Tek rapor detayı için React Query hook
 */

import { useQuery } from '@tanstack/react-query';
import { getReport } from '@/services/api';

export function useReport(id: string | undefined) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => getReport(id!),
    enabled: !!id,
    select: (response) => {
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error?.message || 'Rapor yüklenemedi');
    },
  });
}
