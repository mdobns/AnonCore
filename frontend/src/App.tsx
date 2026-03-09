import { useState } from 'react';
import { auth as authAPI } from './api';
import { useAuthStore } from './store/authStore';
import { useFeedStore } from './store/feedStore';
import { useNotificationStore } from './store/notificationStore';
import { useUIStore } from './store/uiStore';
import { AuthGate } from './components/AuthGate';
import { FeedPage } from './components/FeedPage';
import { Header } from './components/Header';
import { ToastContainer } from './components/Toast';
import { NotificationPanel } from './components/NotificationPanel';
import './styles.css';

export default function App() {
  const session = useAuthStore((s) => s.session);
  const setSession = useAuthStore((s) => s.setSession);
  const clearSession = useAuthStore((s) => s.clearSession);
  const clearFeed = useFeedStore((s) => s.setPosts);
  const clearNotif = useNotificationStore((s) => s.clear);
  const addToast = useUIStore((s) => s.addToast);
  const unread = useNotificationStore((s) => s.unread);

  const [notifOpen, setNotifOpen] = useState(false);

  async function handleLogout() {
    if (!session) return;
    try {
      await authAPI.logout(session.accessToken);
    } catch { /* ignore */ }
    clearSession();
    clearFeed([]);
    clearNotif();
    addToast('info', 'Session terminated. Identity wiped.');
  }

  async function handleRefreshIdentity() {
    if (!session) return;
    try {
      const resp = await authAPI.refresh(session.accessToken);
      setSession({
        persona: resp.session_alias,
        accessToken: resp.access_token,
        expiresAt: resp.expires_at,
      });
      addToast('success', `New identity: ${resp.session_alias}`);
    } catch (err: unknown) {
      const msg = (err as { detail?: string })?.detail ?? 'Refresh failed.';
      addToast('error', msg);
    }
  }

  return (
    <>
      {/* Decorative backgrounds */}
      <div className="bg-grid" />
      <div className="scanlines" />

      <div className="app-layout">
        {session && (
          <Header
            onLogout={handleLogout}
            onRefreshIdentity={handleRefreshIdentity}
            onToggleNotif={() => setNotifOpen((v) => !v)}
            unread={unread}
          />
        )}

        {session ? <FeedPage /> : <AuthGate />}
      </div>

      <NotificationPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
      <ToastContainer />
    </>
  );
}
