"""Admin router – protected routes for strike management and moderation."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..models import AuditLog, Comment, Post, UserAccount
from .security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Simple admin-role guard (extend to real RBAC as needed)
# ---------------------------------------------------------------------------

def require_admin(
    current_user: UserAccount = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UserAccount:
    """Raise 403 if the user is not in the configured admin email list."""
    admin_emails = settings.admin_emails
    if current_user.email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class UserSummary(BaseModel):
    id: str
    email: str
    is_banned: bool
    strike_count: int


class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    violation_type: str
    detail: str
    timestamp: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/users", response_model=List[UserSummary])
async def list_users(
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[UserSummary]:
    """List all user accounts."""
    result = await db.execute(select(UserAccount).order_by(UserAccount.created_at))
    users = result.scalars().all()
    return [
        UserSummary(
            id=str(u.id),
            email=u.email,
            is_banned=u.is_banned,
            strike_count=u.strike_count,
        )
        for u in users
    ]


@router.post("/users/{user_id}/ban", response_model=MessageResponse)
async def ban_user(
    user_id: str,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Permanently ban a user by their account ID."""
    user = await db.scalar(select(UserAccount).where(UserAccount.id == uuid.UUID(user_id)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_banned = True
    log = AuditLog(
        user_id=user.id,
        violation_type="manual_ban",
        detail=f"Banned by admin {admin.email}.",
    )
    db.add(log)
    return MessageResponse(message=f"User {user_id} has been banned.")


@router.post("/users/{user_id}/unban", response_model=MessageResponse)
async def unban_user(
    user_id: str,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Lift a ban from a user account."""
    user = await db.scalar(select(UserAccount).where(UserAccount.id == uuid.UUID(user_id)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_banned = False
    user.strike_count = 0
    log = AuditLog(
        user_id=user.id,
        violation_type="manual_unban",
        detail=f"Unbanned by admin {admin.email}.",
    )
    db.add(log)
    return MessageResponse(message=f"User {user_id} has been unbanned.")


@router.post("/users/{user_id}/reset-strikes", response_model=MessageResponse)
async def reset_strikes(
    user_id: str,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset the strike counter for a user."""
    user = await db.scalar(select(UserAccount).where(UserAccount.id == uuid.UUID(user_id)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    old_count = user.strike_count
    user.strike_count = 0
    log = AuditLog(
        user_id=user.id,
        violation_type="strikes_reset",
        detail=f"Strikes reset from {old_count} by admin {admin.email}.",
    )
    db.add(log)
    return MessageResponse(message=f"Strike count reset for user {user_id}.")


@router.delete("/posts/{post_id}", response_model=MessageResponse)
async def remove_post(
    post_id: str,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Soft-delete a post (marks is_removed=True)."""
    post = await db.scalar(select(Post).where(Post.id == uuid.UUID(post_id)))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    post.is_removed = True
    log = AuditLog(
        user_id=post.user_id,
        violation_type="post_removed",
        detail=f"Removed by admin {admin.email}.",
        post_id=post.id,
    )
    db.add(log)
    return MessageResponse(message=f"Post {post_id} removed.")


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def remove_comment(
    comment_id: str,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Soft-delete a comment."""
    comment = await db.scalar(select(Comment).where(Comment.id == uuid.UUID(comment_id)))
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    comment.is_removed = True
    log = AuditLog(
        user_id=comment.user_id,
        violation_type="comment_removed",
        detail=f"Removed by admin {admin.email}.",
        comment_id=comment.id,
    )
    db.add(log)
    return MessageResponse(message=f"Comment {comment_id} removed.")


@router.get("/audit-logs", response_model=List[AuditLogEntry])
async def get_audit_logs(
    limit: int = 100,
    admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[AuditLogEntry]:
    """Return the latest audit log entries."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(min(limit, 500))
    )
    logs = result.scalars().all()
    return [
        AuditLogEntry(
            id=str(lg.id),
            user_id=str(lg.user_id),
            violation_type=lg.violation_type,
            detail=lg.detail,
            timestamp=lg.timestamp.isoformat(),
        )
        for lg in logs
    ]
