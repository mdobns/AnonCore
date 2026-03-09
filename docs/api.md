# API Reference

The AnonCore backend exposes a REST API and a WebSocket endpoint.

- **Base URL (local):** `http://localhost:8000`
- **Interactive docs:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative docs:** `http://localhost:8000/redoc` (ReDoc)

---

## Authentication

All endpoints (except `/health` and `/auth/register`) require **at least one** of these headers:

| Header | Value | Required for |
|--------|-------|-------------|
| `X-API-Key` | A key from `VALID_API_KEYS` | `/auth/register`, `/auth/login` |
| `Authorization` | `Bearer <JWT>` | All other protected routes |

JWTs are obtained from `/auth/login` or `/auth/register` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60 minutes). The SDK refreshes them automatically.

---

## Endpoints

### Health

#### `GET /health`

Returns the service liveness status. No authentication required.

**Response `200`:**
```json
{ "status": "ok" }
```

**cURL:**
```bash
curl http://localhost:8000/health
```

---

### Auth

#### `POST /auth/register`

Create a new user account and receive a JWT + anonymous persona.

**Headers:** `X-API-Key: <key>`

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "strongpassword"
}
```

**Response `201`:**
```json
{
  "session_alias": "Neon-Raven-404",
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_at": "2026-03-09T10:00:00+00:00"
}
```

**Errors:**
| Code | Reason |
|------|--------|
| `409` | Email already registered |

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'
```

---

#### `POST /auth/login`

Authenticate and receive a **new** anonymous persona every time.

**Headers:** `X-API-Key: <key>`

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response `200`:** same shape as `/auth/register`.

**Errors:**
| Code | Reason |
|------|--------|
| `401` | Invalid credentials |
| `403` | Account is banned |

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'
```

---

#### `POST /auth/logout`

Invalidate the current session (server-side audit hook; JWT is still short-lived).

**Headers:** `Authorization: Bearer <JWT>`

**Response `200`:**
```json
{ "message": "Logged out successfully." }
```

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer eyJ..."
```

---

#### `POST /auth/refresh`

Rotate identity: issue a brand-new persona alias and JWT while keeping the same account.

**Headers:** `Authorization: Bearer <JWT>`

**Response `200`:** same shape as `/auth/login`.

**Errors:**
| Code | Reason |
|------|--------|
| `403` | Account is banned |

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Authorization: Bearer eyJ..."
```

---

### Posts

#### `GET /posts/`

Return the paginated global anonymous feed, newest first.

**Headers:** `Authorization: Bearer <JWT>`

**Query params:**
| Param | Default | Max | Description |
|-------|---------|-----|-------------|
| `limit` | `50` | `100` | Number of posts to return |
| `offset` | `0` | — | Number of posts to skip |

**Response `200`:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "Hello, anonymous world!",
    "session_alias": "Neon-Raven-404",
    "created_at": "2026-03-09T09:00:00+00:00",
    "comment_count": 3
  }
]
```

**cURL:**
```bash
curl "http://localhost:8000/posts/?limit=20&offset=0" \
  -H "Authorization: Bearer eyJ..."
```

---

#### `POST /posts/`

Submit a new anonymous post. Content is run through the moderation pipeline before being stored.

**Headers:** `Authorization: Bearer <JWT>`

**Request body:**
```json
{ "content": "My anonymous message." }
```

**Response `201`:** same shape as a single item from `GET /posts/`.

**Errors:**
| Code | Reason |
|------|--------|
| `403` | Content flagged by moderation; a strike is recorded |

**cURL:**
```bash
curl -X POST http://localhost:8000/posts/ \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"content":"My anonymous message."}'
```

---

#### `GET /posts/{post_id}/comments`

List all non-removed comments on a post, oldest first.

**Headers:** `Authorization: Bearer <JWT>`

**Response `200`:**
```json
[
  {
    "id": "...",
    "post_id": "550e8400-...",
    "content": "Nice post!",
    "session_alias": "Silent-Fox-82",
    "created_at": "2026-03-09T09:05:00+00:00"
  }
]
```

**cURL:**
```bash
curl "http://localhost:8000/posts/550e8400-e29b-41d4-a716-446655440000/comments" \
  -H "Authorization: Bearer eyJ..."
```

---

#### `POST /posts/{post_id}/comments`

Add an anonymous comment to a post. Also subject to moderation.

**Headers:** `Authorization: Bearer <JWT>`

**Request body:**
```json
{ "content": "Nice post!" }
```

**Response `201`:** same shape as a single item from `GET /posts/{id}/comments`.

**cURL:**
```bash
curl -X POST \
  "http://localhost:8000/posts/550e8400-e29b-41d4-a716-446655440000/comments" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"content":"Nice post!"}'
```

---

#### `POST /posts/report`

Report a post or comment for admin review.

**Headers:** `Authorization: Bearer <JWT>`

**Request body:**
```json
{
  "reason": "spam",
  "post_id": "550e8400-...",
  "comment_id": null
}
```

At least one of `post_id` or `comment_id` must be provided.

**Response `200`:**
```json
{ "message": "Report submitted. Thank you." }
```

**cURL:**
```bash
curl -X POST http://localhost:8000/posts/report \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"reason":"spam","post_id":"550e8400-e29b-41d4-a716-446655440000"}'
```

---

### Admin

All admin routes require the authenticated user's email to be listed in the `ADMIN_EMAILS` environment variable.

#### `GET /admin/users`

List all user accounts.

```bash
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer eyJ..."
```

#### `POST /admin/users/{user_id}/ban`

Permanently ban a user.

```bash
curl -X POST "http://localhost:8000/admin/users/<uuid>/ban" \
  -H "Authorization: Bearer eyJ..."
```

#### `POST /admin/users/{user_id}/unban`

Lift a ban and reset the strike counter.

```bash
curl -X POST "http://localhost:8000/admin/users/<uuid>/unban" \
  -H "Authorization: Bearer eyJ..."
```

#### `POST /admin/users/{user_id}/reset-strikes`

Reset strike counter to 0 without lifting a ban.

```bash
curl -X POST "http://localhost:8000/admin/users/<uuid>/reset-strikes" \
  -H "Authorization: Bearer eyJ..."
```

#### `DELETE /admin/posts/{post_id}`

Soft-delete a post (`is_removed = true`; not physically deleted).

```bash
curl -X DELETE "http://localhost:8000/admin/posts/<uuid>" \
  -H "Authorization: Bearer eyJ..."
```

#### `DELETE /admin/comments/{comment_id}`

Soft-delete a comment.

```bash
curl -X DELETE "http://localhost:8000/admin/comments/<uuid>" \
  -H "Authorization: Bearer eyJ..."
```

#### `GET /admin/audit-logs`

Return the latest moderation audit entries (default 100, max 500).

```bash
curl "http://localhost:8000/admin/audit-logs?limit=50" \
  -H "Authorization: Bearer eyJ..."
```

---

### WebSocket — Real-Time Feed

#### `WS /ws/feed`

Opens a persistent WebSocket connection that streams every global event to the connected client.

**Connection URL:**
```
ws://localhost:8000/ws/feed?token=<JWT>&api_key=<API_KEY>
```

**Close codes:**
| Code | Reason |
|------|--------|
| `1008` | Invalid API key |
| `1008` | Invalid or expired JWT |

**Event messages** (JSON):

Each message is a JSON object with a `type` field and a `data` payload.

```jsonc
// New post
{
  "type": "NEW_POST",
  "data": {
    "id": "...",
    "content": "...",
    "session_alias": "Neon-Raven-404",
    "created_at": "2026-03-09T09:00:00+00:00",
    "comment_count": 0
  }
}

// New comment
{
  "type": "NEW_COMMENT",
  "data": {
    "id": "...",
    "post_id": "...",
    "content": "...",
    "session_alias": "Silent-Fox-82",
    "created_at": "2026-03-09T09:01:00+00:00"
  }
}
```

**JavaScript example:**
```javascript
const ws = new WebSocket(
  `ws://localhost:8000/ws/feed?token=${jwt}&api_key=${apiKey}`
);

ws.addEventListener('message', (event) => {
  const { type, data } = JSON.parse(event.data);
  if (type === 'NEW_POST') console.log('New post:', data.content);
  if (type === 'NEW_COMMENT') console.log('New comment:', data.content);
});
```

---

## Error Response Format

All error responses follow FastAPI's standard format:

```json
{
  "detail": "Human-readable error message."
}
```

For validation errors (HTTP `422`) the `detail` field is an array of field-level error objects as defined by Pydantic.
