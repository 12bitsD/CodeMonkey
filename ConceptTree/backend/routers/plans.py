from datetime import datetime, timezone
from typing import Optional
import json
import uuid
from threading import Lock

from fastapi import APIRouter, Body, Depends, HTTPException

from database import ensure_schema_columns, get_db, transaction
from models import (
    ArchivePlanRequest,
    ErrorResponse,
    PlanCreateRequest,
    PlanCreateResponse,
    PlanListResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
)
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["plans"])

_PLAN_MANAGEMENT_COLUMNS_READY = False
_PLAN_MANAGEMENT_COLUMNS_LOCK = Lock()


def _format_datetime(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _ensure_plan_management_columns(db) -> None:
    global _PLAN_MANAGEMENT_COLUMNS_READY
    if _PLAN_MANAGEMENT_COLUMNS_READY:
        return

    with _PLAN_MANAGEMENT_COLUMNS_LOCK:
        if _PLAN_MANAGEMENT_COLUMNS_READY:
            return

        ensure_schema_columns(
            db,
            {
                "plans": (
                    "start_date",
                    "target_end_date",
                    "study_frequency",
                    "study_days_per_week",
                    "reminder_enabled",
                    "reminder_time",
                    "reminder_timezone",
                    "archived_reason",
                ),
                "nodes": ("target_end_date",),
            },
        )
        _PLAN_MANAGEMENT_COLUMNS_READY = True


def _serialize_plan(plan) -> dict:
    return {
        "id": plan["id"],
        "title": plan["title"],
        "progress": plan["progress"] or 0,
        "total": plan["total"] or 0,
        "status": plan["status"] or "active",
        "lastAccess": _format_datetime(plan["last_access_at"]),
        "createdAt": _format_datetime(plan["created_at"]),
        "startDate": _format_datetime(plan["start_date"]),
        "targetEndDate": _format_datetime(plan["target_end_date"]),
        "studyFrequency": plan["study_frequency"] or "flexible",
        "studyDaysPerWeek": plan["study_days_per_week"] or 3,
        "reminderEnabled": bool(plan["reminder_enabled"]),
        "reminderTime": plan["reminder_time"],
        "reminderTimezone": plan["reminder_timezone"],
        "archivedReason": plan["archived_reason"],
    }


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _json_dumps(value) -> str:
    return json.dumps(_jsonable(value or []), ensure_ascii=False)


def _get_owned_plan(db, plan_id: str, current_user_id: str):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            },
        )
    if plan["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": "Forbidden"},
            },
        )
    return plan


@router.get(
    "/plans",
    response_model=PlanListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_plans(current_user_id: str = Depends(get_current_user_id), db=Depends(get_db)):
    _ensure_plan_management_columns(db)
    plans = db.execute(
        "SELECT * FROM plans WHERE user_id = ? ORDER BY last_access_at DESC, created_at DESC",
        (current_user_id,),
    ).fetchall()
    return {
        "success": True,
        "data": [_serialize_plan(plan) for plan in plans],
    }


@router.post(
    "/plans",
    response_model=PlanCreateResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def create_plan(
    request: PlanCreateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _ensure_plan_management_columns(db)

    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    node_id_map = {node.id: f"{plan_id}_{node.id}" for node in request.nodes}

    with transaction(db):
        db.execute(
            """
            INSERT INTO plans (
                id, user_id, title, original_input, target_node_id, progress, total, status,
                last_access_at, created_at, learning_purpose, start_date, target_end_date,
                study_frequency, study_days_per_week, reminder_enabled, reminder_time,
                reminder_timezone, archived_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                current_user_id,
                request.title,
                request.originalInput,
                node_id_map.get(request.targetNodeId, request.targetNodeId),
                0,
                len([node for node in request.nodes if node.status != "skipped"]),
                "active",
                now,
                now,
                request.learning_purpose,
                request.startDate or now,
                request.targetEndDate,
                request.studyFrequency,
                request.studyDaysPerWeek,
                request.reminderEnabled,
                request.reminderTime,
                request.reminderTimezone,
                None,
            ),
        )

        for node in request.nodes:
            db.execute(
                """
                INSERT INTO nodes (
                    id, plan_id, name, status, x, y, why, what, mastery, prompt,
                    resources, is_target, domain, phase, phase_order, depth_level,
                    target_end_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?, ?::jsonb, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id_map[node.id],
                    plan_id,
                    node.name,
                    node.status.value if hasattr(node.status, "value") else node.status,
                    node.x,
                    node.y,
                    node.why,
                    _json_dumps(node.what),
                    _json_dumps(node.mastery),
                    node.prompt,
                    _json_dumps(node.resources),
                    node.isTarget,
                    node.domain,
                    node.phase,
                    node.phase_order,
                    node.depth_level,
                    node.targetEndDate,
                ),
            )

        for edge in request.edges:
            db.execute(
                """
                INSERT INTO edges (id, plan_id, from_node_id, to_node_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    plan_id,
                    node_id_map.get(edge.from_node, edge.from_node),
                    node_id_map.get(edge.to_node, edge.to_node),
                ),
            )

    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return {"success": True, "data": _serialize_plan(plan)}


@router.put(
    "/plans/{plan_id}",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_plan(
    plan_id: str,
    request: PlanUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _ensure_plan_management_columns(db)
    _get_owned_plan(db, plan_id, current_user_id)

    updates = []
    params = []

    field_map = {
        "title": "title",
        "startDate": "start_date",
        "targetEndDate": "target_end_date",
        "studyFrequency": "study_frequency",
        "studyDaysPerWeek": "study_days_per_week",
        "reminderEnabled": "reminder_enabled",
        "reminderTime": "reminder_time",
        "reminderTimezone": "reminder_timezone",
    }

    payload = request.model_dump(exclude_unset=True)
    for field_name, value in payload.items():
        column = field_map.get(field_name)
        if not column:
            continue
        updates.append(f"{column} = ?")
        params.append(value)

    if updates:
        updates.append("last_access_at = CURRENT_TIMESTAMP")
        params.append(plan_id)
        params.append(current_user_id)
        with transaction(db):
            db.execute(
                f"UPDATE plans SET {', '.join(updates)} WHERE id = ? AND user_id = ?",
                tuple(params),
            )

    plan = _get_owned_plan(db, plan_id, current_user_id)
    return {"success": True, "data": _serialize_plan(plan)}


def _update_plan_status(
    db,
    plan_id: str,
    current_user_id: str,
    status: str,
    archived_reason: Optional[str] = None,
):
    _ensure_plan_management_columns(db)
    _get_owned_plan(db, plan_id, current_user_id)
    with transaction(db):
        db.execute(
            """
            UPDATE plans
            SET status = ?, archived_reason = ?, last_access_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (status, archived_reason, plan_id, current_user_id),
        )
    return _get_owned_plan(db, plan_id, current_user_id)


@router.put(
    "/plans/{plan_id}/archive",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def archive_plan(
    plan_id: str,
    request: Optional[ArchivePlanRequest] = Body(default=None),
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = _update_plan_status(
        db,
        plan_id,
        current_user_id,
        "archived",
        (request.reason if request else None) or "manual",
    )
    return {"success": True, "data": _serialize_plan(plan)}


@router.put(
    "/plans/{plan_id}/restore",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def restore_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = _update_plan_status(db, plan_id, current_user_id, "active", None)
    return {"success": True, "data": _serialize_plan(plan)}


@router.put(
    "/plans/{plan_id}/pause",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def pause_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = _update_plan_status(db, plan_id, current_user_id, "paused", None)
    return {"success": True, "data": _serialize_plan(plan)}


@router.put(
    "/plans/{plan_id}/resume",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def resume_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = _update_plan_status(db, plan_id, current_user_id, "active", None)
    return {"success": True, "data": _serialize_plan(plan)}


@router.delete(
    "/plans/{plan_id}",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def delete_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_owned_plan(db, plan_id, current_user_id)
    with transaction(db):
        db.execute("DELETE FROM plans WHERE id = ? AND user_id = ?", (plan_id, current_user_id))
    return {"success": True, "data": {"id": plan_id}}
