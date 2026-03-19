"""
JWT-based authentication utilities for FastAPI route protection.

The primary entry point for route authors is ``get_current_user_id``:
inject it via ``Depends()`` on any endpoint that requires a logged-in user.

Key facts every developer must know:
    1. Tokens are signed with HS256 and expire after 7 days by default.
    2. ``SECRET_KEY`` **must** be replaced with a secure random value before
       deploying to production — the default is intentionally insecure.
    3. All validation failures raise HTTP 401 rather than returning None,
       so callers never receive a partially-authenticated state.

Security note:
    ``SECRET_KEY = "your-secret-key-change-in-production"`` is a placeholder.
    Generate a production key with: ``openssl rand -hex 32``
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Return a signed JWT containing ``data`` and an expiry claim.

    Encodes ``data`` into a JWT, appends an ``exp`` claim, and signs the
    result with ``SECRET_KEY`` using the HS256 algorithm.

    Args:
        data: Arbitrary key/value pairs to embed in the token payload.
            Typically ``{"sub": user_id}``.
        expires_delta: How long until the token expires. Defaults to
            ``ACCESS_TOKEN_EXPIRE_DAYS`` (7 days) when omitted.

    Returns:
        A URL-safe, signed JWT string ready to send to the client.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Decode and validate a JWT, returning its payload on success.

    Decodes the token using ``SECRET_KEY`` and the HS256 algorithm.
    Expiry is checked automatically by the ``jose`` library.

    Args:
        token: A raw JWT string, typically extracted from the
            ``Authorization: Bearer <token>`` header.

    Returns:
        The decoded payload as a plain dict (e.g. ``{"sub": "u_abc123", "exp": ...}``).

    Raises:
        fastapi.HTTPException: HTTP 401 if the token is malformed,
            tampered with, or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """FastAPI dependency that extracts the authenticated user's ID from a Bearer token.

    Designed to be used with ``Depends()`` on any protected route. Validates
    the token and returns the ``sub`` claim, which stores the user ID.

    Args:
        credentials: Injected automatically by FastAPI from the
            ``Authorization: Bearer <token>`` header.

    Returns:
        The user ID string stored in the token's ``sub`` claim
        (e.g. ``"u_abc123def456"``).

    Raises:
        fastapi.HTTPException: HTTP 401 if the token is invalid, expired,
            or does not contain a ``sub`` claim.

    Example::

        @router.get("/me")
        async def get_me(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    token = credentials.credentials
    payload = verify_token(token)
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user_id
