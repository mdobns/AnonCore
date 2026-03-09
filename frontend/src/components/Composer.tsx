import { useState } from 'react';
import { posts as postsAPI } from '../api';
import { useAuthStore } from '../store/authStore';
import { useFeedStore } from '../store/feedStore';
import { useUIStore } from '../store/uiStore';
import type { Post } from '../types';

const MAX_CHARS = 500;

export function Composer() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const session = useAuthStore((s) => s.session);
  const prependPost = useFeedStore((s) => s.prependPost);
  const addToast = useUIStore((s) => s.addToast);

  const remaining = MAX_CHARS - text.length;
  const countClass = remaining < 50 ? (remaining < 0 ? 'over' : 'warn') : '';

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const content = text.trim();
    if (!content || !session || busy) return;
    if (content.length > MAX_CHARS) { addToast('warning', 'Message too long.'); return; }
    setBusy(true);
    try {
      const post: Post = await postsAPI.create(session.accessToken, content);
      prependPost({ ...post, _new: true });
      setText('');
    } catch (err: unknown) {
      const msg = (err as { detail?: string })?.detail ?? (err as Error)?.message ?? 'Post failed';
      if ((err as { status?: number })?.status === 403) {
        addToast('warning', `⚠ ${msg}`);
      } else {
        addToast('error', msg);
      }
    } finally {
      setBusy(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div className="glass-card composer">
      <div className="composer-header">
        <span className="composer-title">
          <span>&gt; </span>NEW TRANSMISSION
        </span>
        <span className="text-faint" style={{ fontSize: 10, letterSpacing: '0.1em' }}>
          {session?.persona ?? ''}
        </span>
      </div>
      <form onSubmit={submit}>
        <textarea
          placeholder="Speak into the void…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={busy}
          maxLength={MAX_CHARS + 50}
        />
        <div className="composer-footer">
          <span className="composer-hint">Ctrl+Enter to send · anonymous by default</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className={`char-count ${countClass}`}>{remaining}</span>
            <button
              type="submit"
              className="btn btn-cyan"
              disabled={busy || !text.trim() || remaining < 0}
            >
              {busy ? <span className="spinner" /> : <SendIcon />}
              Transmit
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}
