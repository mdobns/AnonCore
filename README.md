# AnonCore

**AnonCore** is an anonymous, real-time social platform built on the *Ghost Protocol*: every login issues a brand-new randomly-generated persona alias. Your posts exist; your identity doesn't.

```
"The void is always watching. Every transmission echoes into the darkness indefinitely."
```

---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start — Docker Compose](#quick-start--docker-compose)
- [Manual Setup](#manual-setup)
  - [1 — Backend (FastAPI)](#1--backend-fastapi)
  - [2 — Frontend (React + Vite)](#2--frontend-react--vite)
  - [3 — Python SDK](#3--python-sdk)
- [Creating Admin Accounts](#creating-admin-accounts)
- [Configuration Reference](#configuration-reference)
- [API Overview](#api-overview)
- [Documentation](#documentation)
- [License](#license)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser / Client                        │
│                  React + Vite SPA  (port 3000)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST  /api/*   WebSocket  /ws/feed
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend  (port 8000)                  │
│  /auth  /posts  /admin  /ws/feed  /health  /docs                │
└──────────────┬──────────────────────────────┬───────────────────┘
               │  async SQLAlchemy            │  redis-py
               ▼                             ▼
        ┌─────────────┐               ┌─────────────┐
        │ PostgreSQL  │               │    Redis    │
        │  (port 5432)│               │  (port 6379)│
        └─────────────┘               └─────────────┘

  Python SDK  (anoncore)
  └── async client library wrapping all REST + WebSocket endpoints
```

### The Ghost Protocol — Identity Rotation

| Token | Lifetime | Visible to UI? |
|-------|----------|----------------|
| **Account ID** | Permanent | ❌ Never |
| **Session Persona** | Per-login | ✅ Always (e.g. `Neon-Raven-404`) |

Every login generates a fresh human-readable alias. The permanent account ID never leaves the server.

---

## Prerequisites

### Docker path (recommended)
- [Docker Desktop](https://docs.docker.com/get-docker/) ≥ 24  
  or Docker Engine + [Compose plugin](https://docs.docker.com/compose/install/)

### Manual path
| Tool | Minimum version |
|------|----------------|
| Python | 3.10 |
| Node.js | 18 LTS |
| npm | 9 |
| PostgreSQL | 15 |
| Redis | 7 |

---

## Quick Start — Docker Compose

Spin up the entire stack (database, cache, backend, frontend) with a single command.

```bash
# 1. Clone the repository
git clone https://github.com/mdobns/AnonCore.git
cd AnonCore

# 2. Copy the environment template (edit SECRET_KEY before going to production)
cp backend/.env.example backend/.env

# 3. Start every service
docker compose up --build
```

Once all containers are healthy:

| URL | What opens |
|-----|-----------|
| <http://localhost:3000> | AnonCore frontend |
| <http://localhost:8000/docs> | Swagger / OpenAPI interactive docs |
| <http://localhost:8000/redoc> | ReDoc API reference |
| <http://localhost:8000/health> | Health-check endpoint (`{"status":"ok"}`) |

**Stop the stack:**
```bash
docker compose down          # stop containers, keep database volumes
docker compose down -v       # stop containers AND delete all data
```

---

## Manual Setup

Use this path when you already have PostgreSQL and Redis running, or when you want to develop each component independently.

### 1 — Backend (FastAPI)

#### a) Create a virtual environment

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

#### b) Install Python dependencies

```bash
pip install -r requirements.txt
```

#### c) Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set values for your environment. The variables you **must** change for a working local setup:

| Variable | Example | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://anoncore:secret@localhost:5432/anoncore` | Requires the `asyncpg` driver |
| `REDIS_URL` | `redis://localhost:6379` | |
| `SECRET_KEY` | *(generate with `openssl rand -hex 32`)* | **Change before production** |

See [docs/configuration.md](docs/configuration.md) for every available variable.

#### d) Create the PostgreSQL database

The backend automatically creates all tables on first startup — no migration tool needed for development.

If you need to create the database user/schema first:

```bash
psql -U postgres <<SQL
CREATE USER anoncore WITH PASSWORD 'anoncore';
CREATE DATABASE anoncore OWNER anoncore;
SQL
```

#### e) Start the backend server

```bash
# Development — auto-reloads on file changes
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API is live at <http://localhost:8000>.  
Swagger UI (interactive): <http://localhost:8000/docs>

---

### 2 — Frontend (React + Vite)

#### a) Install Node.js dependencies

```bash
cd frontend
npm install
```

#### b) Configure the frontend (optional)

Create `frontend/.env.local`:

```bash
# Must match one of the values in VALID_API_KEYS (backend .env)
VITE_API_KEY=dev-api-key

# Only needed if the backend is not on the same host (production)
# VITE_WS_URL=wss://api.example.com
```

> **Proxy note:** In development, Vite automatically proxies `/api/*` →  
> `http://localhost:8000` and `/ws/*` → `ws://localhost:8000`, so you never  
> need to set CORS headers or custom origins when running locally.

#### c) Start the development server

```bash
npm run dev
```

Open <http://localhost:3000>.

#### d) Build for production

```bash
npm run build      # type-checks + bundles to frontend/dist/
npm run preview    # locally preview the production build
```

Deploy the `frontend/dist/` directory to any static host (Nginx, Caddy, S3, Vercel, Netlify, etc.).

---

### 3 — Python SDK

The SDK is a standalone async Python library. You can install it into any Python 3.10+ environment.

#### a) Install

```bash
cd sdk

# Standard install
pip install .

# Editable install (recommended while developing the SDK itself)
pip install -e .

# Include test/dev dependencies
pip install -e ".[dev]"
```

#### b) Minimal usage example

```python
import asyncio
from anoncore import AnonCore
from anoncore.models import SDKConfig, Credentials

async def main():
    anon = AnonCore(SDKConfig(
        api_key="dev-api-key",            # must match VALID_API_KEYS on the server
        base_url="http://localhost:8000",
        ws_url="ws://localhost:8000",
    ))

    # Every login returns a fresh anonymous persona — Ghost Protocol
    session = await anon.auth.login(Credentials("user@example.com", "secret"))
    print(f"Connected as: {session.persona}")   # e.g. "Neon-Raven-404"

    # Subscribe to real-time events before connecting
    anon.stream.subscribe(lambda event: print("Event:", event.type, event.data))

    # Open the WebSocket stream
    await anon.connect()

    # Post to the global anonymous feed
    post = await anon.post.create_post("Hello, anonymous world!")

    # Fetch the current feed
    feed = await anon.post.get_feed()
    for p in feed:
        print(f"  [{p.session_alias}] {p.content}")

    # Rotate identity without logging out
    new_session = await anon.auth.refresh_identity()
    print(f"New persona: {new_session.persona}")

    # Logout wipes all local session and notification data
    await anon.logout()

asyncio.run(main())
```

See [docs/sdk.md](docs/sdk.md) for the complete SDK reference.

---

## Creating Admin Accounts

Admin privileges are granted by adding a registered user's email to the `ADMIN_EMAILS_RAW` environment variable — there is no separate sign-up flow.

**Quick steps:**

1. **Register** the account via `POST /auth/register` (or the web UI).
2. **Add the email** to `ADMIN_EMAILS_RAW` in `backend/.env`:
   ```bash
   ADMIN_EMAILS_RAW=admin@example.com
   ```
3. **Restart** the backend for the change to take effect.
4. **Log in** with the promoted account — the admin console will appear in the frontend sidebar.

For a full guide including multiple admins, revoking access, available admin endpoints, and security recommendations, see [docs/admin.md](docs/admin.md).

---

## Configuration Reference

All environment variables with their defaults and accepted values are documented in [docs/configuration.md](docs/configuration.md).

---

## API Overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | API key | Create account; returns JWT + persona |
| `POST` | `/auth/login` | API key | Login; rotates persona; returns JWT |
| `POST` | `/auth/logout` | JWT | Invalidate the current session |
| `POST` | `/auth/refresh` | JWT | Rotate persona; return new JWT |
| `GET`  | `/posts/` | JWT | Paginated global feed |
| `POST` | `/posts/` | JWT | Submit a new anonymous post |
| `GET`  | `/posts/{id}/comments` | JWT | List comments on a post |
| `POST` | `/posts/{id}/comments` | JWT | Add an anonymous comment |
| `POST` | `/posts/report` | JWT | Flag content for admin review |
| `GET`  | `/admin/users` | JWT + admin | List all user accounts |
| `POST` | `/admin/users/{id}/ban` | JWT + admin | Ban a user |
| `POST` | `/admin/users/{id}/unban` | JWT + admin | Lift a ban |
| `POST` | `/admin/users/{id}/reset-strikes` | JWT + admin | Reset strike counter |
| `DELETE` | `/admin/posts/{id}` | JWT + admin | Soft-delete a post |
| `DELETE` | `/admin/comments/{id}` | JWT + admin | Soft-delete a comment |
| `GET`  | `/admin/audit-logs` | JWT + admin | Latest moderation audit entries |
| `GET`  | `/health` | none | Liveness check |
| `WS`   | `/ws/feed?token=…&api_key=…` | JWT + API key | Real-time event stream |

Full interactive explorer: <http://localhost:8000/docs>  
Detailed reference with cURL examples: [docs/api.md](docs/api.md)

---

## Documentation

| File | Contents |
|------|---------|
| [docs/admin.md](docs/admin.md) | How to create and manage admin accounts |
| [docs/configuration.md](docs/configuration.md) | Every environment variable, defaults, and valid values |
| [docs/api.md](docs/api.md) | REST & WebSocket API reference with cURL examples |
| [docs/sdk.md](docs/sdk.md) | Python SDK — classes, methods, error types |
| [docs/development.md](docs/development.md) | Dev workflow, running tests, project structure |

---

## License

This project is licensed under the **MIT License**.
