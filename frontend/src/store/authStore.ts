import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session } from '../types';

interface AuthState {
  session: Session | null;
  isAdmin: boolean;
  setSession: (s: Session | null) => void;
  setIsAdmin: (v: boolean) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      session: null,
      isAdmin: false,
      setSession: (session) => set({ session }),
      setIsAdmin: (isAdmin) => set({ isAdmin }),
      clearSession: () => set({ session: null, isAdmin: false }),
    }),
    { name: 'anon-auth' },
  ),
);
