import { useAuthStore } from '../store/authStore';

export function Sidebar({ postCount }: { postCount: number }) {
  const session = useAuthStore((s) => s.session);
  const persona = session?.persona ?? '–';

  return (
    <aside>
      {/* Identity widget */}
      <div className="glass-card sidebar-widget">
        <div className="widget-title">Session Identity</div>
        <div style={{ textAlign: 'center', padding: '12px 0' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 56,
            height: 56,
            borderRadius: '50%',
            background: 'var(--purple-dim)',
            border: '2px solid rgba(168,85,247,0.35)',
            fontSize: 22,
            marginBottom: 12,
          }}>
            {persona.charAt(0)}
          </div>
          <div style={{ fontWeight: 600, color: 'var(--purple)', fontSize: 13, marginBottom: 4 }}>
            {persona}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-faint)', letterSpacing: '0.1em' }}>
            TRANSIENT · SESSION BOUND
          </div>
        </div>
      </div>

      {/* Stats widget */}
      <div className="glass-card sidebar-widget">
        <div className="widget-title">Feed Stats</div>
        <div className="stat-row">
          <span className="stat-label">Posts visible</span>
          <span className="stat-value">{postCount}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Status</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--green)', fontSize: 11 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
            Live
          </span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Broadcast</span>
          <span className="stat-value">Global</span>
        </div>
      </div>

      {/* Info widget */}
      <div className="glass-card sidebar-widget">
        <div className="widget-title">Ghost Protocol</div>
        <p style={{ fontSize: 11, color: 'var(--text-faint)', lineHeight: 1.7 }}>
          Your identity rotates on every login. Posts persist, identities don't.
          No cross-session linking possible.
        </p>
      </div>
    </aside>
  );
}
