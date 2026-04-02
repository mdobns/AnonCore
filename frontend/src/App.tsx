import { useState, useEffect } from 'react';
import { auth as authAPI, admin as adminAPI } from './api';
import { useAuthStore } from './store/authStore';
import { useFeedStore } from './store/feedStore';
import { useNotificationStore } from './store/notificationStore';
import { useUIStore } from './store/uiStore';
import { AuthGate } from './components/AuthGate';
import { FeedPage } from './components/FeedPage';
import { Header } from './components/Header';
import { AdminPage } from './components/AdminPage';
import { ToastContainer } from './components/Toast';
import { NotificationPanel } from './components/NotificationPanel';
import './styles.css';

export default function App() {
  const session = useAuthStore((s) => s.session);
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const setSession = useAuthStore((s) => s.setSession);
  const setIsAdmin = useAuthStore((s) => s.setIsAdmin);
  const clearSession = useAuthStore((s) => s.clearSession);
  const clearFeed = useFeedStore((s) => s.setPosts);
  const clearNotif = useNotificationStore((s) => s.clear);
  const addToast = useUIStore((s) => s.addToast);
  const unread = useNotificationStore((s) => s.unread);

  const [notifOpen, setNotifOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);

  // Detect admin status whenever session changes
  useEffect(() => {
    if (!session) { setIsAdmin(false); return; }
    adminAPI.listUsers(session.accessToken)
      .then(() => setIsAdmin(true))
      .catch(() => setIsAdmin(false));
  }, [session?.accessToken, setIsAdmin]);

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
            onToggleAdmin={() => setAdminOpen((v) => !v)}
            unread={unread}
            isAdmin={isAdmin}
          />
        )}

        {session ? <FeedPage /> : <AuthGate />}
      </div>

      <NotificationPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
      {adminOpen && <AdminPage onClose={() => setAdminOpen(false)} />}
      <ToastContainer />
    </>
  );
}
