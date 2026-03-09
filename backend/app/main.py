"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import create_tables
from .routers.admin import router as admin_router
from .routers.auth import router as auth_router
from .routers.posts import router as posts_router
from .services import redis as redis_service

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="AnonCore API",
    description=(
        "Real-time anonymous social platform backend. "
        "Every post is a global event broadcast to all active sessions."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    logger.info("AnonCore API starting up…")
    await create_tables()


@app.on_event("shutdown")
async def shutdown() -> None:  # pragma: no cover
    logger.info("AnonCore API shutting down…")
    redis = await redis_service.get_redis()
    await redis.aclose()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket – real-time global feed
# ---------------------------------------------------------------------------


@app.websocket("/ws/feed")
async def websocket_feed(ws: WebSocket) -> None:
    """WebSocket endpoint that streams all global events to the client.

    Query parameters
    ----------------
    token : str
        Bearer JWT for authentication.
    api_key : str
        SDK API key.

    The endpoint validates the token, then subscribes to the Redis
    ``global_feed`` channel and forwards every message to the client.
    """
    token = ws.query_params.get("token", "")
    api_key = ws.query_params.get("api_key", "")

    # Validate API key
    if api_key not in settings.api_keys:
        await ws.close(code=1008, reason="Invalid API key.")
        return

    # Validate JWT
    from .routers.security import decode_token

    try:
        payload = decode_token(token, settings)
    except Exception:
        await ws.close(code=1008, reason="Invalid token.")
        return

    await ws.accept()
    logger.info(
        "WebSocket connected for persona '%s'.", payload.get("persona", "unknown")
    )

    try:
        async for event in redis_service.subscribe_to_feed():
            await ws.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as exc:  # noqa: BLE001
        logger.error("WebSocket error: %s", exc)
    finally:
        logger.debug("WebSocket handler exiting.")
