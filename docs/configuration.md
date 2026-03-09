# Configuration Reference

All AnonCore backend settings are loaded from environment variables (or a `.env` file placed in the `backend/` directory). Settings are parsed by [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

---

## Backend Environment Variables

Copy `backend/.env.example` to `backend/.env` and adjust the values below.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://anoncore:anoncore@localhost:5432/anoncore` | Async PostgreSQL connection string. **Must** use the `asyncpg` driver prefix (`postgresql+asyncpg://`). |

**Examples:**

```bash
# Local default
DATABASE_URL=postgresql+asyncpg://anoncore:anoncore@localhost:5432/anoncore

# Remote / RDS
DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/anoncore

# With SSL
DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/anoncore?ssl=require
```

---

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string used for the real-time Pub/Sub feed. |

**Examples:**

```bash
# Local
REDIS_URL=redis://localhost:6379

# Redis Cloud / Upstash with password
REDIS_URL=redis://:yourpassword@redis-host.example.com:6379

# Redis with TLS
REDIS_URL=rediss://:yourpassword@redis-host.example.com:6380
```

---

### Authentication & JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `CHANGE_ME_IN_PRODUCTION` | HMAC secret used to sign JWTs. Generate a strong value with `openssl rand -hex 32`. **Never use the default in production.** |
| `ALGORITHM` | `HS256` | JWT signing algorithm. `HS256` is recommended; `HS384` and `HS512` are also supported. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Number of minutes before a JWT expires. The SDK automatically refreshes tokens 60 seconds before expiry. |

---

### API Keys

| Variable | Default | Description |
|----------|---------|-------------|
| `VALID_API_KEYS` | `dev-api-key` | Comma-separated list of API keys that the frontend/SDK must send in the `X-API-Key` header. Add multiple keys to support rolling rotation. |

**Example:**
```bash
VALID_API_KEYS=key-abc123,key-def456
```

---

### Moderation

| Variable | Default | Description |
|----------|---------|-------------|
| `MODERATION_ENABLED` | `true` | Set to `false` to disable the pre-flight content filter entirely (useful in development). |
| `MAX_STRIKES` | `3` | Number of moderation violations before a user account is automatically suspended. |

The moderation pipeline runs two passes:
1. **Regex filter** — fast keyword matching (blocking slurs, spam patterns, phone numbers).
2. **NLP stub** — pluggable toxicity model. Replace `_nlp_check()` in `backend/app/middleware/moderation.py` with a real implementation (e.g. Google Perspective API, spaCy).

---

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins. Set to your production frontend domain in production. |

**Example:**
```bash
ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
```

---

### Admin

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_EMAILS` | *(empty)* | Comma-separated list of email addresses that have access to the `/admin/*` endpoints. Leave empty to disable admin routes. |

**Example:**
```bash
ADMIN_EMAILS=admin@example.com,security@example.com
```

---

## Frontend Environment Variables

Frontend variables are passed to Vite at build time and must be prefixed with `VITE_`.  
For local development, create `frontend/.env.local` (this file is gitignored).

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_KEY` | `dev-api-key` | API key sent as the `X-API-Key` header in all requests. Must match one of the values in the backend `VALID_API_KEYS`. |
| `VITE_WS_URL` | *(current host)* | Override the WebSocket base URL, e.g. `wss://api.example.com`. Defaults to the same host and protocol as the page (auto-detected). |

**Example `frontend/.env.local`:**
```bash
VITE_API_KEY=my-production-api-key
VITE_WS_URL=wss://api.example.com
```

> **Note:** In development the Vite dev-server proxy rewrites `/api/*` and `/ws/*`  
> requests to the backend, so neither variable is required locally.

---

## Docker Compose Variables

When running via Docker Compose you can override any value using a root-level `.env` file or by prefixing the `docker compose` command:

```bash
SECRET_KEY=$(openssl rand -hex 32) \
ADMIN_EMAILS=admin@example.com \
docker compose up --build
```

Or create a `.env` in the repo root:

```bash
# .env  (repo root — used by docker compose)
SECRET_KEY=...
VALID_API_KEYS=prod-key-abc,prod-key-def
VITE_API_KEY=prod-key-abc
ADMIN_EMAILS=admin@example.com
```
