import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import type { Post } from '../types';
import { useFeedStore } from '../store/feedStore';
import { posts as postsAPI } from '../api';
import { useUIStore } from '../store/uiStore';
import { useAuthStore } from '../store/authStore';

interface PostCardProps {
  post: Post;
  isNew?: boolean;
}

export function PostCard({ post, isNew }: PostCardProps) {
  const setActivePostId = useFeedStore((s) => s.setActivePostId);
  const removePost = useFeedStore((s) => s.removePost);
  const addToast = useUIStore((s) => s.addToast);
  const session = useAuthStore((s) => s.session);
  const isAdmin = useAuthStore((s) => s.isAdmin);

  const isOwner = !!session && session.persona === post.session_alias;
  const canDelete = isAdmin || isOwner;

  const [busy, setBusy] = useState(false);

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(post.created_at), { addSuffix: true });
    } catch {
      return 'just now';
    }
  })();

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!session || busy) return;
    if (!window.confirm('Delete this post? This cannot be undone.')) return;
    setBusy(true);
    try {
      await postsAPI.deletePost(session.accessToken, post.id);
      removePost(post.id);
      addToast('info', 'Post deleted.');
    } catch (err: unknown) {
      addToast('error', (err as { detail?: string })?.detail ?? 'Could not delete post.');
    } finally {
      setBusy(false);
    }
  }

  async function handleReport(e: React.MouseEvent) {
    e.stopPropagation();
    if (!session) return;
    const reason = window.prompt('Reason for report:');
    if (!reason) return;
    try {
      await postsAPI.report(session.accessToken, reason, post.id);
      addToast('info', 'Report submitted.');
    } catch {
      addToast('error', 'Could not submit report.');
    }
  }

  return (
    <article
      className={`glass-card post-card ${isNew ? 'new-post' : ''}`}
      onClick={() => setActivePostId(post.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') setActivePostId(post.id); }}
    >
      <div className="post-meta">
        <span className="post-alias">{post.session_alias}</span>
        <time className="post-time" dateTime={post.created_at} title={post.created_at}>
          {timeAgo}
        </time>
      </div>

      <p className="post-content">{post.content}</p>

      <div className="post-footer">
        <button
          className="post-action"
          onClick={(e) => { e.stopPropagation(); setActivePostId(post.id); }}
        >
          <CommentIcon />
          {post.comment_count} {post.comment_count === 1 ? 'reply' : 'replies'}
        </button>

        <div className="post-actions-right" onClick={(e) => e.stopPropagation()}>
          <button
            className="post-action"
            title="Report this post"
            disabled={!session}
            onClick={handleReport}
          >
            <FlagIcon />
          </button>
          {canDelete && (
            <button
              className="post-action post-action-delete"
              title="Delete this post"
              disabled={busy}
              onClick={handleDelete}
            >
              {busy ? <span className="spinner" style={{ width: 11, height: 11 }} /> : <TrashIcon />}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function CommentIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function FlagIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </svg>
  );
}
function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  );
}
