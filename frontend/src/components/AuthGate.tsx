import { useState } from 'react';
import { auth as authAPI } from '../api';
import { useAuthStore } from '../store/authStore';
import { useUIStore } from '../store/uiStore';

type Tab = 'login' | 'register';

export function AuthGate() {
  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const setSession = useAuthStore((s) => s.setSession);
  const addToast = useUIStore((s) => s.addToast);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setBusy(true);
    setError('');
    try {
      const resp = tab === 'login'
        ? await authAPI.login(email, password)
        : await authAPI.register(email, password);
      setSession({
        persona: resp.session_alias,
        accessToken: resp.access_token,
        expiresAt: resp.expires_at,
      });
      addToast('success', `Connected as ${resp.session_alias}`);
    } catch (err: unknown) {
      const msg = (err as { detail?: string })?.detail ?? (err as Error)?.message ?? 'Unknown error';
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  const switchTab = (t: Tab) => {
    setTab(t);
    setError('');
    setEmail('');
    setPassword('');
  };

  return (
    <main className="auth-page">
      {/* animated background decorations */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{
            position: 'absolute',
            borderRadius: '50%',
            border: `1px solid ${i % 2 ? 'rgba(0,245,255,0.06)' : 'rgba(168,85,247,0.06)'}`,
            width: `${200 + i * 140}px`,
            height: `${200 + i * 140}px`,
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }} />
        ))}
      </div>

      <div className="glass-card auth-panel">
        <div className="auth-logo">
          <h1 className="glitch text-cyan" data-text="ANONCORE">ANONCORE</h1>
          <p className="tagline text-muted">
            anonymous · ephemeral · real-time
          </p>
        </div>

        <div className="auth-tabs">
          <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => switchTab('login')}>
            &gt; Login
          </button>
          <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => switchTab('register')}>
            &gt; Register
          </button>
        </div>

        {error && (
          <div className="auth-error">
            <ErrorIcon />
            {error}
          </div>
        )}

        <form onSubmit={submit}>
          <div className="field-group">
            <label className="terminal-label">
              <span className="prompt">&gt;</span> Email
            </label>
            <input
              type="email"
              className={`terminal-input ${error ? 'error' : ''}`}
              placeholder="user@anon.local"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
              disabled={busy}
            />
          </div>

          <div className="field-group">
            <label className="terminal-label">
              <span className="prompt">&gt;</span> Password
            </label>
            <input
              type="password"
              className={`terminal-input ${error ? 'error' : ''}`}
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              disabled={busy}
            />
          </div>

          <button
            type="submit"
            className="btn btn-solid"
            style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: '13px', letterSpacing: '0.1em' }}
            disabled={busy}
          >
            {busy ? <span className="spinner" /> : null}
            {tab === 'login' ? 'ENTER THE VOID' : 'CREATE IDENTITY'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 11, color: 'var(--text-faint)', letterSpacing: '0.06em' }}>
          Your identity rotates on every login.
          <br />No profiles · No history · No traces.
        </p>
      </div>
    </main>
  );
}

function ErrorIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
