"""AnonCore SDK – anonymised social platform client library."""

from .client import AnonCore
from .exceptions import (
    AnonCoreError,
    APIError,
    AuthenticationError,
    ConnectionError,
    ModerationError,
    NotConnectedError,
    SessionExpiredError,
    SuspendedAccountError,
)
from .models import (
    Comment,
    Credentials,
    EventType,
    NotificationEntry,
    Post,
    SDKConfig,
    SessionInfo,
    StreamEvent,
)

__all__ = [
    "AnonCore",
    # Exceptions
    "AnonCoreError",
    "APIError",
    "AuthenticationError",
    "ConnectionError",
    "ModerationError",
    "NotConnectedError",
    "SessionExpiredError",
    "SuspendedAccountError",
    # Models
    "Comment",
    "Credentials",
    "EventType",
    "NotificationEntry",
    "Post",
    "SDKConfig",
    "SessionInfo",
    "StreamEvent",
]