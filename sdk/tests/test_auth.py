"""Tests for AuthModule."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest
import httpx
import respx

from anoncore import AnonCore, Credentials, SDKConfig, SessionInfo
from anoncore.exceptions import (
    AuthenticationError,
    SuspendedAccountError,
    SessionExpiredError,
    APIError,
)


BASE_URL = "http://test-server"
EXPIRES = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()

LOGIN_RESPONSE = {
    "session_alias": "Neon-Raven-404",
    "access_token": "test.jwt.token",
    "expires_at": EXPIRES,
}


@pytest.fixture
def sdk() -> AnonCore:
    config = SDKConfig(api_key="test-key", base_url=BASE_URL, ws_url="ws://test-server")
    return AnonCore(config)


@pytest.mark.asyncio
async def test_login_success(sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        session = await sdk.auth.login(Credentials("user@example.com", "secret"))

    assert isinstance(session, SessionInfo)
    assert session.persona == "Neon-Raven-404"
    assert session.jwt == "test.jwt.token"
    assert sdk.auth.is_authenticated


@pytest.mark.asyncio
async def test_login_invalid_credentials(sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid credentials"})
        )
        with pytest.raises(AuthenticationError):
            await sdk.auth.login(Credentials("bad@example.com", "wrong"))


@pytest.mark.asyncio
async def test_login_suspended_account(sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(403, json={"detail": "Account is banned"})
        )
        with pytest.raises(SuspendedAccountError):
            await sdk.auth.login(Credentials("banned@example.com", "pass"))


@pytest.mark.asyncio
async def test_login_server_error(sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(APIError) as exc_info:
            await sdk.auth.login(Credentials("user@example.com", "pass"))
        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_logout_clears_session(sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        respx.post(f"{BASE_URL}/auth/logout").mock(return_value=httpx.Response(200))
        await sdk.auth.login(Credentials("user@example.com", "secret"))
        assert sdk.auth.is_authenticated
        await sdk.auth.logout()

    assert not sdk.auth.is_authenticated
    assert sdk.auth.session is None


@pytest.mark.asyncio
async def test_refresh_identity(sdk: AnonCore) -> None:
    new_expires = (datetime.now(tz=timezone.utc) + timedelta(hours=2)).isoformat()
    refresh_response = {
        "session_alias": "Silent-Fox-82",
        "access_token": "new.jwt.token",
        "expires_at": new_expires,
    }
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        respx.post(f"{BASE_URL}/auth/refresh").mock(
            return_value=httpx.Response(200, json=refresh_response)
        )
        await sdk.auth.login(Credentials("user@example.com", "secret"))
        new_session = await sdk.auth.refresh_identity()

    assert new_session.persona == "Silent-Fox-82"
    assert new_session.jwt == "new.jwt.token"


@pytest.mark.asyncio
async def test_refresh_without_session_raises(sdk: AnonCore) -> None:
    with pytest.raises(SessionExpiredError):
        await sdk.auth.refresh_identity()


@pytest.mark.asyncio
async def test_session_shortcut(sdk: AnonCore) -> None:
    """sdk.session should mirror sdk.auth.session."""
    assert sdk.session is None
    with respx.mock:
        respx.post(f"{BASE_URL}/auth/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        await sdk.auth.login(Credentials("user@example.com", "secret"))

    assert sdk.session is sdk.auth.session
