"""AnonCore – the main client class that wires all SDK modules together."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from .auth import AuthModule
from .models import Credentials, SDKConfig, SessionInfo
from .notification import NotificationModule
from .post import PostModule
from .stream import StreamModule

logger = logging.getLogger(__name__)


class AnonCore:
    """Top-level AnonCore SDK client.

    This is the single entry point for all SDK functionality.  Create one
    instance per application and use its properties to access the individual
    modules.

    Parameters
    ----------
    config:
        :class:`~anoncore.models.SDKConfig` instance.  Alternatively, pass
        keyword arguments; they are forwarded to ``SDKConfig``.

    Examples
    --------
    Basic login, posting, and real-time feed::

        import asyncio
        from anoncore import AnonCore
        from anoncore.models import SDKConfig, Credentials

        async def main():
            anon = AnonCore(SDKConfig(api_key="my-api-key"))

            session = await anon.auth.login(Credentials("user@example.com", "secret"))
            print(f"Logged in as {session.persona}")

            anon.stream.subscribe(lambda e: print("Event:", e))
            await anon.connect()

            post = await anon.post.create_post("Hello, anonymous world!")
            print(f"Post created: {post.id}")

            await asyncio.sleep(10)
            await anon.disconnect()

        asyncio.run(main())
    """

    def __init__(self, config: SDKConfig | None = None, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if config is None:
            config = SDKConfig(**kwargs)
        self._config = config

        self._http = httpx.AsyncClient(timeout=config.request_timeout)

        # Instantiate modules
        self._auth = AuthModule(config, self._http)
        self._stream = StreamModule(
            ws_url=config.ws_url,
            api_key=config.api_key,
            reconnect_interval=config.reconnect_interval,
        )
        self._post = PostModule(config, self._http, self._auth)
        self._notifications = NotificationModule()

        # Wire stream → notifications
        self._stream.subscribe(self._notifications.handle_event)

    # ------------------------------------------------------------------
    # Module properties
    # ------------------------------------------------------------------

    @property
    def auth(self) -> AuthModule:
        """The :class:`~anoncore.auth.AuthModule` for login/logout/refresh."""
        return self._auth

    @property
    def stream(self) -> StreamModule:
        """The :class:`~anoncore.stream.StreamModule` for the real-time feed."""
        return self._stream

    @property
    def post(self) -> PostModule:
        """The :class:`~anoncore.post.PostModule` for content submission."""
        return self._post

    @property
    def notifications(self) -> NotificationModule:
        """The :class:`~anoncore.notification.NotificationModule` for alerts."""
        return self._notifications

    @property
    def session(self) -> Optional[SessionInfo]:
        """Shortcut to ``auth.session`` – the current transient session."""
        return self._auth.session

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket stream using the current session.

        Must be called *after* :meth:`~anoncore.auth.AuthModule.login`.

        This also registers the current persona with the notification module
        so it can match replies and mentions.
        """
        session = self._auth.session
        if session is None:
            raise RuntimeError("Call auth.login() before connect().")
        self._notifications.watch_persona(session.persona)
        await self._stream.connect(session)

    async def disconnect(self) -> None:
        """Close the WebSocket stream without logging out."""
        await self._stream.disconnect()

    async def login(self, credentials: Credentials) -> SessionInfo:
        """Convenience wrapper: login and immediately open the stream.

        Parameters
        ----------
        credentials:
            User email and password.

        Returns
        -------
        SessionInfo
            The newly created session.
        """
        session = await self._auth.login(credentials)
        self._notifications.watch_persona(session.persona)
        await self._stream.connect(session)
        return session

    async def logout(self) -> None:
        """Convenience wrapper: disconnect the stream then log out.

        The notification history is wiped on logout to ensure true anonymity.
        """
        await self._stream.disconnect()
        await self._auth.logout()
        self._notifications.clear()

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AnonCore":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()
        if not self._http.is_closed:
            await self._http.aclose()
