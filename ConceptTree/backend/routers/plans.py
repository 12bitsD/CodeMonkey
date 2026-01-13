from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from database import get_db
from models import (
    PlanListResponse,
    PlanCreateRequest,
    PlanCreateResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
    ErrorResponse,
)
import uuid
import json

router = APIRouter(prefix="/api", tags=["plans"])


@router.post(
    "/plans",
    response_model=PlanCreateResponse,
    responses={500: {"model": ErrorResponse}},
)
def create_plan(request: PlanCreateRequest, db=Depends(get_db)):
    try:
        user_id = "user_default"  # 模拟用户ID，后续接入认证后从token获取
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
                    json.dumps(node.what),
                    json.dumps(node.mastery),
                    node.prompt,
                    json.dumps([r.model_dump() for r in node.resources]),
                    1 if node.isTarget else 0,
                    node.domain,
                ),
            )

        # 3. 批量创建边
        for edge in request.edges:
            db.execute(
                """INSERT INTO edges (id, plan_id, source, target) 
                   VALUES (?, ?, ?, ?)""",
                (edge.id, plan_id, edge.source, edge.target),
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
        )


@router.put(
    "/plans/{plan_id}",
    response_model=PlanUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_plan(plan_id: str, request: PlanUpdateRequest, db=Depends(get_db)):
    try:
        # 检查计划是否存在
        plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
                },
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
        )


@router.get(
    "/plans",
    response_model=PlanListResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_plans(status: Optional[str] = None, db=Depends(get_db)):
    try:
        if status:
            rows = db.execute(
                "SELECT * FROM plans WHERE status = ? ORDER BY last_access_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM plans ORDER BY last_access_at DESC"
            ).fetchall()

        plans = []
        for plan in rows:
            # 获取每个计划的统计数据
            stats = db.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'learned' THEN 1 ELSE 0 END) as completed FROM nodes WHERE plan_id = ?",
                (plan["id"],),
            ).fetchone()

            plans.append(
                {
                    "id": plan["id"],
                    "title": plan["title"],
                    "progress": stats["completed"] if stats["completed"] else 0,
                    "total": stats["total"] if stats["total"] else 0,
                    "status": plan["status"],
                    "lastAccess": plan["last_access_at"],
                    "createdAt": plan["created_at"],
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
        )


@router.put(
    "/plans/{plan_id}/archive",
    response_model=PlanCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def archive_plan(plan_id: str, db=Depends(get_db)):
    try:
        # 检查计划是否存在
        plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
                },
            )

        # 更新状态为归档
        db.execute("UPDATE plans SET status = 'archived' WHERE id = ?", (plan_id,))
        db.commit()

        # 获取更新后的计划摘要
        row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()

        # 计算进度
        stats = db.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'learned' THEN 1 ELSE 0 END) as completed FROM nodes WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()

        return {
            "success": True,
            "data": {
                "id": row["id"],
                "title": row["title"],
                "progress": stats["completed"] if stats["completed"] else 0,
                "total": stats["total"] if stats["total"] else 0,
                "status": row["status"],
                "lastAccess": row["last_access_at"],
                "createdAt": row["created_at"],
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
        )


@router.put(
    "/plans/{plan_id}/restore",
    response_model=PlanCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def restore_plan(plan_id: str, db=Depends(get_db)):
    try:
        # 检查计划是否存在
        plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
                },
            )

        # 更新状态为激活
        db.execute("UPDATE plans SET status = 'active' WHERE id = ?", (plan_id,))
        db.commit()

        # 获取更新后的计划摘要
        row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()

        # 计算进度
        stats = db.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'learned' THEN 1 ELSE 0 END) as completed FROM nodes WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()

        return {
            "success": True,
            "data": {
                "id": row["id"],
                "title": row["title"],
                "progress": stats["completed"] if stats["completed"] else 0,
                "total": stats["total"] if stats["total"] else 0,
                "status": row["status"],
                "lastAccess": row["last_access_at"],
                "createdAt": row["created_at"],
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
        )


@router.delete(
    "/plans/{plan_id}",
    responses={
        200: {"description": "Plan deleted"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_plan(plan_id: str, db=Depends(get_db)):
    try:
        # 检查计划是否存在
        plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
                },
            )

        # 级联删除由数据库外键约束处理，如果没开启则手动删除
        # 这里假设开启了 PRAGMA foreign_keys = ON;
        db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        db.commit()

        return {"success": True}
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
        )
