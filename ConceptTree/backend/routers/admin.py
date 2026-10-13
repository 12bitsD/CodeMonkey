from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

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
from services.admin.analytics import (
    get_ai_usage,
    get_overview,
    get_session_detail,
    get_timeseries,
    get_user_detail,
    list_sessions,
    list_users,
)
from services.admin.audit import record_admin_read
from utils.auth import add_token_to_blacklist, get_current_user_id
from utils.limiter import limiter
from utils.observability import get_metrics_snapshot


router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _date_range(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    resolved_end = end or datetime.now(timezone.utc)
    resolved_start = start or (resolved_end - timedelta(days=7))
    if resolved_start >= resolved_end:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATE_RANGE", "message": "开始时间必须早于结束时间"},
        )
    if resolved_end - resolved_start > timedelta(days=90):
        raise HTTPException(
            status_code=400,
            detail={"code": "DATE_RANGE_TOO_LARGE", "message": "查询范围不能超过90天"},
        )
    return resolved_start, resolved_end


def _audit_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


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


@router.get("/overview")
def admin_overview(
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    resolved_start, resolved_end = _date_range(start, end)
    data = get_overview(db, resolved_start, resolved_end)
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="dashboard.read",
        resource_type="overview",
        request_id=_audit_request_id(request),
        metadata={"start": resolved_start.isoformat(), "end": resolved_end.isoformat()},
    )
    return {"success": True, "data": {"range": {"start": resolved_start, "end": resolved_end}, **data}}


@router.get("/timeseries")
def admin_timeseries(
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    resolved_start, resolved_end = _date_range(start, end)
    data = get_timeseries(db, resolved_start, resolved_end)
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="dashboard.read",
        resource_type="timeseries",
        request_id=_audit_request_id(request),
    )
    return {"success": True, "data": {"items": data}}


@router.get("/users")
def admin_users(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    data = list_users(db, limit=limit, cursor=cursor)
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="users.list",
        resource_type="user",
        request_id=_audit_request_id(request),
        metadata={"limit": limit},
    )
    return {"success": True, "data": data}


@router.get("/users/{user_id}")
def admin_user_detail(
    user_id: str,
    request: Request,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    data = get_user_detail(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="user.read",
        resource_type="user",
        resource_id=user_id,
        request_id=_audit_request_id(request),
    )
    return {"success": True, "data": data}


@router.get("/sessions")
def admin_sessions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    data = list_sessions(db, limit=limit, cursor=cursor)
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="sessions.list",
        resource_type="session",
        request_id=_audit_request_id(request),
        metadata={"limit": limit},
    )
    return {"success": True, "data": data}


@router.get("/sessions/{session_id}")
def admin_session_detail(
    session_id: str,
    request: Request,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    data = get_session_detail(db, session_id)
    if not data:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在"})
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="session.read",
        resource_type="session",
        resource_id=session_id,
        request_id=_audit_request_id(request),
    )
    return {"success": True, "data": data}


@router.get("/ai-usage")
def admin_ai_usage(
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    admin_user_id: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    resolved_start, resolved_end = _date_range(start, end)
    data = get_ai_usage(db, resolved_start, resolved_end)
    record_admin_read(
        db,
        admin_user_id=admin_user_id,
        action="ai_usage.read",
        resource_type="ai_usage",
        request_id=_audit_request_id(request),
    )
    return {"success": True, "data": {"range": {"start": resolved_start, "end": resolved_end}, **data}}


@router.get("/system-health")
def admin_system_health(admin_user_id: str = Depends(require_admin)):
    return {"success": True, "data": get_metrics_snapshot()}
