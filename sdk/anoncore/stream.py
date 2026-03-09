"""StreamModule – WebSocket connection and real-time global feed."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, List, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .exceptions import NotConnectedError
from .models import Comment, EventType, Post, SessionInfo, StreamEvent

logger = logging.getLogger(__name__)

StreamCallback = Callable[[StreamEvent], None]


class StreamModule:
    """Manages the persistent WebSocket connection to the backend.

    The backend broadcasts *every* post/comment to all connected clients
    (the "Everyone sees Everything" rule).  :meth:`subscribe` registers a
    callback that is invoked for each incoming event.

    Usage::

        async with stream:
            stream.subscribe(lambda event: print(event))
            await stream.connect(session)
            await asyncio.sleep(60)

    Or without context manager::

        await stream.connect(session)
        stream.subscribe(callback)
        # ...
        await stream.disconnect()
    """

    def __init__(
        self,
        ws_url: str,
        api_key: str,
        reconnect_interval: float = 5.0,
    ) -> None:
        self._ws_url = ws_url.rstrip("/")
        self._api_key = api_key
        self._reconnect_interval = reconnect_interval
        self._callbacks: List[StreamCallback] = []
        self._ws: Optional[websockets.WebSocketClientProtocol] = None  # type: ignore[type-arg]
        self._listen_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self._session: Optional[SessionInfo] = None
        self._running = False
        self._background_tasks: set[asyncio.Task] = set()  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, callback: StreamCallback) -> None:
        """Register *callback* to be called with every :class:`~anoncore.models.StreamEvent`.

        Multiple callbacks can be registered; they are invoked in registration
        order.

        Parameters
        ----------
        callback:
            A callable that accepts a single :class:`~anoncore.models.StreamEvent`
            argument.  It may be a regular function or a coroutine function.
        """
        self._callbacks.append(callback)

    def unsubscribe(self, callback: StreamCallback) -> None:
        """Remove a previously registered callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    async def connect(self, session: SessionInfo) -> None:
        """Open the WebSocket connection and start listening.

        Parameters
        ----------
        session:
            The current :class:`~anoncore.models.SessionInfo`.  Its JWT is
            sent as a query parameter so the backend can validate the
            connection.
        """
        self._session = session
        self._running = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Stream connecting for persona '%s'.", session.persona)

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._running = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None
        logger.info("Stream disconnected.")

    def update_session(self, session: SessionInfo) -> None:
        """Notify the stream of a new session (after identity rotation).

        The current connection is kept alive but the session reference is
        updated so the next reconnect uses the new JWT.
        """
        self._session = session

    @property
    def is_connected(self) -> bool:
        """``True`` when the WebSocket is open."""
        return self._ws is not None and not self._ws.closed

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "StreamModule":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_ws_uri(self) -> str:
        token = self._session.jwt if self._session else ""
        return (
            f"{self._ws_url}/ws/feed"
            f"?token={token}&api_key={self._api_key}"
        )

    async def _listen_loop(self) -> None:
        """Reconnect-aware listen loop."""
        while self._running:
            try:
                uri = self._build_ws_uri()
                async with websockets.connect(uri) as ws:  # type: ignore[attr-defined]
                    self._ws = ws
                    logger.debug("WebSocket connected: %s", uri)
                    async for raw in ws:
                        self._dispatch(raw)
            except ConnectionClosed as exc:
                logger.warning("WebSocket closed: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.warning("WebSocket error: %s", exc)
            finally:
                self._ws = None

            if self._running:
                logger.info(
                    "Reconnecting in %.1f s…", self._reconnect_interval
                )
                await asyncio.sleep(self._reconnect_interval)

    def _dispatch(self, raw: str) -> None:
        """Parse a raw JSON message and call all registered callbacks."""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON message from server: %s", raw[:200])
            return

        event = self._parse_event(payload)
        if event is None:
            return

        for callback in self._callbacks:
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    task = asyncio.create_task(result)
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
            except Exception:  # noqa: BLE001
                logger.exception("Exception in stream callback.")

    def _parse_event(self, payload: dict) -> Optional[StreamEvent]:  # type: ignore[type-arg]
        raw_type = payload.get("type", "")
        try:
            event_type = EventType(raw_type)
        except ValueError:
            logger.debug("Unknown event type '%s' – ignored.", raw_type)
            return None

        data = payload.get("data", {})

        if event_type == EventType.NEW_POST:
            parsed_data: object = Post(
                id=data["id"],
                content=data["content"],
                session_alias=data["session_alias"],
                created_at=datetime.fromisoformat(data["created_at"]),
                comment_count=data.get("comment_count", 0),
            )
        elif event_type == EventType.NEW_COMMENT:
            parsed_data = Comment(
                id=data["id"],
                post_id=data["post_id"],
                content=data["content"],
                session_alias=data["session_alias"],
                created_at=datetime.fromisoformat(data["created_at"]),
            )
        else:
            parsed_data = data

        return StreamEvent(type=event_type, data=parsed_data)
