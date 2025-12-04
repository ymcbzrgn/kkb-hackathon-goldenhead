/**
 * useDeleteReport Hook
 * Rapor silme için React Query mutation
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteReport } from '@/services/api';
import { useUIStore } from '@/stores/uiStore';

export function useDeleteReport() {
  const queryClient = useQueryClient();
  const addToast = useUIStore((state) => state.addToast);
  const closeDeleteModal = useUIStore((state) => state.closeDeleteModal);

  return useMutation({
    mutationFn: (id: string) => deleteReport(id),
    onSuccess: (response, id) => {
      if (response.success) {
        // Cache'i invalidate et
        queryClient.invalidateQueries({ queryKey: ['reports'] });
        queryClient.removeQueries({ queryKey: ['report', id] });
        
        // Modal'ı kapat
        closeDeleteModal();
        
        // Toast göster
        addToast({
          type: 'success',
          message: 'Rapor silindi',
        });
      } else {
        addToast({
          type: 'error',
          message: response.error?.message || 'Rapor silinemedi',
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
