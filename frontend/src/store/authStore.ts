import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session } from '../types';

interface AuthState {
  session: Session | null;
  setSession: (s: Session | null) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      session: null,
      setSession: (session) => set({ session }),
      clearSession: () => set({ session: null }),
    }),
    { name: 'anon-auth' },
  ),
);
