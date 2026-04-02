# Development Guide

This guide covers the local development workflow for each AnonCore component, running the test suite, and the overall project structure.

---

## Project Structure

```
AnonCore/
├── README.md                   ← Getting started (you are here)
├── docker-compose.yml          ← One-command full-stack setup
│
├── docs/
│   ├── configuration.md        ← All environment variables
│   ├── api.md                  ← REST & WebSocket API reference
│   ├── sdk.md                  ← Python SDK guide
│   └── development.md          ← This file
│
├── backend/                    ← FastAPI service
│   ├── Dockerfile
│   ├── .env.example            ← Template for .env
│   ├── requirements.txt
│   └── app/
│       ├── main.py             ← FastAPI app + WebSocket endpoint
│       ├── config.py           ← Pydantic settings (env vars)
│       ├── database.py         ← Async SQLAlchemy engine + session
│       ├── models.py           ← ORM models (UserAccount, Post, Comment, AuditLog)
│       ├── routers/
│       │   ├── auth.py         ← /auth/register, /login, /logout, /refresh
│       │   ├── posts.py        ← /posts/ (feed, create, comment, report)
│       │   ├── admin.py        ← /admin/* (ban, audit logs, content removal)
│       │   └── security.py     ← JWT helpers, FastAPI dependencies
│       ├── middleware/
│       │   └── moderation.py   ← Regex + NLP content filter
│       └── services/
│           ├── persona.py      ← Ghost Protocol alias generator
│           └── redis.py        ← Redis Pub/Sub publish / subscribe
│
├── frontend/                   ← React SPA
│   ├── Dockerfile
│   ├── nginx.conf              ← Nginx config (used in Docker)
│   ├── package.json
│   ├── vite.config.ts          ← Vite + dev proxy config
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx            ← React entry point
│       ├── App.tsx             ← Root component + routing
│       ├── styles.css          ← Global cyberpunk theme tokens
│       ├── api/
│       │   └── index.ts        ← Typed fetch wrapper + WebSocket factory
│       ├── components/
│       │   ├── AuthGate.tsx    ← Login / register screen
│       │   ├── FeedPage.tsx    ← Main feed + WebSocket lifecycle
│       │   ├── Header.tsx      ← Nav bar with persona badge
│       │   ├── Composer.tsx    ← Post composer
│       │   ├── PostCard.tsx    ← Individual post card
│       │   ├── CommentDrawer.tsx ← Slide-in comment thread
│       │   ├── Sidebar.tsx     ← Session stats + identity widget
│       │   ├── NotificationPanel.tsx ← Dropdown notification list
│       │   └── Toast.tsx       ← Animated toast container
│       ├── store/
│       │   ├── authStore.ts    ← Zustand auth (persisted to localStorage)
│       │   ├── feedStore.ts    ← Posts + comments state
│       │   ├── notificationStore.ts ← Notification list
│       │   └── uiStore.ts      ← Toast queue + UI flags
│       └── types/
│           └── index.ts        ← Shared TypeScript interfaces
│
└── sdk/                        ← Python async client library
    ├── anoncore/
    │   ├── __init__.py         ← Public exports
    │   ├── client.py           ← AnonCore main entry point
    │   ├── auth.py             ← AuthModule
    │   ├── stream.py           ← StreamModule (WebSocket + reconnect)
    │   ├── post.py             ← PostModule
    │   ├── notification.py     ← NotificationModule
    │   ├── models.py           ← Dataclasses / enums
    │   └── exceptions.py       ← Custom exception hierarchy
    ├── tests/
    │   ├── test_auth.py
    │   ├── test_post.py
    │   └── test_notification.py
    ├── pyproject.toml
    ├── pytest.ini
    ├── requirements.txt        ← Runtime deps (httpx, websockets)
    └── requirements-dev.txt    ← Test deps (pytest, respx, etc.)
```

---

## Backend Development

### Running with hot-reload

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Uvicorn watches for file changes and restarts automatically.

### Logging

Set the log level via the `--log-level` flag:

```bash
uvicorn app.main:app --reload --log-level debug
```

### Resetting the database

Drop and recreate all tables (development only):

```bash
# Connect to your database
psql -U anoncore anoncore

-- Drop and recreate the schema
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q
```

Then restart the backend — `create_tables()` will recreate everything on startup.

### Adding new moderation rules

Edit `backend/app/middleware/moderation.py`:

1. **Regex rules** — add a new `re.compile(...)` entry to `_BLOCKED_PATTERNS`.
2. **NLP integration** — replace the body of `_nlp_check()` with a call to your toxicity API.

### Persona generator

New alias formats can be added to `backend/app/services/persona.py`.  
The default format is `Adjective-Noun-NNN`.

---

## Frontend Development

### Starting the dev server

```bash
cd frontend
npm install    # first time only
npm run dev    # starts on http://localhost:3000
```

The Vite dev server proxies all requests:
- `/api/*` → `http://localhost:8000` (REST)
- `/ws/*` → `ws://localhost:8000` (WebSocket)

No CORS configuration is needed during development.

### TypeScript

Run the type-checker without building:

```bash
npm run build   # runs tsc --noEmit then vite build
# or just type-check:
npx tsc --noEmit
```

### Production build

```bash
npm run build         # outputs to frontend/dist/
npm run preview       # serves frontend/dist/ locally on port 3000
```

### State management

State is managed with [Zustand](https://zustand-demo.pmnd.rs/):

| Store | File | Persisted? | Contents |
|-------|------|------------|---------|
| `authStore` | `store/authStore.ts` | ✅ localStorage | Current session (persona, JWT, expiry) |
| `feedStore` | `store/feedStore.ts` | ❌ | Posts, comments, active post ID |
| `notificationStore` | `store/notificationStore.ts` | ❌ | Notification list, unread count |
| `uiStore` | `store/uiStore.ts` | ❌ | Toast queue, modal flags |

---

## SDK Development

### Editable install

```bash
cd sdk
pip install -e ".[dev]"
```

### Running tests

```bash
cd sdk
pytest -v
```

Tests use `respx` to mock all HTTP calls — no live backend is needed.

```bash
# Run a specific test file
pytest tests/test_auth.py -v

# Run with output capture disabled (see print statements)
pytest -s

# Run and show test coverage
pytest --tb=short
```

### Adding a new SDK module

1. Create `sdk/anoncore/my_module.py` with a class `MyModule`.
2. Import and instantiate it in `sdk/anoncore/client.py`.
3. Expose it as a `@property` on `AnonCore`.
4. Add tests in `sdk/tests/test_my_module.py`.
5. Export it from `sdk/anoncore/__init__.py` if users need to import the class directly.

---

## Running the Full Test Suite

### SDK tests

```bash
cd sdk
pip install -e ".[dev]"
pytest -v
```

### Backend tests

> The backend currently relies on SQLAlchemy startup (`create_tables`) and integration tests should use a test database. If you add backend tests, use `pytest-asyncio` and `httpx.AsyncClient` against the FastAPI `app` object directly.

```bash
# Example (requires a test DATABASE_URL env var)
cd backend
pip install pytest pytest-asyncio httpx
DATABASE_URL=postgresql+asyncpg://... pytest -v
```

---

## Code Style

### Backend (Python)

- Follow **PEP 8** and **PEP 257** (docstrings).
- All public functions should have type annotations.
- Use `from __future__ import annotations` at the top of every file.
- Async functions use `await` — no threading.

### Frontend (TypeScript)

- **Strict mode** is enabled — no implicit `any`.
- Component files use `.tsx`, utility files use `.ts`.
- Avoid framework UI libraries; use the custom design system in `src/styles.css`.

### SDK (Python)

- Follow the same Python conventions as the backend.
- All public methods must be `async def`.
- Use the existing exception hierarchy from `exceptions.py` — never raise raw `Exception`.

---

## Common Issues

### Backend won't start — "connection refused" to database

Ensure PostgreSQL is running and the `DATABASE_URL` in `.env` is correct.  
Check the database credentials:

```bash
psql "postgresql://anoncore:anoncore@localhost:5432/anoncore" -c "\l"
```

### Frontend shows "API error" on login

1. Confirm the backend is running on port `8000`.
2. Check that `VITE_API_KEY` (or the default `dev-api-key`) matches a value in `VALID_API_KEYS`.
3. Look at browser DevTools → Network tab for the exact error response.

### WebSocket doesn't connect

- The backend must be running.
- In development the Vite proxy handles `/ws/` — make sure you're using the dev server (`npm run dev`), not a production build served without Nginx.
- In Docker, check `nginx.conf` proxy settings and that the `backend` service health-check passes.

### `asyncpg` not found

The `asyncpg` package is listed in `requirements.txt`. If you see import errors, ensure you activated the virtual environment before installing:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Token expired mid-session

The `AuthModule` runs an automatic background refresh 60 seconds before token expiry.  
If you see `SessionExpiredError` it means either:
- The refresh loop was cancelled (the process restarted).
- The server rejected the refresh (account was banned).

Log in again to obtain a fresh token.
