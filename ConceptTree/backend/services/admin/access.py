from __future__ import annotations

from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, Response, status

from config import settings
from database import DbSession, get_db
from utils.auth import create_access_token, verify_token
from utils.password import verify_password


ADMIN_COOKIE_NAME = "concept_tree_admin_session"


def _admin_row(db: DbSession, user_id: str):
    return db.execute(
        """
        SELECT users.id, users.email, users.password_hash
        FROM users
        JOIN user_roles
          ON user_roles.user_id = users.id AND user_roles.role = 'admin'
        WHERE users.id = ?
        """,
        (user_id,),
    ).fetchone()


def authenticate_admin(db: DbSession, user_id: str, password: str) -> dict:
    row = _admin_row(db, user_id)
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_ACCESS_DENIED", "message": "管理员验证失败"},
        )
    return {"id": str(row["id"]), "email": row["email"]}


def create_admin_token(user_id: str) -> str:
    return create_access_token(
        {"sub": user_id, "scope": "admin"},
        expires_delta=timedelta(minutes=settings.ADMIN_SESSION_TTL_MINUTES),
    )


def set_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=settings.ADMIN_SESSION_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.ADMIN_COOKIE_SECURE,
        samesite="strict",
        path="/api/admin",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        httponly=True,
        secure=settings.ADMIN_COOKIE_SECURE,
        samesite="strict",
        path="/api/admin",
    )


def get_admin_subject(
    admin_token: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
) -> str:
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ADMIN_SESSION_REQUIRED", "message": "需要管理员会话"},
        )

    payload = verify_token(admin_token)
    user_id = payload.get("sub")
    if not user_id or payload.get("scope") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_ADMIN_SESSION", "message": "管理员会话无效"},
        )
    return str(user_id)


def require_admin(
    user_id: str = Depends(get_admin_subject),
    db: DbSession = Depends(get_db),
) -> str:
    if not _admin_row(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_ACCESS_DENIED", "message": "无管理员权限"},
        )
    return user_id
