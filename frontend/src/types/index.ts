// ─── Domain types ─────────────────────────────────────────────────────────────

export interface Session {
  persona: string;
  accessToken: string;
  expiresAt: string;
}

export interface Post {
  id: string;
  content: string;
  session_alias: string;
  created_at: string;
  comment_count: number;
  _new?: boolean;
}

export interface Comment {
  id: string;
  post_id: string;
  content: string;
  session_alias: string;
  created_at: string;
}

// ─── Stream events ────────────────────────────────────────────────────────────

export type StreamEventType = 'NEW_POST' | 'NEW_COMMENT' | 'MODERATION_WARNING' | 'SESSION_EXPIRED';

export interface StreamEvent {
  type: StreamEventType;
  data: Post | Comment | Record<string, unknown>;
}

// ─── Notification ─────────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  message: string;
  post_id: string;
  comment_id?: string;
  created_at: string;
  read: boolean;
}

// ─── API shapes ───────────────────────────────────────────────────────────────

export interface AuthResponse {
  session_alias: string;
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface APIError {
  detail: string;
}

// ─── Admin types ──────────────────────────────────────────────────────────────

export interface UserSummary {
  id: string;
  email: string;
  is_banned: boolean;
  strike_count: number;
}

export interface AuditLogEntry {
  id: string;
  user_id: string;
  violation_type: string;
  detail: string;
  timestamp: string;
}
