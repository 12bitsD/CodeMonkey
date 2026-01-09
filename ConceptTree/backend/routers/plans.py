from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import PlanListResponse, ErrorResponse

router = APIRouter(prefix="/api", tags=["plans"])


@router.get(
    "/plans",
    response_model=PlanListResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
def get_plans(status: Optional[str] = None, db=Depends(get_db)):
    if status:
        rows = db.execute("SELECT * FROM plans WHERE status = ? ORDER BY last_access_at DESC", (status,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM plans ORDER BY last_access_at DESC").fetchall()

    plans = []
    for plan in rows:
        plans.append({
            "id": plan["id"],
            "title": plan["title"],
            "progress": plan["progress"],
            "total": plan["total"],
            "status": plan["status"],
            "lastAccess": plan["last_access_at"],
            "createdAt": plan["created_at"]
        })

    return {
        "success": True,
        "data": plans
    }


@router.put(
    "/plans/{plan_id}/archive",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
def archive_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail={
            "code": "PLAN_NOT_FOUND",
            "message": "Plan not found"
        })
    
    if plan["status"] == "archived":
        raise HTTPException(status_code=400, detail={
            "code": "PLAN_ALREADY_ARCHIVED",
            "message": "Plan is already archived"
        })
    
    db.execute("UPDATE plans SET status = 'archived' WHERE id = ?", (plan_id,))

    return {
        "success": True,
        "data": {"id": plan_id, "status": "archived"}
    }


@router.put(
    "/plans/{plan_id}/restore",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
def restore_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail={
            "code": "PLAN_NOT_FOUND",
            "message": "Plan not found"
        })
    
    if plan["status"] == "active":
        raise HTTPException(status_code=400, detail={
            "code": "PLAN_ALREADY_ACTIVE",
            "message": "Plan is already active"
        })
    
    db.execute("UPDATE plans SET status = 'active' WHERE id = ?", (plan_id,))

    return {
        "success": True,
        "data": {"id": plan_id, "status": "active"}
    }


@router.delete(
    "/plans/{plan_id}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
def delete_plan(plan_id: str, db=Depends(get_db)):
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail={
            "code": "PLAN_NOT_FOUND",
            "message": "Plan not found"
        })
    
    db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    db.commit()

    return {
        "success": True,
        "message": "计划已删除"
    }
