"""Redis Pub/Sub service for real-time broadcasting."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import redis.asyncio as aioredis

from ..config import get_settings

logger = logging.getLogger(__name__)

GLOBAL_FEED_CHANNEL = "global_feed"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return a shared Redis connection (FastAPI dependency)."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish(event_type: str, data: dict) -> None:
    """Publish a real-time event to the global feed channel.

    Parameters
    ----------
    event_type:
        One of the ``EventType`` values, e.g. ``"NEW_POST"``.
    data:
        JSON-serialisable payload dict.
    """
    try:
        redis = await get_redis()
        message = json.dumps({"type": event_type, "data": data})
        await redis.publish(GLOBAL_FEED_CHANNEL, message)
        logger.debug("Published %s to %s.", event_type, GLOBAL_FEED_CHANNEL)
    except Exception as exc:  # noqa: BLE001
        logger.error("Redis publish failed: %s", exc)


async def subscribe_to_feed() -> AsyncIterator[dict]:
    """Async generator that yields parsed messages from the global feed channel.

    Intended for use inside WebSocket handlers::

        async for event in subscribe_to_feed():
            await ws.send_json(event)
    """
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(GLOBAL_FEED_CHANNEL)
    try:
        async for raw in pubsub.listen():
            if raw["type"] == "message":
                try:
                    yield json.loads(raw["data"])
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from Redis: %s", raw["data"][:200])
    finally:
        await pubsub.unsubscribe(GLOBAL_FEED_CHANNEL)
        await client.aclose()
