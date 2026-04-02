import type { AuthResponse, Post, Comment, UserSummary, AuditLogEntry } from '../types';

const BASE = '/api';
const API_KEY = import.meta.env.VITE_API_KEY ?? 'dev-api-key';

if (import.meta.env.PROD && !import.meta.env.VITE_API_KEY) {
  console.warn('[AnonCore] VITE_API_KEY is not set – using insecure default key.');
}

// ─── Low-level fetch wrapper ──────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail ?? 'API error'), { status: res.status, detail: err.detail });
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  register: (email: string, password: string) =>
    request<AuthResponse>('POST', '/auth/register', { email, password }),

  login: (email: string, password: string) =>
    request<AuthResponse>('POST', '/auth/login', { email, password }),

  logout: (token: string) =>
    request<{ message: string }>('POST', '/auth/logout', undefined, token),

  refresh: (token: string) =>
    request<AuthResponse>('POST', '/auth/refresh', undefined, token),
};

// ─── Posts ────────────────────────────────────────────────────────────────────

export const posts = {
  feed: (token: string, limit = 50, offset = 0) =>
    request<Post[]>('GET', `/posts/?limit=${limit}&offset=${offset}`, undefined, token),

  create: (token: string, content: string) =>
    request<Post>('POST', '/posts/', { content }, token),

  comments: (token: string, postId: string) =>
    request<Comment[]>('GET', `/posts/${postId}/comments`, undefined, token),

  addComment: (token: string, postId: string, content: string) =>
    request<Comment>('POST', `/posts/${postId}/comments`, { content }, token),

  deletePost: (token: string, postId: string) =>
    request<{ message: string }>('DELETE', `/posts/${postId}`, undefined, token),

  deleteComment: (token: string, postId: string, commentId: string) =>
    request<{ message: string }>('DELETE', `/posts/${postId}/comments/${commentId}`, undefined, token),

  report: (token: string, reason: string, postId?: string, commentId?: string) =>
    request<{ message: string }>('POST', '/posts/report', { reason, post_id: postId, comment_id: commentId }, token),
};

// ─── Admin ────────────────────────────────────────────────────────────────────

export const admin = {
  /** Returns the user list; throws with status=403 if not admin. */
  listUsers: (token: string) =>
    request<UserSummary[]>('GET', '/admin/users', undefined, token),

  banUser: (token: string, userId: string) =>
    request<{ message: string }>('POST', `/admin/users/${userId}/ban`, undefined, token),

  unbanUser: (token: string, userId: string) =>
    request<{ message: string }>('POST', `/admin/users/${userId}/unban`, undefined, token),

  resetStrikes: (token: string, userId: string) =>
    request<{ message: string }>('POST', `/admin/users/${userId}/reset-strikes`, undefined, token),

  removePost: (token: string, postId: string) =>
    request<{ message: string }>('DELETE', `/admin/posts/${postId}`, undefined, token),

  removeComment: (token: string, commentId: string) =>
    request<{ message: string }>('DELETE', `/admin/comments/${commentId}`, undefined, token),

  auditLogs: (token: string, limit = 100) =>
    request<AuditLogEntry[]>('GET', `/admin/audit-logs?limit=${limit}`, undefined, token),
};

// ─── WebSocket stream ─────────────────────────────────────────────────────────

export function createFeedSocket(token: string, onMessage: (data: unknown) => void): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  // In dev mode Vite proxies /ws → backend, in prod use same host
  const wsBase = import.meta.env.VITE_WS_URL ?? `${proto}://${window.location.host}`;
  const url = `${wsBase}/ws/feed?token=${encodeURIComponent(token)}&api_key=${encodeURIComponent(API_KEY)}`;
  const ws = new WebSocket(url);
  ws.addEventListener('message', (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      // ignore unparseable frames
    }
  });
  return ws;
}
