"""AuthModule – handles login, logout, and identity rotation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from .exceptions import (
    APIError,
    AuthenticationError,
    SessionExpiredError,
    SuspendedAccountError,
)
from .models import Credentials, SDKConfig, SessionInfo

logger = logging.getLogger(__name__)


class AuthModule:
    """Manages authentication and session persona lifecycle.

    The Ghost Protocol
    ------------------
    Each call to :meth:`login` requests a *fresh* ``session_alias`` (persona)
    from the backend.  The persona is what every other part of the SDK exposes
    to the UI layer – the permanent account token is never surfaced.

    Usage::

        auth = AuthModule(config, http_client)
        session = await auth.login(Credentials(email="...", password="..."))
        print(session.persona)   # e.g. "Neon-Raven-404"
        await auth.logout()
    """

    def __init__(self, config: SDKConfig, http: httpx.AsyncClient) -> None:
        self._config = config
        self._http = http
        self._session: Optional[SessionInfo] = None
        self._refresh_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session(self) -> Optional[SessionInfo]:
        """Return the current :class:`~anoncore.models.SessionInfo`, or ``None``."""
        return self._session

    @property
    def is_authenticated(self) -> bool:
        """``True`` when a valid session is held."""
        return self._session is not None

    async def login(self, credentials: Credentials) -> SessionInfo:
        """Authenticate and obtain a new transient persona.

        Parameters
        ----------
        credentials:
            User's email and password.

        Returns
        -------
        SessionInfo
            The newly created session including persona alias and JWT.

        Raises
        ------
        AuthenticationError
            If the credentials are rejected by the server.
        SuspendedAccountError
            If the account has been permanently banned.
        APIError
            For any other non-2xx response.
        """
        payload = {
            "email": credentials.email,
            "password": credentials.password,
        }
        headers = {"X-API-Key": self._config.api_key}

        try:
            response = await self._http.post(
                f"{self._config.base_url}/auth/login",
                json=payload,
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise AuthenticationError(f"Network error during login: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError("Invalid email or password.")
        if response.status_code == 403:
            detail = response.json().get("detail", "")
            if "banned" in detail.lower() or "suspended" in detail.lower():
                raise SuspendedAccountError(detail)
            raise AuthenticationError(detail)
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)

        data = response.json()
        self._session = SessionInfo(
            persona=data["session_alias"],
            jwt=data["access_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]).replace(
                tzinfo=timezone.utc
            ),
        )
        logger.info("Logged in as persona '%s'.", self._session.persona)
        self._start_refresh_loop()
        return self._session

    async def logout(self) -> None:
        """Invalidate the current session on the server and clear local state.

        After calling this the SDK no longer holds any identity information,
        honouring the "true anonymity" requirement.
        """
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()

        if self._session:
            try:
                await self._http.post(
                    f"{self._config.base_url}/auth/logout",
                    headers=self._auth_headers(),
                )
            except Exception:  # noqa: BLE001
                logger.debug("Logout request failed (server may be unreachable).")
            finally:
                self._session = None
                logger.info("Session cleared – identity wiped.")

    async def refresh_identity(self) -> SessionInfo:
        """Rotate the current persona, obtaining a brand-new alias.

        This calls ``/auth/refresh`` which returns a new ``session_alias``
        and a fresh JWT while keeping the same permanent account on the
        server side.

        Raises
        ------
        SessionExpiredError
            When the current JWT can no longer be used to refresh.
        """
        if not self._session:
            raise SessionExpiredError("No active session to refresh.")

        try:
            response = await self._http.post(
                f"{self._config.base_url}/auth/refresh",
                headers=self._auth_headers(),
            )
        except httpx.RequestError as exc:
            raise SessionExpiredError(f"Network error during refresh: {exc}") from exc

        if response.status_code == 401:
            self._session = None
            raise SessionExpiredError("Session expired; please log in again.")
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)

        data = response.json()
        old_persona = self._session.persona
        self._session = SessionInfo(
            persona=data["session_alias"],
            jwt=data["access_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]).replace(
                tzinfo=timezone.utc
            ),
        )
        logger.info(
            "Identity rotated: '%s' → '%s'.", old_persona, self._session.persona
        )
        return self._session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def auth_headers(self) -> dict[str, str]:
        """Return HTTP headers required for authenticated requests."""
        return self._auth_headers()

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"X-API-Key": self._config.api_key}
        if self._session:
            headers["Authorization"] = f"Bearer {self._session.jwt}"
        return headers

    def _start_refresh_loop(self) -> None:
        """Schedule automatic token refresh before expiry."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        self._refresh_task = asyncio.create_task(self._auto_refresh())

    async def _auto_refresh(self) -> None:
        """Background task: refresh the JWT 60 seconds before it expires."""
        while self._session:
            now = datetime.now(tz=timezone.utc)
            seconds_left = (self._session.expires_at - now).total_seconds()
            sleep_for = max(seconds_left - 60, 5)
            await asyncio.sleep(sleep_for)
            if not self._session:
                break
            try:
                await self.refresh_identity()
            except (SessionExpiredError, APIError) as exc:
                logger.warning("Auto-refresh failed: %s", exc)
                break
