"""Authentication utilities — JWT creation/verification and password hashing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from packages.common import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    data:
        Claims to embed in the token.  Must include at least ``"sub"``
        (subject / user id) and ``"tenant_id"``.
    expires_delta:
        Custom token lifetime.  Falls back to
        ``settings.ACCESS_TOKEN_EXPIRE_MINUTES``.
    """
    settings = get_settings()
    to_encode = data.copy()

    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, returning the payload dict.

    Raises
    ------
    jose.JWTError
        If the token is expired, tampered with, or otherwise invalid.
    """
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches the bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)
