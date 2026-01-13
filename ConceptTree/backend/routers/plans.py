from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import (
    PlanListResponse,
    PlanCreateRequest,
    PlanCreateResponse,
    PlanUpdateRequest,
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
            """INSERT INTO plans (id, user_id, title, original_input, target_node_id, status) 
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
                """INSERT INTO nodes (id, plan_id, name, status, x, y, why, what, mastery, prompt, resources, is_target, domain) 
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
            edge_id = "e_" + str(uuid.uuid4())[:8]
            db.execute(
                "INSERT INTO edges (id, plan_id, from_node_id, to_node_id) VALUES (?, ?, ?, ?)",
                (edge_id, plan_id, edge.from_node, edge.to_node),
            )

        db.commit()

        # 获取创建后的计划摘要
        row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()

        return {
            "success": True,
            "data": {
                "id": row["id"],
                "title": row["title"],
                "progress": 0,
                "total": len(request.nodes),
                "status": row["status"],
                "lastAccess": row["last_access_at"],
                "createdAt": row["created_at"],
            },
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail={"code": "CREATE_PLAN_ERROR", "message": str(e)}
        )


@router.put(
    "/plans/{plan_id}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_plan(plan_id: str, request: PlanUpdateRequest, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
        )

    db.execute("UPDATE plans SET title = ? WHERE id = ?", (request.title, plan_id))
    db.commit()

    return {"success": True, "data": {"id": plan_id, "title": request.title}}


@router.get(
    "/plans", response_model=PlanListResponse, responses={500: {"model": ErrorResponse}}
)
def get_plans(status: Optional[str] = None, db=Depends(get_db)):
    if status:
        rows = db.execute(
            "SELECT * FROM plans WHERE status = ? ORDER BY last_access_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM plans ORDER BY last_access_at DESC").fetchall()

    plans = []
    for plan in rows:
        plans.append(
            {
                "id": plan["id"],
                "title": plan["title"],
                "progress": plan["progress"],
                "total": plan["total"],
                "status": plan["status"],
                "lastAccess": plan["last_access_at"],
                "createdAt": plan["created_at"],
            }
        )

    return {"success": True, "data": plans}


@router.put(
    "/plans/{plan_id}/archive",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def archive_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
        )

    if plan["status"] == "archived":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PLAN_ALREADY_ARCHIVED",
                "message": "Plan is already archived",
            },
        )

    db.execute("UPDATE plans SET status = 'archived' WHERE id = ?", (plan_id,))

    return {"success": True, "data": {"id": plan_id, "status": "archived"}}


@router.put(
    "/plans/{plan_id}/restore",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def restore_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
        )

    if plan["status"] == "active":
        raise HTTPException(
            status_code=400,
            detail={"code": "PLAN_ALREADY_ACTIVE", "message": "Plan is already active"},
        )

    db.execute("UPDATE plans SET status = 'active' WHERE id = ?", (plan_id,))

    return {"success": True, "data": {"id": plan_id, "status": "active"}}


@router.delete(
    "/plans/{plan_id}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def delete_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
        )

    db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    db.commit()

    return {"success": True, "message": "计划已删除"}
