"""Posts router – /posts/ for creating posts, comments, and reports."""

from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..middleware.moderation import run_moderation
from ..models import AuditLog, Comment, Post, UserAccount
from ..services import redis as redis_service
from .security import decode_token, get_current_user, validate_api_key

router = APIRouter(prefix="/posts", tags=["posts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class PostCreate(BaseModel):
    content: str


class CommentCreate(BaseModel):
    content: str


class ReportCreate(BaseModel):
    reason: str
    post_id: Optional[str] = None
    comment_id: Optional[str] = None


class PostResponse(BaseModel):
    id: str
    content: str
    session_alias: str
    created_at: str
    comment_count: int


class CommentResponse(BaseModel):
    id: str
    post_id: str
    content: str
    session_alias: str
    created_at: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_to_response(post: Post, comment_count: int = 0) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        content=post.content,
        session_alias=post.session_alias,
        created_at=post.created_at.isoformat(),
        comment_count=comment_count,
    )


def _comment_to_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=str(comment.id),
        post_id=str(comment.post_id),
        content=comment.content,
        session_alias=comment.session_alias,
        created_at=comment.created_at.isoformat(),
    )


def _get_persona(current_user: UserAccount, authorization: str | None) -> str:
    """Extract the session persona from the Bearer JWT claims."""
    if not authorization:
        return "Unknown"
    token = authorization.removeprefix("Bearer ").strip()
    try:
        from ..config import get_settings as _gs
        settings = _gs()
        payload = decode_token(token, settings)
        return payload.get("persona", "Unknown")
    except Exception:  # noqa: BLE001
        return "Unknown"


async def _handle_strike(
    user: UserAccount,
    violation: str,
    db: AsyncSession,
    settings: Settings,
    post_id: uuid.UUID | None = None,
    comment_id: uuid.UUID | None = None,
) -> None:
    """Increment the user's strike count and ban if threshold is reached."""
    user.strike_count += 1
    log = AuditLog(
        user_id=user.id,
        violation_type=violation,
        detail=f"Strike {user.strike_count}/{settings.max_strikes}",
        post_id=post_id,
        comment_id=comment_id,
    )
    db.add(log)

    if user.strike_count >= settings.max_strikes:
        user.is_banned = True
        log2 = AuditLog(
            user_id=user.id,
            violation_type="auto_suspension",
            detail=f"Banned after {user.strike_count} strikes.",
        )
        db.add(log2)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[PostResponse])
async def get_feed(
    limit: int = 50,
    offset: int = 0,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PostResponse]:
    """Return the global anonymous feed (paginated)."""
    result = await db.execute(
        select(Post)
        .where(Post.is_removed.is_(False))
        .order_by(Post.created_at.desc())
        .limit(min(limit, 100))
        .offset(offset)
    )
    posts = result.scalars().all()

    out = []
    for post in posts:
        count = await db.scalar(
            select(func.count(Comment.id)).where(Comment.post_id == post.id)
        )
        out.append(_post_to_response(post, comment_count=count or 0))
    return out


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreate,
    authorization: Annotated[str | None, Header()] = None,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PostResponse:
    """Create a new anonymous post.

    The content is run through the moderation pipeline before being persisted.
    A ``403`` is returned if the content is flagged; a strike is also recorded.
    """
    if settings.moderation_enabled:
        result = run_moderation(body.content)
        if result.flagged:
            await _handle_strike(
                current_user, result.violation or "flagged", db, settings
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Content flagged by moderation: {result.violation}",
            )

    persona = _get_persona(current_user, authorization)
    post = Post(
        content=body.content,
        session_alias=persona,
        user_id=current_user.id,
    )
    db.add(post)
    await db.flush()

    # Broadcast to all connected WebSocket clients via Redis
    post_data = {
        "id": str(post.id),
        "content": post.content,
        "session_alias": post.session_alias,
        "created_at": post.created_at.isoformat(),
        "comment_count": 0,
    }
    await redis_service.publish("NEW_POST", post_data)

    return _post_to_response(post, comment_count=0)


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    post_id: str,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CommentResponse]:
    """Return all comments for a given post."""
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == uuid.UUID(post_id), Comment.is_removed.is_(False))
        .order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()
    return [_comment_to_response(c) for c in comments]


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: str,
    body: CommentCreate,
    authorization: Annotated[str | None, Header()] = None,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CommentResponse:
    """Add an anonymous comment to a post."""
    post = await db.scalar(
        select(Post).where(Post.id == uuid.UUID(post_id), Post.is_removed.is_(False))
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    if settings.moderation_enabled:
        result = run_moderation(body.content)
        if result.flagged:
            await _handle_strike(
                current_user, result.violation or "flagged", db, settings,
                post_id=uuid.UUID(post_id),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Content flagged by moderation: {result.violation}",
            )

    persona = _get_persona(current_user, authorization)
    comment = Comment(
        post_id=uuid.UUID(post_id),
        content=body.content,
        session_alias=persona,
        user_id=current_user.id,
    )
    db.add(comment)
    await db.flush()

    # Broadcast
    comment_data = {
        "id": str(comment.id),
        "post_id": str(comment.post_id),
        "content": comment.content,
        "session_alias": comment.session_alias,
        "created_at": comment.created_at.isoformat(),
    }
    await redis_service.publish("NEW_COMMENT", comment_data)

    return _comment_to_response(comment)


@router.delete("/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: str,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Soft-delete a post.  Allowed for the post's own author or an admin."""
    post = await db.scalar(
        select(Post).where(Post.id == uuid.UUID(post_id), Post.is_removed.is_(False))
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    is_admin = current_user.email in settings.admin_emails
    if post.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    post.is_removed = True
    log = AuditLog(
        user_id=current_user.id,
        violation_type="post_removed",
        detail=f"Removed by {'admin' if is_admin else 'author'} {current_user.email}.",
        post_id=post.id,
    )
    db.add(log)
    return MessageResponse(message=f"Post {post_id} removed.")


@router.delete("/{post_id}/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    post_id: str,
    comment_id: str,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Soft-delete a comment.  Allowed for the comment's own author or an admin."""
    comment = await db.scalar(
        select(Comment).where(
            Comment.id == uuid.UUID(comment_id),
            Comment.post_id == uuid.UUID(post_id),
            Comment.is_removed.is_(False),
        )
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

    is_admin = current_user.email in settings.admin_emails
    if comment.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    comment.is_removed = True
    log = AuditLog(
        user_id=current_user.id,
        violation_type="comment_removed",
        detail=f"Removed by {'admin' if is_admin else 'author'} {current_user.email}.",
        comment_id=comment.id,
    )
    db.add(log)
    return MessageResponse(message=f"Comment {comment_id} removed.")


@router.post("/report", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def report_content(
    body: ReportCreate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Report a post or comment for admin review."""
    if not body.post_id and not body.comment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one of post_id or comment_id.",
        )

    log = AuditLog(
        user_id=current_user.id,
        violation_type="user_report",
        detail=body.reason,
        post_id=uuid.UUID(body.post_id) if body.post_id else None,
        comment_id=uuid.UUID(body.comment_id) if body.comment_id else None,
    )
    db.add(log)
    return MessageResponse(message="Report submitted. Thank you.")
