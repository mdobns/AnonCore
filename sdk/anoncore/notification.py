"""NotificationModule – session-bound mention and reply notifications."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional

from .models import Comment, EventType, NotificationEntry, Post, StreamEvent

logger = logging.getLogger(__name__)

NotificationCallback = Callable[[NotificationEntry], None]


class NotificationModule:
    """Tracks session-bound notifications for mentions and replies.

    Because identities change every session, notifications are *ephemeral* –
    they only apply while the current persona is active.  On logout the
    history is wiped via :meth:`clear`.

    The module hooks into the :class:`~anoncore.stream.StreamModule` by
    registering itself as a stream callback.  Any ``NEW_COMMENT`` event whose
    parent post was authored by the current persona triggers a notification.

    Usage::

        notifications.watch_persona("Silent-Fox-82")
        notifications.on_notification(lambda n: toast(n.message))

        # The stream module calls notifications.handle_event automatically
        # when connected via AnonCore.connect().
    """

    def __init__(self) -> None:
        self._current_persona: Optional[str] = None
        self._history: List[NotificationEntry] = []
        self._callbacks: List[NotificationCallback] = []
        # Track post IDs authored by the current persona so we can detect replies
        self._own_post_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch_persona(self, persona: str) -> None:
        """Set the active persona alias to watch notifications for.

        Parameters
        ----------
        persona:
            The current session alias (e.g. ``"Silent-Fox-82"``).
        """
        self._current_persona = persona
        logger.debug("NotificationModule watching persona '%s'.", persona)

    def on_notification(self, callback: NotificationCallback) -> None:
        """Register *callback* to be invoked when a new notification arrives.

        Parameters
        ----------
        callback:
            Called with the new :class:`~anoncore.models.NotificationEntry`.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: NotificationCallback) -> None:
        """Unregister a previously registered notification callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    @property
    def history(self) -> List[NotificationEntry]:
        """Return the full notification history for the current session."""
        return list(self._history)

    @property
    def unread_count(self) -> int:
        """Number of unread notifications."""
        return sum(1 for n in self._history if not n.read)

    def mark_read(self, notification_id: str) -> None:
        """Mark a single notification as read.

        Parameters
        ----------
        notification_id:
            The ``id`` field of the :class:`~anoncore.models.NotificationEntry`.
        """
        for entry in self._history:
            if entry.id == notification_id:
                entry.read = True
                return

    def mark_all_read(self) -> None:
        """Mark all notifications in the current session as read."""
        for entry in self._history:
            entry.read = True

    def clear(self) -> None:
        """Wipe the notification history and reset persona tracking.

        Called on logout to ensure true anonymity – once the session ends,
        no trace of the notification history is kept in memory.
        """
        self._history.clear()
        self._own_post_ids.clear()
        self._current_persona = None
        logger.debug("NotificationModule history cleared.")

    # ------------------------------------------------------------------
    # Stream integration
    # ------------------------------------------------------------------

    def handle_event(self, event: StreamEvent) -> None:
        """Process a real-time stream event.

        This method should be registered as a callback on
        :class:`~anoncore.stream.StreamModule` via ``stream.subscribe()``.

        It detects:
        * Posts authored by the current persona (stored for reply matching).
        * Comments on those posts (triggers a notification).
        * Direct @mentions of the current persona alias in any content.
        """
        if not self._current_persona:
            return

        if event.type == EventType.NEW_POST and isinstance(event.data, Post):
            post: Post = event.data
            if post.session_alias == self._current_persona:
                self._own_post_ids.add(post.id)

        elif event.type == EventType.NEW_COMMENT and isinstance(event.data, Comment):
            comment: Comment = event.data
            notification: Optional[NotificationEntry] = None

            # Case 1 – reply to one of our posts
            if comment.post_id in self._own_post_ids:
                notification = NotificationEntry(
                    id=str(uuid.uuid4()),
                    post_id=comment.post_id,
                    comment_id=comment.id,
                    message=(
                        f"{comment.session_alias} replied to your post."
                    ),
                    created_at=datetime.now(tz=timezone.utc),
                )

            # Case 2 – @mention of our persona alias in the comment content
            elif f"@{self._current_persona}" in comment.content:
                notification = NotificationEntry(
                    id=str(uuid.uuid4()),
                    post_id=comment.post_id,
                    comment_id=comment.id,
                    message=(
                        f"{comment.session_alias} mentioned you in a comment."
                    ),
                    created_at=datetime.now(tz=timezone.utc),
                )

            if notification:
                self._history.append(notification)
                self._fire_callbacks(notification)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fire_callbacks(self, entry: NotificationEntry) -> None:
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception:  # noqa: BLE001
                logger.exception("Exception in notification callback.")
