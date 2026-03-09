"""
AnonCore Python SDK
A production-ready SDK for the AnonCore anonymous posting platform.
Implements the Ghost Protocol with Double-Token System.
"""

from .client import AnonCore
from .models import (
    SessionState,
    Post,
    Comment,
    Event,
    User,
    Notification,
)
from .exceptions import (
    AnonCoreError,
    AuthenticationError,
    ConnectionError,
    ModerationError,
    SessionError,
)

__version__ = "0.1.0"
__all__ = [
    "AnonCore",
    "SessionState",
    "Post",
    "Comment",
    "Event",
    "User",
    "Notification",
    "AnonCoreError",
    "AuthenticationError",
    "ConnectionError",
    "ModerationError",
    "SessionError",
]