/**
 * useCreateReport Hook
 * Yeni rapor oluşturma için React Query mutation
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { createReport } from '@/services/api';
import { useUIStore } from '@/stores/uiStore';
import type { CreateReportRequest } from '@/types';

export function useCreateReport() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const addToast = useUIStore((state) => state.addToast);

  return useMutation({
    mutationFn: (request: CreateReportRequest) => createReport(request),
    onSuccess: (response) => {
      if (response.success && response.data) {
        // Cache'i invalidate et
        queryClient.invalidateQueries({ queryKey: ['reports'] });
        
        // Toast göster
        addToast({
          type: 'success',
          message: 'Rapor oluşturuldu, analiz başlıyor...',
        });

        // Live sayfasına yönlendir
        navigate(`/reports/${response.data.report_id}/live`);
      } else {
        addToast({
          type: 'error',
          message: response.error?.message || 'Rapor oluşturulamadı',
        });
      }
    },
    onError: (error) => {
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Bir hata oluştu',
      });
    },
  });
}
