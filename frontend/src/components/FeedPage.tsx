import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { posts as postsAPI, createFeedSocket } from '../api';
import { useAuthStore } from '../store/authStore';
import { useFeedStore } from '../store/feedStore';
import { useNotificationStore } from '../store/notificationStore';
import { useUIStore } from '../store/uiStore';
import { Composer } from './Composer';
import { PostCard } from './PostCard';
import { CommentDrawer } from './CommentDrawer';
import { Sidebar } from './Sidebar';
import type { StreamEvent, Post, Comment } from '../types';

export function FeedPage() {
  const session = useAuthStore((s) => s.session);
  const { posts, setPosts, prependPost, appendComment, incrementCommentCount } = useFeedStore();
  const addNotification = useNotificationStore((s) => s.add);
  const addToast = useUIStore((s) => s.addToast);

  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [newPostIds, setNewPostIds] = useState<Set<string>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);

  // ── initial feed load ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!session) return;
    setLoading(true);
    postsAPI.feed(session.accessToken)
      .then(setPosts)
      .catch(() => addToast('error', 'Could not load feed.'))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.accessToken]);

  // ── WebSocket real-time stream ────────────────────────────────────────────
  useEffect(() => {
    if (!session) return;
    const currentSession = session; // capture for closure
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let closed = false;

    function connect() {
      if (closed) return;
      const ws = createFeedSocket(currentSession.accessToken, (data) => {
        const event = data as StreamEvent;
        if (event.type === 'NEW_POST') {
          const post = event.data as Post;
          prependPost(post);
          setNewPostIds((prev) => { const s = new Set(prev); s.add(post.id); return s; });
          setTimeout(() => setNewPostIds((prev) => { const s = new Set(prev); s.delete(post.id); return s; }), 2500);
        } else if (event.type === 'NEW_COMMENT') {
          const comment = event.data as Comment;
          appendComment(comment);
          incrementCommentCount(comment.post_id);
          // Notify if someone replied to a post we care about (simple heuristic)
          if (comment.session_alias !== session?.persona) {
            addNotification({
              id: crypto.randomUUID(),
              message: `${comment.session_alias} replied in a thread.`,
              post_id: comment.post_id,
              comment_id: comment.id,
              created_at: comment.created_at,
              read: false,
            });
          }
        }
      });
      ws.addEventListener('open', () => setWsConnected(true));
      ws.addEventListener('close', () => {
        setWsConnected(false);
        if (!closed) reconnectTimer = setTimeout(connect, 4000);
      });
      ws.addEventListener('error', () => ws.close());
      wsRef.current = ws;
    }

    connect();
    return () => {
      closed = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.accessToken]);

  return (
    <>
      <div className="feed-layout">
        <main className="feed-main">
          {/* Feed header bar */}
          <div className="feed-bar">
            <h2>Global Feed</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {wsConnected
                ? <span className="live-dot">LIVE</span>
                : <span style={{ fontSize: 10, color: 'var(--text-faint)', letterSpacing: '0.08em' }}>reconnecting…</span>
              }
            </div>
          </div>

          {/* Composer */}
          <Composer />

          {/* Posts */}
          {loading ? (
            <div className="loading-screen" style={{ padding: '60px 0' }}>
              <span className="spinner lg" />
              <span>Connecting to the void…</span>
            </div>
          ) : posts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◈</div>
              <p>The void is silent.<br />Be the first to transmit.</p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {posts.map((post) => (
                <motion.div
                  key={post.id}
                  initial={{ opacity: 0, y: -16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 16 }}
                  transition={{ duration: 0.25 }}
                >
                  <PostCard post={post} isNew={newPostIds.has(post.id)} />
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </main>

        <div className="feed-aside">
          <Sidebar postCount={posts.length} />
        </div>
      </div>

      {/* Comment drawer overlay */}
      <CommentDrawer />
    </>
  );
}
