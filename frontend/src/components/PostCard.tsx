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
  const addToast = useUIStore((s) => s.addToast);
  const session = useAuthStore((s) => s.session);

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(post.created_at), { addSuffix: true });
    } catch {
      return 'just now';
    }
  })();

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
        <ReportButton postId={post.id} token={session?.accessToken} addToast={addToast} />
      </div>
    </article>
  );
}

function ReportButton({
  postId,
  token,
  addToast,
}: {
  postId: string;
  token?: string;
  addToast: (kind: 'info' | 'success' | 'warning' | 'error', msg: string) => void;
}) {
  return (
    <button
      className="post-action"
      style={{ marginLeft: 'auto' }}
      title="Report this post"
      onClick={async (e) => {
        e.stopPropagation();
        const reason = window.prompt('Reason for report:');
        if (!reason || !token) return;
        try {
          await postsAPI.report(token, reason, postId);
          addToast('info', 'Report submitted.');
        } catch {
          addToast('error', 'Could not submit report.');
        }
      }}
    >
      <FlagIcon />
    </button>
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
