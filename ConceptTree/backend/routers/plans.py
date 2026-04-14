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
    try:
        user_id = current_user_id
        plan_id = "p_" + str(uuid.uuid4())[:8]

        # 将 AI 返回的节点 ID (n1/n2...) 映射为全局唯一 ID，避免跨计划冲突
        node_id_map = {node.id: f"{plan_id}_{node.id}" for node in request.nodes}
        target_node_id = node_id_map.get(request.targetNodeId, request.targetNodeId)

        # 1. 创建计划
        total_nodes = len(request.nodes)
        db.execute(
            """INSERT INTO plans (id, user_id, title, original_input,
               target_node_id, status, total, learning_purpose)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan_id,
                user_id,
                request.title,
                request.originalInput,
                target_node_id,
                "active",
                total_nodes,
                request.learning_purpose,
            ),
        )

        # 2. 批量创建节点（使用映射后的唯一 ID）
        for node in request.nodes:
            db.execute(
                """INSERT INTO nodes (id, plan_id, name, status, x, y, why,
                   what, mastery, prompt, resources, is_target, domain,
                   phase, phase_order, depth_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_id_map[node.id],
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
                    node.phase,
                    node.phase_order,
                    node.depth_level,
                ),
            )

        # 3. 批量创建边（同步映射节点 ID）
        for edge in request.edges:
            edge_id = "e_" + uuid.uuid4().hex[:12]
            db.execute(
                """INSERT INTO edges (id, plan_id, from_node_id, to_node_id)
                   VALUES (?, ?, ?, ?)""",
                (
                    edge_id,
                    plan_id,
                    node_id_map.get(edge.from_node, edge.from_node),
                    node_id_map.get(edge.to_node, edge.to_node),
                ),
            )

        db.commit()
        return {
            "success": True,
            "data": {
                "id": plan_id,
                "title": request.title,
                "progress": 0,
                "total": total_nodes,
                "status": "active",
                "lastAccess": None,
                "createdAt": None,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "CREATE_PLAN_ERROR", "message": "创建学习计划失败，请稍后重试"},
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
                "error": {"code": "UPDATE_PLAN_ERROR", "message": "更新学习计划失败，请稍后重试"},
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
                "error": {"code": "GET_PLANS_ERROR", "message": "获取学习计划失败，请稍后重试"},
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

        # 计算进度
        stats = db.execute(
            """SELECT
                   COUNT(*) as total
                   ,SUM(CASE WHEN status = 'learned' THEN 1
                       ELSE 0 END) as completed
               FROM nodes
               WHERE plan_id = ?""",
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
                "error": {"code": "ARCHIVE_PLAN_ERROR", "message": "归档学习计划失败，请稍后重试"},
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

        # 计算进度
        stats = db.execute(
            """SELECT
                   COUNT(*) as total
                   ,SUM(CASE WHEN status = 'learned' THEN 1
                       ELSE 0 END) as completed
               FROM nodes
               WHERE plan_id = ?""",
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
                "error": {"code": "RESTORE_PLAN_ERROR", "message": "恢复学习计划失败，请稍后重试"},
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
                "error": {"code": "DELETE_PLAN_ERROR", "message": "删除学习计划失败，请稍后重试"},
            },
        ) from e
