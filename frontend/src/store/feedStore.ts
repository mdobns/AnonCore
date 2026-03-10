import { create } from 'zustand';
import type { Post, Comment } from '../types';

interface FeedState {
  posts: Post[];
  setPosts: (posts: Post[]) => void;
  prependPost: (post: Post) => void;
  removePost: (postId: string) => void;
  incrementCommentCount: (postId: string) => void;
  decrementCommentCount: (postId: string) => void;
  comments: Record<string, Comment[]>;
  setComments: (postId: string, comments: Comment[]) => void;
  appendComment: (comment: Comment) => void;
  removeComment: (postId: string, commentId: string) => void;
  activePostId: string | null;
  setActivePostId: (id: string | null) => void;
}

export const useFeedStore = create<FeedState>((set, get) => ({
  posts: [],
  setPosts: (posts) => set({ posts }),
  prependPost: (post) =>
    set((s) =>
      s.posts.some((p) => p.id === post.id)
        ? s
        : { posts: [post, ...s.posts] },
    ),
  removePost: (postId) =>
    set((s) => ({ posts: s.posts.filter((p) => p.id !== postId) })),
  incrementCommentCount: (postId) =>
    set((s) => ({
      posts: s.posts.map((p) =>
        p.id === postId ? { ...p, comment_count: p.comment_count + 1 } : p,
      ),
    })),
  decrementCommentCount: (postId) =>
    set((s) => ({
      posts: s.posts.map((p) =>
        p.id === postId ? { ...p, comment_count: Math.max(0, p.comment_count - 1) } : p,
      ),
    })),
  comments: {},
  setComments: (postId, comments) =>
    set((s) => ({ comments: { ...s.comments, [postId]: comments } })),
  appendComment: (comment) => {
    const existing = get().comments[comment.post_id] ?? [];
    if (existing.some((c) => c.id === comment.id)) return;
    set((s) => ({
      comments: {
        ...s.comments,
        [comment.post_id]: [...existing, comment],
      },
    }));
  },
  removeComment: (postId, commentId) =>
    set((s) => ({
      comments: {
        ...s.comments,
        [postId]: (s.comments[postId] ?? []).filter((c) => c.id !== commentId),
      },
    })),
  activePostId: null,
  setActivePostId: (id) => set({ activePostId: id }),
}));
