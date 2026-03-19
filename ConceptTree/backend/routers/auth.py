"""
Authentication router — handles account creation, login, and logout for the ConceptTree API.

This is the entry point for all user identity operations. It exposes three endpoints
under the ``/api/auth`` prefix:

- ``POST /register`` — create a new account and receive a JWT (JSON Web Token)
- ``POST /login``    — verify credentials and receive a JWT
- ``POST /logout``   — signal intent to log out (token is invalidated client-side only)

**Response envelope:**
All endpoints return a consistent JSON envelope::

    # Success
    {"success": true,  "data":  { ... }}

    # Failure
    {"success": false, "error": {"code": "ERROR_CODE", "message": "Human-readable reason"}}

**JWT lifetime:** 604 800 seconds (7 days). Store the token and send it in every
subsequent request as ``Authorization: Bearer <token>``.
"""

import re
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database import get_db_context
from models import LoginRequest, RegisterRequest
from utils.password import hash_password, verify_password
from utils.auth import create_access_token, get_current_user_id
from utils.id_generator import generate_user_id, generate_profile_id

router = APIRouter(prefix="/api/auth", tags=["认证"])


def validate_email(email: str) -> bool:
    """Return ``True`` if ``email`` matches a standard email address pattern.

    Uses a simple regex: ``local-part @ domain . tld`` (TLD must be ≥ 2 chars).
    Does **not** perform DNS or mailbox-existence checks.

    Args:
        email: The email address string to validate.

    Returns:
        ``True`` if the format is valid, ``False`` otherwise.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@router.post("/register")
def register(req: RegisterRequest):
    """Create a new user account and return a JWT for immediate use.

    Registration is atomic: a ``users`` row and a default ``user_profiles`` row
    are created in the same database transaction. The profile starts with
    beginner-level defaults (``programming_level`` = "入门", ``math_level`` = "入门").

    Args:
        req: Registration payload with fields:
            - ``email``    (str) — must be a valid email address format.
            - ``password`` (str) — minimum 6 characters.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "user":  {"id": "<user_id>", "email": "<email>"},
                "token": "<jwt_string>"
              }
            }

    Raises:
        400 INVALID_EMAIL:   ``email`` fails format validation.
        400 WEAK_PASSWORD:   ``password`` is fewer than 6 characters.
        409 EMAIL_EXISTS:    ``email`` is already registered.
    """
    # Validate email format before touching the database
    if not validate_email(req.email):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "INVALID_EMAIL", "message": "邮箱格式不正确"},
            },
        )

    # Enforce minimum password length
    if len(req.password) < 6:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "密码长度至少6位"},
            },
        )

    with get_db_context() as db:
        # Reject duplicate emails before attempting insert
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (req.email,)
        ).fetchone()

        if existing:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": {"code": "EMAIL_EXISTS", "message": "邮箱已被注册"},
                },
            )

        # Create the user record with a hashed password
        user_id = generate_user_id()
        password_hash = hash_password(req.password)

        db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, req.email, password_hash),
        )

        # Create a blank learning profile linked to the new user
        profile_id = generate_profile_id()
        db.execute(
            """INSERT INTO user_profiles (
                   id,
                   user_id,
                   occupation,
                   education,
                   programming_level,
                   math_level,
                   abilities,
                   mastered_knowledge
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (profile_id, user_id, None, None, "入门", "入门", "[]", "[]"),
        )

        db.commit()

        # Issue a JWT so the caller is immediately authenticated
        token = create_access_token(data={"sub": user_id})

        return {
            "success": True,
            "data": {
                "user": {"id": user_id, "email": req.email},
                "token": token,
            },
        }


@router.post("/login")
def login(req: LoginRequest):
    """Authenticate with email and password and return a JWT valid for 7 days.

    Credentials are verified by looking up the user by email and running a
    constant-time password hash comparison. The error message is intentionally
    generic ("邮箱或密码错误") to avoid leaking whether the email exists.

    Args:
        req: Login payload with fields:
            - ``email``    (str) — registered email address.
            - ``password`` (str) — account password.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "user":      {"id": "<user_id>", "email": "<email>"},
                "token":     "<jwt_string>",
                "expiresIn": 604800
              }
            }

        ``expiresIn`` is in seconds (604 800 s = 7 days).

    Raises:
        401 INVALID_CREDENTIALS: Email not found or password does not match.
    """
    with get_db_context() as db:
        user = db.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (req.email,),
        ).fetchone()

        if not user or not verify_password(
            req.password,
            user["password_hash"],
        ):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "邮箱或密码错误",
                    },
                },
            )

        # Issue a JWT embedding the user's ID as the subject claim
        token = create_access_token(data={"sub": user["id"]})

        return {
            "success": True,
            "data": {
                "user": {"id": user["id"], "email": user["email"]},
                "token": token,
                "expiresIn": 604800,
            },
        }


@router.post("/logout")
def logout(user_id: str = Depends(get_current_user_id)):
    """Signal logout intent and confirm success.

    **Current limitation:** The server does **not** blacklist the JWT.
    The token remains valid until it expires naturally (7 days). For a
    secure logout, clients must delete the token from local storage immediately
    after calling this endpoint.

    Args:
        user_id: Injected automatically from the ``Authorization`` header via
            the ``get_current_user_id`` dependency. The caller must be authenticated.

    Returns:
        200 JSON::

            {"success": true, "data": {"message": "已登出"}}

    Raises:
        401: Missing or invalid ``Authorization`` header (handled by the dependency).
    """
    # Token blacklisting is not yet implemented.
    # Clients are responsible for discarding the token locally.
    return {"success": True, "data": {"message": "已登出"}}
