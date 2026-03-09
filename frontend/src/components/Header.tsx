import { useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';

/** Renders a typewriter effect for the given text, re-animating on change. */
export function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    setDisplayed('');
    let i = 0;
    const id = setInterval(() => {
      if (i >= text.length) { clearInterval(id); return; }
      setDisplayed(text.slice(0, ++i));
    }, 42);
    return () => clearInterval(id);
  }, [text]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && <span className="typewriter-cursor" />}
    </span>
  );
}

/** Top navigation bar. */
export function Header({
  onRefreshIdentity,
  onLogout,
  onToggleNotif,
  unread,
}: {
  onRefreshIdentity: () => void;
  onLogout: () => void;
  onToggleNotif: () => void;
  unread: number;
}) {
  const session = useAuthStore((s) => s.session);

  return (
    <header className="header">
      <div className="header-logo">
        <LogoIcon />
        <span>ANON<span style={{ color: 'var(--purple)' }}>CORE</span></span>
      </div>

      {session && (
        <div className="header-persona">
          <span style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            IDENTITY
          </span>
          <div className="persona-badge">
            <span className="persona-dot" />
            <TypewriterText text={session.persona} />
          </div>
        </div>
      )}

      {session && (
        <div className="header-actions">
          <button className="notif-badge btn btn-ghost btn-icon" onClick={onToggleNotif} title="Notifications">
            <BellIcon />
            {unread > 0 && <span className="badge">{unread > 9 ? '9+' : unread}</span>}
          </button>
          <button className="btn btn-purple" onClick={onRefreshIdentity} title="Rotate identity">
            <RotateIcon /> Rotate
          </button>
          <button className="btn btn-danger" onClick={onLogout}>
            <PowerIcon /> Logout
          </button>
        </div>
      )}
    </header>
  );
}

// ─── Inline SVG icons ─────────────────────────────────────────────────────────
function LogoIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 2" />
      <circle cx="12" cy="12" r="4" fill="rgba(0,245,255,0.2)" stroke="currentColor" strokeWidth="1" />
      <path d="M12 8v4l2.5 2.5" stroke="var(--purple)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function BellIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}
function RotateIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  );
}
function PowerIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
      <line x1="12" y1="2" x2="12" y2="12" />
    </svg>
  );
}
