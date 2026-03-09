"""Shared data models (dataclasses / typed dicts) used across SDK modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    """Types of real-time stream events emitted by StreamModule."""

    NEW_POST = "NEW_POST"
    NEW_COMMENT = "NEW_COMMENT"
    MODERATION_WARNING = "MODERATION_WARNING"
    SESSION_EXPIRED = "SESSION_EXPIRED"


@dataclass
class SessionInfo:
    """Transient session created on each login."""

    persona: str
    """Human-readable alias for this session, e.g. 'Silent-Fox-82'."""

    jwt: str
    """Short-lived JWT used to authenticate API requests."""

    expires_at: datetime
    """UTC timestamp when the JWT expires."""


@dataclass
class Post:
    """A single anonymised post in the global feed."""

    id: str
    content: str
    session_alias: str
    created_at: datetime
    comment_count: int = 0


@dataclass
class Comment:
    """A comment nested under a Post."""

    id: str
    post_id: str
    content: str
    session_alias: str
    created_at: datetime


@dataclass
class StreamEvent:
    """A real-time event delivered via the WebSocket stream."""

    type: EventType
    data: Any
    """Payload depends on *type*:
    - NEW_POST  → Post
    - NEW_COMMENT → Comment
    - MODERATION_WARNING → dict with 'message'
    - SESSION_EXPIRED → None
    """


@dataclass
class NotificationEntry:
    """A session-bound notification (mention or reply)."""

    id: str
    post_id: str
    comment_id: Optional[str]
    message: str
    created_at: datetime
    read: bool = False


@dataclass
class Credentials:
    """User credentials for authentication."""

    email: str
    password: str


@dataclass
class SDKConfig:
    """Configuration supplied when constructing AnonCore."""

    api_key: str
    base_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000"
    reconnect_interval: float = 5.0
    """Seconds to wait before attempting to reconnect a dropped WebSocket."""
    request_timeout: float = 30.0
    """HTTP request timeout in seconds."""

