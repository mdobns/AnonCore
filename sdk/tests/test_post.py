"""Tests for PostModule."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
import httpx
import respx

from anoncore import AnonCore, SDKConfig, SessionInfo
from anoncore.auth import AuthModule
from anoncore.exceptions import APIError, ModerationError, NotConnectedError
from anoncore.models import Comment, Post


BASE_URL = "http://test-server"
EXPIRES = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()

POST_RESPONSE = {
    "id": "post-123",
    "content": "Hello world",
    "session_alias": "Neon-Raven-404",
    "created_at": datetime.now(tz=timezone.utc).isoformat(),
    "comment_count": 0,
}

COMMENT_RESPONSE = {
    "id": "comment-456",
    "post_id": "post-123",
    "content": "Nice post!",
    "session_alias": "Silent-Fox-82",
    "created_at": datetime.now(tz=timezone.utc).isoformat(),
}


@pytest.fixture
def authenticated_sdk() -> AnonCore:
    config = SDKConfig(api_key="test-key", base_url=BASE_URL, ws_url="ws://test-server")
    sdk = AnonCore(config)
    # Inject a fake session without hitting the network
    sdk._auth._session = SessionInfo(
        persona="Neon-Raven-404",
        jwt="fake.jwt",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
    )
    return sdk


@pytest.mark.asyncio
async def test_create_post_success(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/").mock(
            return_value=httpx.Response(201, json=POST_RESPONSE)
        )
        post = await authenticated_sdk.post.create_post("Hello world")

    assert isinstance(post, Post)
    assert post.id == "post-123"
    assert post.content == "Hello world"
    assert post.session_alias == "Neon-Raven-404"


@pytest.mark.asyncio
async def test_create_post_moderation_rejected(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/").mock(
            return_value=httpx.Response(
                403, json={"detail": "Content flagged: hate speech"}
            )
        )
        with pytest.raises(ModerationError) as exc_info:
            await authenticated_sdk.post.create_post("bad content")
    assert "flagged" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_post_unauthenticated() -> None:
    config = SDKConfig(api_key="test-key", base_url=BASE_URL, ws_url="ws://test-server")
    sdk = AnonCore(config)  # no login
    with pytest.raises(NotConnectedError):
        await sdk.post.create_post("Hello")


@pytest.mark.asyncio
async def test_create_post_api_error(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        with pytest.raises(APIError) as exc_info:
            await authenticated_sdk.post.create_post("Hello")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_add_comment_success(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/post-123/comments").mock(
            return_value=httpx.Response(201, json=COMMENT_RESPONSE)
        )
        comment = await authenticated_sdk.post.add_comment("post-123", "Nice post!")

    assert isinstance(comment, Comment)
    assert comment.id == "comment-456"
    assert comment.post_id == "post-123"
    assert comment.content == "Nice post!"


@pytest.mark.asyncio
async def test_add_comment_moderation_rejected(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/post-123/comments").mock(
            return_value=httpx.Response(
                403, json={"detail": "Content flagged: profanity"}
            )
        )
        with pytest.raises(ModerationError):
            await authenticated_sdk.post.add_comment("post-123", "bad comment")


@pytest.mark.asyncio
async def test_report_content(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/posts/report").mock(
            return_value=httpx.Response(204)
        )
        # Should not raise
        await authenticated_sdk.post.report_content(
            post_id="post-123", reason="spam"
        )


@pytest.mark.asyncio
async def test_report_content_requires_id(authenticated_sdk: AnonCore) -> None:
    with pytest.raises(ValueError):
        await authenticated_sdk.post.report_content(reason="spam")


@pytest.mark.asyncio
async def test_get_feed(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/posts/").mock(
            return_value=httpx.Response(200, json=[POST_RESPONSE])
        )
        posts = await authenticated_sdk.post.get_feed()

    assert len(posts) == 1
    assert posts[0].id == "post-123"


@pytest.mark.asyncio
async def test_get_comments(authenticated_sdk: AnonCore) -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/posts/post-123/comments").mock(
            return_value=httpx.Response(200, json=[COMMENT_RESPONSE])
        )
        comments = await authenticated_sdk.post.get_comments("post-123")

    assert len(comments) == 1
    assert comments[0].id == "comment-456"
