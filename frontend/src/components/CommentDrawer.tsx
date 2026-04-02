import { useEffect, useRef, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AnimatePresence, motion } from 'framer-motion';
import { posts as postsAPI } from '../api';
import { useAuthStore } from '../store/authStore';
import { useFeedStore } from '../store/feedStore';
import { useUIStore } from '../store/uiStore';
import type { Comment } from '../types';

export function CommentDrawer() {
  const session = useAuthStore((s) => s.session);
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const {
    posts, comments, activePostId, setActivePostId,
    setComments, appendComment, incrementCommentCount,
    removeComment, decrementCommentCount,
  } = useFeedStore();
  const addToast = useUIStore((s) => s.addToast);

  const post = posts.find((p) => p.id === activePostId);
  const postComments: Comment[] = activePostId ? (comments[activePostId] ?? []) : [];

  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activePostId || !session) return;
    setLoading(true);
    postsAPI.comments(session.accessToken, activePostId)
      .then((c) => setComments(activePostId, c))
      .catch(() => addToast('error', 'Could not load comments.'))
      .finally(() => setLoading(false));
    setText('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePostId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [postComments.length]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || !session || !activePostId) return;
    setBusy(true);
    try {
      const comment = await postsAPI.addComment(session.accessToken, activePostId, text.trim());
      appendComment(comment);
      incrementCommentCount(activePostId);
      setText('');
    } catch (err: unknown) {
      const msg = (err as { detail?: string })?.detail ?? 'Could not post comment.';
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

  async function handleDeleteComment(comment: Comment) {
    if (!session || !activePostId) return;
    if (!window.confirm('Delete this comment? This cannot be undone.')) return;
    try {
      await postsAPI.deleteComment(session.accessToken, activePostId, comment.id);
      removeComment(activePostId, comment.id);
      decrementCommentCount(activePostId);
      addToast('info', 'Comment deleted.');
    } catch (err: unknown) {
      addToast('error', (err as { detail?: string })?.detail ?? 'Could not delete comment.');
    }
  }

  async function handleReportComment(comment: Comment) {
    if (!session) return;
    const reason = window.prompt('Reason for report:');
    if (!reason) return;
    try {
      await postsAPI.report(session.accessToken, reason, undefined, comment.id);
      addToast('info', 'Report submitted.');
    } catch {
      addToast('error', 'Could not submit report.');
    }
  }

  return (
    <AnimatePresence>
      {activePostId && post && (
        <div className="drawer-overlay" onClick={() => setActivePostId(null)}>
          <motion.aside
            className="drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 340, damping: 38 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="drawer-header">
              <h3>Thread</h3>
              <button className="btn btn-ghost btn-icon" onClick={() => setActivePostId(null)}>
                <CloseIcon />
              </button>
            </div>

            {/* Original post */}
            <div className="drawer-post">
              <div className="post-alias" style={{ fontSize: 12, marginBottom: 8 }}>
                {post.session_alias}
              </div>
              <p className="post-content" style={{ fontSize: 13 }}>{post.content}</p>
            </div>

            {/* Comments */}
            <div className="drawer-comments">
              {loading && (
                <div style={{ textAlign: 'center', padding: 24 }}>
                  <span className="spinner" />
                </div>
              )}
              {!loading && postComments.length === 0 && (
                <div className="empty-comments">
                  &gt; no replies yet — be the first
                </div>
              )}
              {postComments.map((c) => {
                const isOwner = !!session && session.persona === c.session_alias;
                const canDelete = isAdmin || isOwner;
                return (
                  <motion.div
                    key={c.id}
                    className="comment-item"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="comment-meta">
                      <span className="comment-alias">{c.session_alias}</span>
                      <time className="comment-time">
                        {formatDistanceToNowSafe(c.created_at)}
                      </time>
                      <div className="comment-actions">
                        <button
                          className="comment-action-btn"
                          title="Report comment"
                          disabled={!session}
                          onClick={() => handleReportComment(c)}
                        >
                          <FlagIcon />
                        </button>
                        {canDelete && (
                          <button
                            className="comment-action-btn comment-action-delete"
                            title="Delete comment"
                            onClick={() => handleDeleteComment(c)}
                          >
                            <TrashIcon />
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="comment-content">{c.content}</p>
                  </motion.div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            {/* Comment composer */}
            <div className="comment-composer">
              <form onSubmit={submit}>
                <textarea
                  placeholder="Reply anonymously… (Ctrl+Enter)"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={handleKey}
                  disabled={busy}
                />
                <div className="comment-composer-row">
                  <button className="btn btn-cyan" type="submit" disabled={busy || !text.trim()}>
                    {busy ? <span className="spinner" /> : <SendIcon />}
                    Reply
                  </button>
                </div>
              </form>
            </div>
          </motion.aside>
        </div>
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

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
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
function FlagIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </svg>
  );
}
function TrashIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  );
}
