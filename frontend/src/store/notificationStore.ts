import { create } from 'zustand';
import type { Notification } from '../types';

const MAX_NOTIFICATIONS = 50;

interface NotificationState {
  notifications: Notification[];
  add: (n: Notification) => void;
  markRead: (id: string) => void;
  clear: () => void;
  unread: number;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unread: 0,
  add: (n) => {
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, MAX_NOTIFICATIONS),
      unread: s.unread + 1,
    }));
  },
  markRead: (id) => {
    set((s) => ({
      notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
      unread: Math.max(0, s.unread - 1),
    }));
  },
  clear: () => set({ notifications: [], unread: 0 }),
}));
