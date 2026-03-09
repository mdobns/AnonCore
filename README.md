# AnonCore

AnonCore is an **anonymous, real-time social platform** built on a
**Real-time Event-Driven Architecture**. Because there are no "friends,"
every post is a global event broadcast to all active sessions simultaneously.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                  AnonCore SDK (Python)                   │
│  AuthModule · StreamModule · PostModule · NotificationModule │
└────────────────────────┬─────────────────────────────────┘
                         │  HTTPS / WebSocket
┌────────────────────────▼─────────────────────────────────┐
│               FastAPI Backend                            │
│  /auth  ·  /posts  ·  /admin  ·  /ws/feed               │
│  Moderation Middleware (Regex + NLP)                     │
└──────┬──────────────────────────┬────────────────────────┘
       │ SQLAlchemy (async)       │ Redis Pub/Sub
┌──────▼──────────┐     ┌────────▼───────────┐
│  PostgreSQL DB  │     │  Redis             │
│  UserAccounts   │     │  global_feed chan. │
│  Posts          │     └────────────────────┘
│  Comments       │
│  AuditLog       │
└─────────────────┘
```

### The Ghost Protocol – Identity Rotation

Users have two tokens:

| Token | Lifetime | Visible to UI? |
|-------|----------|----------------|
| **Account Token** | Permanent | ❌ Never |
| **Session Persona** | Per-login | ✅ Always |

On every login the backend generates a new human-readable alias
(e.g. `Neon-Raven-404`) via `generate_persona()`. This alias is embedded in
the JWT and used for all public interactions. The permanent account ID never
leaves the server.

---

## Repository Layout

```
AnonCore/
├── sdk/                        # Python SDK (installable package)
│   ├── anoncore/
│   │   ├── __init__.py         # Public exports
│   │   ├── client.py           # AnonCore – main entry point
│   │   ├── auth.py             # AuthModule
│   │   ├── stream.py           # StreamModule (WebSocket)
│   │   ├── post.py             # PostModule
│   │   ├── notification.py     # NotificationModule
│   │   ├── models.py           # Data models / dataclasses
│   │   └── exceptions.py       # Custom exceptions
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_post.py
│   │   └── test_notification.py
│   ├── pyproject.toml
│   └── requirements.txt
│
└── backend/                    # FastAPI backend
    ├── app/
    │   ├── main.py             # FastAPI app + WebSocket endpoint
    │   ├── config.py           # Settings (pydantic-settings)
    │   ├── database.py         # Async SQLAlchemy engine
    │   ├── models.py           # ORM models
    │   ├── routers/
    │   │   ├── auth.py         # /auth/login · /auth/logout · /auth/refresh
    │   │   ├── posts.py        # /posts/ · /posts/{id}/comments · /posts/report
    │   │   ├── admin.py        # /admin/… (protected)
    │   │   └── security.py     # JWT helpers, dependencies
    │   ├── middleware/
    │   │   └── moderation.py   # Regex + NLP pre-flight filter
    │   └── services/
    │       ├── persona.py      # Ghost Protocol persona generator
    │       └── redis.py        # Redis Pub/Sub publisher/subscriber
    ├── requirements.txt
    └── .env.example
```

---

## SDK – Quick Start

### Installation

```bash
cd sdk
pip install -e .
```

### Usage

```python
import asyncio
from anoncore import AnonCore
from anoncore.models import SDKConfig, Credentials

async def main():
    anon = AnonCore(SDKConfig(
        api_key="dev-api-key",
        base_url="http://localhost:8000",
        ws_url="ws://localhost:8000",
    ))

    # Login – generates a fresh persona ("Ghost Protocol")
    session = await anon.auth.login(Credentials("user@example.com", "secret"))
    print(f"Logged in as: {session.persona}")   # e.g. "Neon-Raven-404"

    # Subscribe to the real-time global feed
    def on_event(event):
        if event.type.value == "NEW_POST":
            print(f"New post by {event.data.session_alias}: {event.data.content}")

    anon.stream.subscribe(on_event)

    # Get notified when someone replies to your posts or mentions you
    anon.notifications.on_notification(
        lambda n: print(f"🔔 {n.message}")
    )

    # Connect WebSocket
    await anon.connect()

    # Create a post
    post = await anon.post.create_post("Hello, anonymous world!")
    print(f"Post created: {post.id}")

    # Add a comment
    comment = await anon.post.add_comment(post.id, "Nice post!")

    # Report content
    await anon.post.report_content(post_id=post.id, reason="spam")

    # Refresh identity (rotate persona)
    new_session = await anon.auth.refresh_identity()
    print(f"New persona: {new_session.persona}")   # e.g. "Silent-Fox-82"

    # Logout – wipes notification history for true anonymity
    await anon.logout()

asyncio.run(main())
```

### SDK Modules

| Module | Class | Key Methods |
|--------|-------|-------------|
| **Auth** | `AuthModule` | `login()`, `logout()`, `refresh_identity()` |
| **Stream** | `StreamModule` | `subscribe()`, `connect()`, `disconnect()` |
| **Post** | `PostModule` | `create_post()`, `add_comment()`, `report_content()`, `get_feed()` |
| **Notifications** | `NotificationModule` | `on_notification()`, `mark_read()`, `clear()` |

### Exceptions

| Exception | When raised |
|-----------|-------------|
| `AuthenticationError` | Bad credentials |
| `SuspendedAccountError` | Account banned |
| `SessionExpiredError` | JWT expired |
| `ModerationError` | Content flagged (HTTP 403) |
| `NotConnectedError` | Action requires login |
| `APIError` | Unexpected non-2xx response |

---

## Backend – Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis

### Setup

```bash
cd backend
cp .env.example .env   # fill in your values
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://…` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `SECRET_KEY` | *(must change)* | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `VALID_API_KEYS` | `dev-api-key` | Comma-separated list of allowed SDK API keys |
| `MODERATION_ENABLED` | `true` | Toggle the pre-flight moderation filter |
| `MAX_STRIKES` | `3` | Strikes before automatic account suspension |
| `ADMIN_EMAILS` | `""` | Comma-separated admin email list |

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | API key | Create account + session |
| POST | `/auth/login` | API key | Login, get new persona |
| POST | `/auth/logout` | JWT | Invalidate session |
| POST | `/auth/refresh` | JWT | Rotate identity |
| GET | `/posts/` | JWT | Global feed |
| POST | `/posts/` | JWT | Create post |
| GET | `/posts/{id}/comments` | JWT | List comments |
| POST | `/posts/{id}/comments` | JWT | Add comment |
| POST | `/posts/report` | JWT | Report content |
| GET | `/admin/users` | JWT (admin) | List accounts |
| POST | `/admin/users/{id}/ban` | JWT (admin) | Ban user |
| DELETE | `/admin/posts/{id}` | JWT (admin) | Remove post |
| GET | `/admin/audit-logs` | JWT (admin) | Audit trail |
| WS | `/ws/feed` | JWT + API key | Real-time event stream |

---

## Moderation & Strike Workflow

1. **Pre-flight Filter** – Every `POST /posts/` and `POST /posts/{id}/comments`
   runs the content through `run_moderation()` before any database write.
2. **HTTP 403 on flag** – The SDK raises `ModerationError` which the UI can
   display as a warning toast.
3. **Strike Counter** – Each flagged submission increments `strike_count` on
   the hidden `UserAccount` record.
4. **Auto-Suspension** – When `strike_count >= MAX_STRIKES` the account's
   `is_banned` flag is set to `True`, causing subsequent requests to return
   `403 Forbidden` and the SDK to surface a `SuspendedAccountError`.

---

## Running Tests

```bash
cd sdk
pip install -r requirements-dev.txt
pytest -v
```

---

## License

This project is licensed under the MIT License.

