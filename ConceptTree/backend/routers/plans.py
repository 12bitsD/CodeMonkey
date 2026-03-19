"""
Plans Router — manages the full lifecycle of a user's learning plans.

A *plan* is the top-level container in ConceptTree: it holds a title, a set
of concept *nodes*, and the prerequisite *edges* between them. This router
enforces that every user can only read and modify their own plans.

Plan status transitions:
  ``active``  →  ``archived``  (via ``/archive``)
  ``archived`` →  ``active``   (via ``/restore``)
  any state   →  deleted       (via ``DELETE``, permanent and irreversible)

Key behaviours for frontend developers:
  1. ``POST /plans`` is atomic — plan, nodes, and edges are all written in one
     transaction, so a partial failure leaves no orphaned rows.
  2. ``GET /plans`` sorts by ``last_access_at`` descending (most-recently viewed
     first). Use the ``status`` query parameter to filter by ``active`` or
     ``archived``.
  3. Progress stats (``progress``/``total``) exclude ``skipped`` nodes from
     the denominator so skipped concepts don't inflate the goal count.

Endpoints
---------
POST   /plans                  — create a plan (atomic: plan + nodes + edges)
GET    /plans                  — list the current user's plans
PUT    /plans/{plan_id}        — update plan title
PUT    /plans/{plan_id}/archive  — soft-delete: move plan to archived state
PUT    /plans/{plan_id}/restore  — undo archive: move plan back to active
DELETE /plans/{plan_id}        — permanent deletion
"""

from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException, Depends

from database import get_db
from utils.auth import get_current_user_id
from models import (
    PlanListResponse,
    PlanCreateRequest,
    PlanCreateResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api", tags=["plans"])


def _format_datetime(dt) -> Optional[str]:
    """Convert a datetime value to an ISO 8601 string for JSON serialisation.

    Returns ``None`` when ``dt`` is ``None``, so the JSON field is omitted
    rather than serialised as ``"None"``. Accepts both ``datetime`` objects
    and strings (the latter are returned unchanged).

    Args:
        dt: A ``datetime`` object, a datetime string, or ``None``.

    Returns:
        ISO 8601 string, the original string, or ``None``.
    """
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


@router.post(
    "/plans",
    response_model=PlanCreateResponse,
    responses={500: {"model": ErrorResponse}},
)
def create_plan(
    request: PlanCreateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Create a new learning plan together with all its nodes and edges atomically.

    All three writes (plan row, node rows, edge rows) happen inside a single
    transaction. If any insert fails the whole operation is rolled back, so the
    database never ends up with a plan that is missing nodes or edges.

    The plan is created with ``status = "active"`` and progress counters at
    zero. The plan ID is generated server-side using the prefix ``p_`` followed
    by the first 8 characters of a UUID.

    Args:
        request: ``PlanCreateRequest`` containing ``title``, ``originalInput``,
            ``targetNodeId``, a list of ``nodes``, and a list of ``edges``.
        current_user_id: Injected from the auth token; used as the plan owner.
        db: Injected database connection.

    Returns:
        ``PlanCreateResponse`` with ``id`` and ``title`` of the new plan.

    Raises:
        HTTPException 500: Any database error during creation
            (``CREATE_PLAN_ERROR``).
    """
    try:
        user_id = current_user_id
        plan_id = "p_" + str(uuid.uuid4())[:8]

        # 1. 创建计划
        db.execute(
            """INSERT INTO plans (id, user_id, title, original_input,
               target_node_id, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                plan_id,
                user_id,
                request.title,
                request.originalInput,
                request.targetNodeId,
                "active",
            ),
        )

        # 2. 批量创建节点
        for node in request.nodes:
            db.execute(
                """INSERT INTO nodes (id, plan_id, name, status, x, y, why,
                   what, mastery, prompt, resources, is_target, domain)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node.id,
                    plan_id,
                    node.name,
                    node.status.value,
                    node.x,
                    node.y,
                    node.why,
                    node.what,
                    node.mastery,
                    node.prompt,
                    [r.model_dump() for r in node.resources],
                    node.isTarget,
                    node.domain,
                ),
            )

        # 3. 批量创建边
        for edge in request.edges:
            edge_id = "e_" + uuid.uuid4().hex[:12]
            db.execute(
                """INSERT INTO edges (id, plan_id, from_node_id, to_node_id)
                   VALUES (?, ?, ?, ?)""",
                (edge_id, plan_id, edge.from_node, edge.to_node),
            )

        db.commit()
        return {
            "success": True,
            "data": {"id": plan_id, "title": request.title},
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "CREATE_PLAN_ERROR", "message": str(e)},
            },
        ) from e


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
    """Update a plan's title. Currently the only mutable plan-level field.

    Only the ``title`` field is updated; nodes, edges, and status are unchanged.
    If ``request.title`` is empty or ``None``, no database write occurs and the
    response echoes back the existing title (no 400 is raised).

    Args:
        plan_id: The plan to update.
        request: ``PlanUpdateRequest`` with an optional ``title`` string.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        ``PlanUpdateResponse`` with ``id`` and the (potentially updated) ``title``.

    Raises:
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
        HTTPException 500: Any database error (``UPDATE_PLAN_ERROR``).
    """
    try:
        # 检查计划是否存在
        plan = db.execute(
            "SELECT id, user_id FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {
                        "code": "PLAN_NOT_FOUND",
                        "message": "Plan not found",
                    },
                },
            )
        if plan["user_id"] != current_user_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Forbidden"},
            )

        # 更新标题
        if request.title:
            db.execute(
                "UPDATE plans SET title = ? WHERE id = ?",
                (request.title, plan_id),
            )
            db.commit()

        return {
            "success": True,
            "data": {"id": plan_id, "title": request.title or plan["title"]},
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "UPDATE_PLAN_ERROR", "message": str(e)},
            },
        ) from e


@router.get(
    "/plans",
    response_model=PlanListResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_plans(
    status: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """List all learning plans owned by the current user, sorted by recency.

    Results are ordered by ``last_access_at`` descending so the most recently
    viewed plan appears first. Each plan includes pre-computed ``progress`` and
    ``total`` counters (maintained by the graph router when nodes change status).

    Args:
        status: Optional filter — pass ``"active"`` or ``"archived"`` to narrow
            results. Omit to return all plans regardless of status.
        current_user_id: Injected from the auth token; scopes results to this
            user only.
        db: Injected database connection.

    Returns:
        ``PlanListResponse`` with a ``data`` list of plan summaries, each
        containing ``id``, ``title``, ``progress``, ``total``, ``status``,
        ``lastAccess``, and ``createdAt``.

    Raises:
        HTTPException 500: Any database error (``GET_PLANS_ERROR``).
    """
    try:
        if status:
            rows = db.execute(
                (
                    "SELECT * FROM plans WHERE user_id = ? AND status = ? "
                    "ORDER BY last_access_at DESC"
                ),
                (current_user_id, status),
            ).fetchall()
        else:
            rows = db.execute(
                (
                    "SELECT * FROM plans WHERE user_id = ? "
                    "ORDER BY last_access_at DESC"
                ),
                (current_user_id,),
            ).fetchall()

        plans = []
        for plan in rows:
            plans.append(
                {
                    "id": plan["id"],
                    "title": plan["title"],
                    "progress": plan["progress"] if plan["progress"] else 0,
                    "total": plan["total"] if plan["total"] else 0,
                    "status": plan["status"],
                    "lastAccess": _format_datetime(plan["last_access_at"]),
                    "createdAt": _format_datetime(plan["created_at"]),
                }
            )

        return {"success": True, "data": plans}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "GET_PLANS_ERROR", "message": str(e)},
            },
        ) from e


@router.put(
    "/plans/{plan_id}/archive",
    response_model=PlanCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def archive_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Archive an active plan — a reversible soft-delete.

    Archiving sets ``status = "archived"`` without deleting any data. The plan
    remains queryable via ``GET /plans?status=archived`` and can be restored at
    any time. Attempting to archive an already-archived plan returns 400.

    The response includes fresh progress stats (``progress``/``total``) computed
    directly from nodes so the UI can display accurate completion at archival
    time. ``skipped`` nodes are excluded from ``total``.

    Args:
        plan_id: The plan to archive.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        Full plan summary including updated ``status``, ``progress``, ``total``,
        ``lastAccess``, and ``createdAt``.

    Raises:
        HTTPException 400: Plan is already archived (``PLAN_ALREADY_ARCHIVED``).
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
        HTTPException 500: Any database error (``ARCHIVE_PLAN_ERROR``).
    """
    try:
        # 检查计划是否存在
        plan = db.execute(
            "SELECT id, user_id, status FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            )
        if plan["user_id"] != current_user_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Forbidden"},
            )

        if plan["status"] == "archived":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "PLAN_ALREADY_ARCHIVED",
                    "message": "Plan already archived",
                },
            )

        # 更新状态为归档
        db.execute(
            "UPDATE plans SET status = 'archived' WHERE id = ?",
            (plan_id,),
        )
        db.commit()

        # 获取更新后的计划摘要
        row = db.execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()

        # 计算进度（排除skipped节点，与graph.py保持一致）
        stats = db.execute(
            """SELECT
                   COUNT(*) as total
                   ,SUM(CASE WHEN status = 'learned' THEN 1
                       ELSE 0 END) as completed
                FROM nodes
                WHERE plan_id = ? AND status != 'skipped'""",
            (plan_id,),
        ).fetchone()

        completed = stats["completed"] if stats["completed"] else 0
        total = stats["total"] if stats["total"] else 0
        return {
            "success": True,
            "data": {
                "id": row["id"],
                "title": row["title"],
                "progress": completed,
                "total": total,
                "status": row["status"],
                "lastAccess": _format_datetime(row["last_access_at"]),
                "createdAt": _format_datetime(row["created_at"]),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "ARCHIVE_PLAN_ERROR", "message": str(e)},
            },
        ) from e


@router.put(
    "/plans/{plan_id}/restore",
    response_model=PlanCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def restore_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Restore an archived plan back to active status.

    This is the inverse of ``/archive``. Sets ``status = "active"`` so the
    plan reappears in the default active plan list. Attempting to restore an
    already-active plan returns 400.

    The response includes fresh progress stats (``progress``/``total``) computed
    from nodes, with ``skipped`` nodes excluded from ``total``.

    Args:
        plan_id: The archived plan to restore.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        Full plan summary with updated ``status = "active"``, ``progress``,
        ``total``, ``lastAccess``, and ``createdAt``.

    Raises:
        HTTPException 400: Plan is already active (``PLAN_ALREADY_ACTIVE``).
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
        HTTPException 500: Any database error (``RESTORE_PLAN_ERROR``).
    """
    try:
        # 检查计划是否存在
        plan = db.execute(
            "SELECT id, user_id, status FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            )
        if plan["user_id"] != current_user_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Forbidden"},
            )

        if plan["status"] == "active":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "PLAN_ALREADY_ACTIVE",
                    "message": "Plan already active",
                },
            )

        # 更新状态为激活
        db.execute(
            "UPDATE plans SET status = 'active' WHERE id = ?",
            (plan_id,),
        )
        db.commit()

        # 获取更新后的计划摘要
        row = db.execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()

        # 计算进度（排除skipped节点，与graph.py保持一致）
        stats = db.execute(
            """SELECT
                   COUNT(*) as total
                   ,SUM(CASE WHEN status = 'learned' THEN 1
                       ELSE 0 END) as completed
                FROM nodes
                WHERE plan_id = ? AND status != 'skipped'""",
            (plan_id,),
        ).fetchone()

        completed = stats["completed"] if stats["completed"] else 0
        total = stats["total"] if stats["total"] else 0
        return {
            "success": True,
            "data": {
                "id": row["id"],
                "title": row["title"],
                "progress": completed,
                "total": total,
                "status": row["status"],
                "lastAccess": _format_datetime(row["last_access_at"]),
                "createdAt": _format_datetime(row["created_at"]),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "RESTORE_PLAN_ERROR", "message": str(e)},
            },
        ) from e


@router.delete(
    "/plans/{plan_id}",
    responses={
        200: {"description": "Plan deleted"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_plan(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Permanently delete a plan and all its associated data.

    **This action is irreversible.** The plan row is hard-deleted; associated
    nodes and edges are removed by database cascade constraints. There is no
    soft-delete or recovery path — use ``/archive`` if reversibility is needed.

    Args:
        plan_id: The plan to delete permanently.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        JSON ``{"success": true, "data": {"message": "计划已删除"}}`` on success.

    Raises:
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
        HTTPException 500: Any database error (``DELETE_PLAN_ERROR``).
    """
    try:
        # 检查计划是否存在
        plan = db.execute(
            "SELECT id, user_id FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            )
        if plan["user_id"] != current_user_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Forbidden"},
            )

        db.execute(
            "DELETE FROM plans WHERE id = ?",
            (plan_id,),
        )
        db.commit()

        return {"success": True, "data": {"message": "计划已删除"}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "DELETE_PLAN_ERROR", "message": str(e)},
            },
        ) from e
