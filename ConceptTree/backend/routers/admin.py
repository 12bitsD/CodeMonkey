from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from database import DbSession, get_db
from config import settings
from models_admin import AdminSessionRequest
from services.admin.access import (
    ADMIN_COOKIE_NAME,
    authenticate_admin,
    clear_admin_cookie,
    create_admin_token,
    require_admin,
    set_admin_cookie,
)
from utils.auth import add_token_to_blacklist, get_current_user_id
from utils.limiter import limiter


router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/auth/session")
@limiter.limit("5/15minutes")
def create_admin_session(
    request: Request,
    payload: AdminSessionRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
):
    admin = authenticate_admin(db, user_id, payload.password)
    set_admin_cookie(response, create_admin_token(user_id))
    return {
        "success": True,
        "data": {
            "user": {"id": admin["id"], "email": admin["email"], "role": "admin"},
            "expiresIn": 60 * settings.ADMIN_SESSION_TTL_MINUTES,
        },
    }


@router.delete("/auth/session")
def delete_admin_session(
    request: Request,
    response: Response,
    admin_user_id: str = Depends(require_admin),
):
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if token:
        add_token_to_blacklist(token)
    clear_admin_cookie(response)
    return {"success": True, "data": {"message": "管理员会话已结束"}}


@router.get("/me")
def get_admin_identity(admin_user_id: str = Depends(require_admin)):
    return {
        "success": True,
        "data": {"user": {"id": admin_user_id, "role": "admin"}},
    }
