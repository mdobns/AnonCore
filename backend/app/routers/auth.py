"""Auth router – /auth/login, /auth/logout, /auth/refresh."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..models import UserAccount
from ..services.persona import generate_persona
from .security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    validate_api_key,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    session_alias: str
    access_token: str
    token_type: str = "bearer"
    expires_at: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_api_key: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    """Create a new user account and return an initial session."""
    validate_api_key(x_api_key, settings)

    # Check for duplicate email
    existing = await db.scalar(
        select(UserAccount).where(UserAccount.email == body.email)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = UserAccount(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # get the auto-generated id

    persona = generate_persona()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    token = create_access_token(
        user_id=str(user.id),
        persona=persona,
        settings=settings,
    )
    return TokenResponse(
        session_alias=persona,
        access_token=token,
        expires_at=expires_at.isoformat(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_api_key: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    """Authenticate and return a fresh transient persona + JWT."""
    validate_api_key(x_api_key, settings)

    user: UserAccount | None = await db.scalar(
        select(UserAccount).where(UserAccount.email == body.email)
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is banned or suspended.",
        )

    persona = generate_persona()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    token = create_access_token(
        user_id=str(user.id),
        persona=persona,
        settings=settings,
    )
    return TokenResponse(
        session_alias=persona,
        access_token=token,
        expires_at=expires_at.isoformat(),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: UserAccount = Depends(get_current_user),
) -> MessageResponse:
    """Invalidate the current session.

    Because JWTs are stateless the server-side logout is a no-op; the SDK
    discards the token on the client side.  This endpoint exists so the SDK
    has a hook for server-side audit logging if needed in the future.
    """
    return MessageResponse(message="Logged out successfully.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    current_user: UserAccount = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Rotate identity: issue a new persona alias and JWT."""
    if current_user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is banned or suspended.",
        )

    persona = generate_persona()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    token = create_access_token(
        user_id=str(current_user.id),
        persona=persona,
        settings=settings,
    )
    return TokenResponse(
        session_alias=persona,
        access_token=token,
        expires_at=expires_at.isoformat(),
    )
