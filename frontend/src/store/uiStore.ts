import { create } from 'zustand';

export type ToastKind = 'info' | 'success' | 'warning' | 'error';

export interface ToastEntry {
  id: string;
  kind: ToastKind;
  message: string;
  timeoutId?: ReturnType<typeof setTimeout>;
}

interface UIState {
  toasts: ToastEntry[];
  showComposer: boolean;
  isLoading: boolean;
  addToast: (kind: ToastKind, message: string) => void;
  removeToast: (id: string) => void;
  setShowComposer: (v: boolean) => void;
  setLoading: (v: boolean) => void;
}

let _seq = 0;

export const useUIStore = create<UIState>((set) => ({
  toasts: [],
  showComposer: false,
  isLoading: false,
  addToast: (kind, message) => {
    const id = String(++_seq);
    const timeoutId = setTimeout(
      () => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
      4000,
    );
    set((s) => ({ toasts: [...s.toasts, { id, kind, message, timeoutId }] }));
  },
  removeToast: (id) =>
    set((s) => {
      const toast = s.toasts.find((t) => t.id === id);
      if (toast?.timeoutId) clearTimeout(toast.timeoutId);
      return { toasts: s.toasts.filter((t) => t.id !== id) };
    }),
  setShowComposer: (showComposer) => set({ showComposer }),
  setLoading: (isLoading) => set({ isLoading }),
}));
