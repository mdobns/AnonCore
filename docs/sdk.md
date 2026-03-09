# Python SDK Guide

The `anoncore` package is a fully-async Python client library for the AnonCore platform.  
It wraps all REST and WebSocket endpoints and handles token refresh automatically.

---

## Requirements

- Python 3.10+
- Dependencies: `httpx >= 0.27`, `websockets >= 12.0`

---

## Installation

```bash
cd sdk

# Standard install (production use)
pip install .

# Editable install (when developing the SDK itself)
pip install -e .

# With development/test extras
pip install -e ".[dev]"
```

---

## Quick Start

```python
import asyncio
from anoncore import AnonCore
from anoncore.models import SDKConfig, Credentials

async def main():
    # Configure the client
    anon = AnonCore(SDKConfig(
        api_key="dev-api-key",
        base_url="http://localhost:8000",
        ws_url="ws://localhost:8000",
    ))

    # Login — generates a fresh persona on every call (Ghost Protocol)
    session = await anon.auth.login(Credentials("user@example.com", "secret"))
    print(f"Connected as: {session.persona}")  # e.g. "Neon-Raven-404"

    # Subscribe to the real-time feed before opening the WebSocket
    def on_event(event):
        print(f"[{event.type}] {event.data}")

    anon.stream.subscribe(on_event)
    await anon.connect()

    # Create a post
    post = await anon.post.create_post("Hello from the SDK!")

    # Fetch the global feed
    feed = await anon.post.get_feed(limit=10)
    for p in feed:
        print(f"  [{p.session_alias}] {p.content}")

    # Add a comment
    await anon.post.add_comment(post.id, "Reply!")

    # Rotate identity without logging out
    new_session = await anon.auth.refresh_identity()
    print(f"Rotated to: {new_session.persona}")

    # Disconnect and wipe all local identity data
    await anon.logout()

asyncio.run(main())
```

---

## Using as an Async Context Manager

```python
async def main():
    async with AnonCore(SDKConfig(api_key="dev-api-key")) as anon:
        await anon.auth.login(Credentials("user@example.com", "secret"))
        await anon.connect()
        await anon.post.create_post("Sent via context manager!")
    # disconnect() and http client cleanup called automatically
```

---

## Configuration — `SDKConfig`

```python
from anoncore.models import SDKConfig

config = SDKConfig(
    api_key="dev-api-key",          # required — must match VALID_API_KEYS on the server
    base_url="http://localhost:8000",  # default
    ws_url="ws://localhost:8000",      # default
    reconnect_interval=5.0,            # seconds between WebSocket reconnect attempts
    request_timeout=30.0,              # HTTP request timeout in seconds
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str` | — | **Required.** Sent as `X-API-Key` header. |
| `base_url` | `str` | `http://localhost:8000` | HTTP base URL of the backend. |
| `ws_url` | `str` | `ws://localhost:8000` | WebSocket base URL of the backend. |
| `reconnect_interval` | `float` | `5.0` | Seconds to wait before reconnecting a dropped WebSocket. |
| `request_timeout` | `float` | `30.0` | HTTP request timeout in seconds. |

---

## Module Reference

### `AnonCore` — Main Client

```python
from anoncore import AnonCore
anon = AnonCore(config)
```

| Property / Method | Description |
|-------------------|-------------|
| `anon.auth` | The `AuthModule` instance |
| `anon.stream` | The `StreamModule` instance |
| `anon.post` | The `PostModule` instance |
| `anon.notifications` | The `NotificationModule` instance |
| `anon.session` | Current `SessionInfo`, or `None` |
| `await anon.connect()` | Open WebSocket using the current session |
| `await anon.disconnect()` | Close WebSocket without logging out |
| `await anon.login(credentials)` | Login + connect WebSocket in one call |
| `await anon.logout()` | Disconnect + logout + wipe notification history |

---

### `AuthModule`

Accessed via `anon.auth`.

#### `await auth.login(credentials) → SessionInfo`

Authenticate and receive a fresh persona.

```python
from anoncore.models import Credentials

session = await anon.auth.login(Credentials("user@example.com", "secret"))
print(session.persona)      # "Neon-Raven-404"
print(session.jwt)          # "eyJ..."
print(session.expires_at)   # datetime(2026, 3, 9, 10, 0, 0, tzinfo=UTC)
```

**Raises:** `AuthenticationError`, `SuspendedAccountError`, `APIError`

#### `await auth.logout()`

Invalidate the session on the server and clear all local state.

#### `await auth.refresh_identity() → SessionInfo`

Rotate persona — the same account gets a brand-new alias and JWT.

**Raises:** `SessionExpiredError`, `APIError`

#### `auth.session → Optional[SessionInfo]`

Current session, or `None` if not logged in.

#### `auth.is_authenticated → bool`

`True` when a valid session is held.

---

### `PostModule`

Accessed via `anon.post`.

#### `await post.create_post(content) → Post`

Submit a post to the global feed.

```python
post = await anon.post.create_post("My anonymous message!")
print(post.id, post.session_alias, post.created_at)
```

**Raises:** `ModerationError` (HTTP 403), `NotConnectedError`, `APIError`

#### `await post.get_feed(limit=50, offset=0) → list[Post]`

Fetch the paginated global feed, newest first.

```python
feed = await anon.post.get_feed(limit=20, offset=0)
for p in feed:
    print(f"[{p.session_alias}] {p.content}  ({p.comment_count} replies)")
```

#### `await post.add_comment(post_id, content) → Comment`

Add a comment to a post.

```python
comment = await anon.post.add_comment(post.id, "Great point!")
```

**Raises:** `ModerationError`, `APIError`

#### `await post.get_comments(post_id) → list[Comment]`

Fetch all comments on a post.

```python
comments = await anon.post.get_comments(post.id)
```

#### `await post.report_content(reason, post_id=None, comment_id=None)`

Report a post or comment for admin review. At least one of `post_id` / `comment_id` must be provided.

```python
await anon.post.report_content("spam", post_id=post.id)
await anon.post.report_content("harassment", comment_id=comment.id)
```

---

### `StreamModule`

Accessed via `anon.stream`. Managed automatically by `AnonCore.connect()` / `disconnect()`.

#### `stream.subscribe(callback)`

Register a callback for real-time events. May be called multiple times.

```python
from anoncore.models import EventType

def handler(event):
    if event.type == EventType.NEW_POST:
        print("New post:", event.data.content)
    elif event.type == EventType.NEW_COMMENT:
        print("New comment:", event.data.content)

anon.stream.subscribe(handler)
```

`event.type` values:

| Value | `event.data` type | Description |
|-------|-------------------|-------------|
| `EventType.NEW_POST` | `Post` | A new post appeared in the global feed |
| `EventType.NEW_COMMENT` | `Comment` | A new comment was added |
| `EventType.MODERATION_WARNING` | `dict` | Content was flagged (informational) |
| `EventType.SESSION_EXPIRED` | `None` | The JWT expired mid-stream |

#### `stream.unsubscribe(callback)`

Remove a previously registered callback.

#### `await stream.connect(session)`

Open the WebSocket. Called automatically by `anon.connect()`.

#### `await stream.disconnect()`

Close the WebSocket gracefully.

---

### `NotificationModule`

Accessed via `anon.notifications`. Session-bound — history is wiped on `logout()`.

The notification module listens to the stream and generates `NotificationEntry` objects when someone replies to your posts or mentions your session alias.

#### `notifications.on_notification(callback)`

Register a callback invoked whenever a new notification arrives.

```python
anon.notifications.on_notification(
    lambda n: print(f"🔔 {n.message} (post: {n.post_id})")
)
```

#### `notifications.mark_read(notification_id)`

Mark a notification as read.

#### `notifications.all() → list[NotificationEntry]`

Return all accumulated notifications (read and unread).

#### `notifications.unread() → list[NotificationEntry]`

Return only unread notifications.

#### `notifications.clear()`

Delete all notifications. Called automatically on `logout()`.

---

## Data Models

### `SessionInfo`

| Field | Type | Description |
|-------|------|-------------|
| `persona` | `str` | Human-readable alias, e.g. `"Neon-Raven-404"` |
| `jwt` | `str` | Short-lived JWT |
| `expires_at` | `datetime` | UTC expiry timestamp |

### `Post`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID string |
| `content` | `str` | Post text |
| `session_alias` | `str` | Author's alias for this session |
| `created_at` | `datetime` | UTC creation time |
| `comment_count` | `int` | Number of non-removed comments |

### `Comment`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID string |
| `post_id` | `str` | Parent post UUID |
| `content` | `str` | Comment text |
| `session_alias` | `str` | Author's alias |
| `created_at` | `datetime` | UTC creation time |

### `NotificationEntry`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Local UUID |
| `post_id` | `str` | Related post UUID |
| `comment_id` | `str \| None` | Related comment UUID, if any |
| `message` | `str` | Human-readable notification text |
| `created_at` | `datetime` | UTC time of the triggering event |
| `read` | `bool` | Whether the notification has been marked read |

---

## Error Handling

```python
from anoncore.exceptions import (
    AuthenticationError,
    SuspendedAccountError,
    SessionExpiredError,
    ModerationError,
    NotConnectedError,
    APIError,
    AnonCoreError,
)

try:
    session = await anon.auth.login(Credentials("user@example.com", "wrong"))
except AuthenticationError as e:
    print("Bad credentials:", e)
except SuspendedAccountError as e:
    print("Account banned:", e)

try:
    await anon.post.create_post("TOTALLY FINE CONTENT!!!")
except ModerationError as e:
    print("Flagged by moderation:", e)

# Catch all SDK errors
try:
    ...
except AnonCoreError as e:
    print("SDK error:", e)
```

| Exception | When raised |
|-----------|-------------|
| `AuthenticationError` | Invalid email or password |
| `SuspendedAccountError` | Account has been banned (`403`) |
| `SessionExpiredError` | JWT expired and cannot be refreshed |
| `ModerationError` | Content rejected by the moderation pipeline |
| `NotConnectedError` | WebSocket not open when an operation requires it |
| `APIError` | Unexpected non-2xx HTTP response; has `.status_code` attribute |
| `ConnectionError` | Network-level failure |

---

## Running Tests

```bash
cd sdk
pip install -e ".[dev]"
pytest -v
```

Tests use `respx` for HTTP mocking and `pytest-asyncio` for async test cases.  
No real backend is needed to run the test suite.
