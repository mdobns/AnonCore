"""Custom exceptions for the AnonCore SDK."""


class AnonCoreError(Exception):
    """Base exception for all AnonCore SDK errors."""


class AuthenticationError(AnonCoreError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""


class SessionExpiredError(AnonCoreError):
    """Raised when the current session JWT has expired and cannot be refreshed."""


class SuspendedAccountError(AnonCoreError):
    """Raised when the user's permanent account has been banned/suspended."""


class ModerationError(AnonCoreError):
    """Raised when content is rejected by the moderation engine (HTTP 403)."""

    def __init__(self, message: str = "Content flagged by moderation engine."):
        super().__init__(message)


class ConnectionError(AnonCoreError):  # noqa: A001
    """Raised when the WebSocket or HTTP connection to the backend fails."""


class NotConnectedError(AnonCoreError):
    """Raised when an operation requires an active WebSocket but none exists."""


class APIError(AnonCoreError):
    """Raised for unexpected non-2xx responses from the backend API."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")
