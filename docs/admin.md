# Admin Account Guide

This guide explains what an admin account is in AnonCore, how to create one, how to promote or revoke admin privileges, and how to use the admin interface.

---

## How Admin Access Works

AnonCore does **not** have a separate admin account type stored in the database. Admin privileges are granted at the configuration level: any registered user whose email address appears in the `ADMIN_EMAILS_RAW` environment variable is automatically treated as an admin by the backend.

```
Regular account + email in ADMIN_EMAILS_RAW  ─►  Admin account
```

This means:
- Admin status is controlled entirely through the server configuration, not via a database flag or a sign-up flow.
- You can promote or demote an account without touching the database — just update the environment variable and restart the backend.
- A banned account whose email is in `ADMIN_EMAILS_RAW` is **still blocked** by the ban check in `/auth/login` before the admin check runs.

---

## Step-by-Step: Creating Your First Admin Account

### Step 1 — Register a normal user account

Use the `/auth/register` endpoint to create the account you want to promote:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "a-strong-password"}'
```

A successful response returns a JWT and an anonymous persona:

```json
{
  "session_alias": "Neon-Raven-404",
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_at": "2026-03-09T10:00:00+00:00"
}
```

> You can also register the account through the web frontend at `http://localhost:3000`.

---

### Step 2 — Add the email to `ADMIN_EMAILS_RAW`

Open your backend environment file (`backend/.env`) and set the `ADMIN_EMAILS_RAW` variable:

```bash
# Single admin
ADMIN_EMAILS_RAW=admin@example.com

# Multiple admins (comma-separated, no spaces required)
ADMIN_EMAILS_RAW=admin@example.com,security@example.com,ops@example.com
```

If you are using Docker Compose you can set the variable in the root `.env` file or inline:

```bash
ADMIN_EMAILS_RAW=admin@example.com docker compose up --build
```

---

### Step 3 — Restart the backend

The settings are read at startup via `lru_cache`. You must restart the backend process for the change to take effect.

```bash
# Manual / dev
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker Compose
docker compose restart backend
```

---

### Step 4 — Verify admin access

Log in with the promoted account and call any admin endpoint:

```bash
# 1. Log in to get a JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"a-strong-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Call an admin endpoint
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer $TOKEN"
```

A `200` response with the user list confirms admin access is working. A `403` response means the email was not found in `ADMIN_EMAILS_RAW` (double-check the variable value and that the backend was restarted).

---

## Promoting and Revoking Admins

### Promote an existing user

1. Add their email to `ADMIN_EMAILS_RAW` (comma-separated).
2. Restart the backend.

### Revoke admin privileges

1. Remove their email from `ADMIN_EMAILS_RAW`.
2. Restart the backend.

Active JWTs issued before the restart will continue to work until they expire (default 60 minutes). If you need to invalidate access immediately, also rotate `SECRET_KEY` — this invalidates **all** existing tokens for every user.

---

## Admin Endpoints Reference

All admin routes share these requirements:
- **Authentication:** `Authorization: Bearer <JWT>` header
- **Admin check:** The JWT's email must appear in `ADMIN_EMAILS_RAW`
- **Base path:** `/admin`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | List all registered accounts (email, strike count, ban status) |
| `POST` | `/admin/users/{user_id}/ban` | Permanently ban a user account |
| `POST` | `/admin/users/{user_id}/unban` | Lift a ban and reset the strike counter |
| `POST` | `/admin/users/{user_id}/reset-strikes` | Reset the strike counter without changing ban status |
| `DELETE` | `/admin/posts/{post_id}` | Soft-delete a post (`is_removed = true`) |
| `DELETE` | `/admin/comments/{comment_id}` | Soft-delete a comment |
| `GET` | `/admin/audit-logs` | Retrieve moderation audit entries (default 100, max 500) |

> You can also explore and test all admin routes interactively in the Swagger UI at `http://localhost:8000/docs`.

---

## Admin UI (Frontend)

When logged in as an admin, the AnonCore frontend displays an **Admin** link in the sidebar. The admin console provides two tabs:

- **Users** — view all accounts; ban, unban, or reset strikes with a single click.
- **Audit Log** — chronological log of every moderation action including the acting admin's persona, action type, and timestamp.

---

## Security Recommendations

| Recommendation | Why it matters |
|----------------|---------------|
| Use a dedicated email address for each admin (e.g. `admin@yourorg.com`) | Makes it easy to identify and revoke specific admins |
| Set a strong `SECRET_KEY` and rotate it periodically | Invalidates all tokens on rotation; limits the blast radius of a stolen token |
| Keep `ADMIN_EMAILS_RAW` to the minimum number of people needed | Reduces the attack surface for privilege escalation |
| Never commit `.env` files to source control | Admin emails and other secrets would be exposed |
| Use separate `VALID_API_KEYS` for production and development | Prevents dev keys from being used against a production instance |

---

## Troubleshooting

### `403 Admin access required`

- Confirm the email in `ADMIN_EMAILS_RAW` exactly matches the email used to register the account (case-sensitive).
- Confirm the backend was restarted after changing the environment variable.
- Confirm you are using a JWT obtained **after** the backend restart.

### Backend does not pick up the new `ADMIN_EMAILS_RAW`

Settings are cached with `lru_cache`. A full process restart (not just a file save with `--reload`) is required when changing environment variables.

### Admin UI does not appear in the frontend

The frontend determines admin status from the `/auth/login` response. Log out and log back in after granting admin access so the frontend re-fetches the `isAdmin` flag.
