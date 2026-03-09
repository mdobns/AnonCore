import { motion, AnimatePresence } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import { useNotificationStore } from '../store/notificationStore';

interface NotificationPanelProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationPanel({ open, onClose }: NotificationPanelProps) {
  const { notifications, markRead, clear, unread } = useNotificationStore();

  return (
    <AnimatePresence>
      {open && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 80 }}
            onClick={onClose}
          />
          <motion.div
            style={{
              position: 'fixed',
              top: 64,
              right: 16,
              zIndex: 90,
              width: 340,
              maxHeight: 'calc(100vh - 100px)',
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
              backdropFilter: 'blur(16px)',
              overflow: 'hidden',
            }}
            initial={{ y: -12, opacity: 0, scale: 0.96 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: -12, opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0.34, 1.56, 0.64, 1] }}
          >
            {/* Panel header */}
            <div style={{
              padding: '14px 18px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--cyan)' }}>
                NOTIFICATIONS
                {unread > 0 && (
                  <span style={{ marginLeft: 8, background: 'var(--pink)', color: '#fff', fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 10 }}>
                    {unread}
                  </span>
                )}
              </span>
              {notifications.length > 0 && (
                <button className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 10 }} onClick={clear}>
                  Clear
                </button>
              )}
            </div>

            {/* Notification list */}
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {notifications.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-faint)', fontSize: 12 }}>
                  No notifications yet.
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => markRead(n.id)}
                    style={{
                      padding: '12px 18px',
                      borderBottom: '1px solid rgba(255,255,255,0.04)',
                      cursor: 'pointer',
                      background: n.read ? 'transparent' : 'rgba(0,245,255,0.04)',
                      transition: 'background 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: n.read ? 'var(--text-muted)' : 'var(--text)' }}>
                        {n.message}
                      </span>
                      {!n.read && (
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--cyan)', boxShadow: '0 0 6px var(--cyan)', flexShrink: 0, marginTop: 4 }} />
                      )}
                    </div>
                    <time style={{ fontSize: 10, color: 'var(--text-faint)' }}>
                      {formatDistanceToNowSafe(n.created_at)}
                    </time>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function formatDistanceToNowSafe(dateStr: string) {
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
  } catch {
    return '';
  }
}
