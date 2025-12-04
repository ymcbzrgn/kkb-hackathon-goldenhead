/**
 * UI Store
 * Global UI state yönetimi (modals, notifications, etc.)
 */

import { create } from 'zustand';

// ==================== Types ====================

interface ModalState {
  isOpen: boolean;
  title?: string;
  content?: React.ReactNode;
  onConfirm?: () => void;
  onCancel?: () => void;
}

interface ToastState {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface UIState {
  // Modal
  modal: ModalState;
  openModal: (modal: Omit<ModalState, 'isOpen'>) => void;
  closeModal: () => void;

  // Delete confirmation modal
  deleteModal: {
    isOpen: boolean;
    reportId: string | null;
    companyName: string | null;
  };
  openDeleteModal: (reportId: string, companyName: string) => void;
  closeDeleteModal: () => void;

  // Toasts
  toasts: ToastState[];
  addToast: (toast: Omit<ToastState, 'id'>) => void;
  removeToast: (id: string) => void;

  // Sidebar (mobile)
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  closeSidebar: () => void;
}

// ==================== Store ====================

export const useUIStore = create<UIState>((set) => ({
  // Modal
  modal: { isOpen: false },
  openModal: (modal) => set({ modal: { ...modal, isOpen: true } }),
  closeModal: () => set({ modal: { isOpen: false } }),

  // Delete Modal
  deleteModal: { isOpen: false, reportId: null, companyName: null },
  openDeleteModal: (reportId, companyName) =>
    set({ deleteModal: { isOpen: true, reportId, companyName } }),
  closeDeleteModal: () =>
    set({ deleteModal: { isOpen: false, reportId: null, companyName: null } }),

  // Toasts
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [
        ...state.toasts,
        { ...toast, id: `toast-${Date.now()}-${Math.random()}` },
      ],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  // Sidebar
  isSidebarOpen: false,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  closeSidebar: () => set({ isSidebarOpen: false }),
}));
