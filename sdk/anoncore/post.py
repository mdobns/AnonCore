"""PostModule – create posts, add comments, and report content."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import httpx

from .auth import AuthModule
from .exceptions import APIError, ModerationError, NotConnectedError
from .models import Comment, Post, SDKConfig

logger = logging.getLogger(__name__)


class PostModule:
    """Provides methods for content submission and moderation reporting.

    All requests are authenticated via the current session JWT managed by
    :class:`~anoncore.auth.AuthModule`.  If the backend returns ``403`` the
    moderation engine has flagged the content; a :class:`~anoncore.exceptions.ModerationError`
    is raised so the frontend can display a warning.

    Usage::

        post = await client.post.create_post("Hello, anonymous world!")
        comment = await client.post.add_comment(post.id, "Nice post!")
        await client.post.report_content(post_id=post.id, reason="spam")
    """

    def __init__(self, config: SDKConfig, http: httpx.AsyncClient, auth: AuthModule) -> None:
        self._config = config
        self._http = http
        self._auth = auth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_post(self, content: str) -> Post:
        """Submit a new anonymous post to the global feed.

        Parameters
        ----------
        content:
            Plain-text body of the post.

        Returns
        -------
        Post
            The persisted post object returned by the server.

        Raises
        ------
        NotConnectedError
            If the user is not authenticated.
        ModerationError
            If the content is flagged by the pre-flight moderation filter.
        APIError
            For any other non-2xx response.
        """
        self._require_auth()
        response = await self._http.post(
            f"{self._config.base_url}/posts/",
            json={"content": content},
            headers=self._auth.auth_headers(),
        )
        return self._handle_post_response(response)

    async def add_comment(self, post_id: str, content: str) -> Comment:
        """Add a comment to an existing post.

        Parameters
        ----------
        post_id:
            UUID of the post to comment on.
        content:
            Plain-text body of the comment.

        Returns
        -------
        Comment
            The persisted comment object returned by the server.

        Raises
        ------
        NotConnectedError
            If the user is not authenticated.
        ModerationError
            If the content is flagged by the moderation filter.
        APIError
            For any other non-2xx response.
        """
        self._require_auth()
        response = await self._http.post(
            f"{self._config.base_url}/posts/{post_id}/comments",
            json={"content": content},
            headers=self._auth.auth_headers(),
        )
        return self._handle_comment_response(response)

    async def report_content(
        self,
        reason: str,
        post_id: str | None = None,
        comment_id: str | None = None,
    ) -> None:
        """Report a post or comment for review by admins.

        At least one of *post_id* or *comment_id* must be provided.

        Parameters
        ----------
        reason:
            Short description of why the content is being reported.
        post_id:
            UUID of the post to report.
        comment_id:
            UUID of the comment to report.

        Raises
        ------
        ValueError
            If neither *post_id* nor *comment_id* is supplied.
        NotConnectedError
            If the user is not authenticated.
        APIError
            For any non-2xx response.
        """
        if not post_id and not comment_id:
            raise ValueError("Provide at least one of post_id or comment_id.")
        self._require_auth()
        payload: dict = {"reason": reason}
        if post_id:
            payload["post_id"] = post_id
        if comment_id:
            payload["comment_id"] = comment_id

        response = await self._http.post(
            f"{self._config.base_url}/posts/report",
            json=payload,
            headers=self._auth.auth_headers(),
        )
        if response.status_code not in (200, 201, 204):
            raise APIError(response.status_code, response.text)

    async def get_feed(self, limit: int = 50, offset: int = 0) -> List[Post]:
        """Retrieve a page of posts from the global feed.

        Parameters
        ----------
        limit:
            Maximum number of posts to return (default 50, max 100).
        offset:
            Pagination offset.

        Returns
        -------
        list of Post
        """
        self._require_auth()
        response = await self._http.get(
            f"{self._config.base_url}/posts/",
            params={"limit": limit, "offset": offset},
            headers=self._auth.auth_headers(),
        )
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)
        return [
            Post(
                id=p["id"],
                content=p["content"],
                session_alias=p["session_alias"],
                created_at=_parse_dt(p["created_at"]),
                comment_count=p.get("comment_count", 0),
            )
            for p in response.json()
        ]

    async def get_comments(self, post_id: str) -> List[Comment]:
        """Retrieve all comments for a given post.

        Parameters
        ----------
        post_id:
            UUID of the post.
        """
        self._require_auth()
        response = await self._http.get(
            f"{self._config.base_url}/posts/{post_id}/comments",
            headers=self._auth.auth_headers(),
        )
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)
        return [
            Comment(
                id=c["id"],
                post_id=post_id,
                content=c["content"],
                session_alias=c["session_alias"],
                created_at=_parse_dt(c["created_at"]),
            )
            for c in response.json()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_auth(self) -> None:
        if not self._auth.is_authenticated:
            raise NotConnectedError("You must be logged in to perform this action.")

    def _handle_post_response(self, response: httpx.Response) -> Post:
        if response.status_code == 403:
            detail = response.json().get("detail", "Content flagged by moderation.")
            raise ModerationError(detail)
        if response.status_code not in (200, 201):
            raise APIError(response.status_code, response.text)
        data = response.json()
        return Post(
            id=data["id"],
            content=data["content"],
            session_alias=data["session_alias"],
            created_at=_parse_dt(data["created_at"]),
            comment_count=data.get("comment_count", 0),
        )

    def _handle_comment_response(self, response: httpx.Response) -> Comment:
        if response.status_code == 403:
            detail = response.json().get("detail", "Content flagged by moderation.")
            raise ModerationError(detail)
        if response.status_code not in (200, 201):
            raise APIError(response.status_code, response.text)
        data = response.json()
        return Comment(
            id=data["id"],
            post_id=data["post_id"],
            content=data["content"],
            session_alias=data["session_alias"],
            created_at=_parse_dt(data["created_at"]),
        )


def _parse_dt(value: str) -> datetime:  # noqa: ANN201
    return datetime.fromisoformat(value)
