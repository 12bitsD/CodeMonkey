from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import json
import uuid

from database import get_db
from utils.auth import get_current_user_id
from models import (
    GraphApiResponse,
    NodeStatusUpdateRequest,
    NodePositionUpdateRequest,
    NodeStatusUpdateResponse,
    NodePositionUpdateResponse,
    BulkPositionUpdateRequest,
    BulkPositionUpdateResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api", tags=["graph"])


def parse_json_field(field_value, default=None):
    if default is None:
        default = []
    if not field_value:
        return default
    if isinstance(field_value, (list, dict)):
        return field_value
    try:
        return json.loads(field_value)
    except json.JSONDecodeError:
        return default


@router.get(
    "/plans/{plan_id}/graph",
    response_model=GraphApiResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_graph(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = db.execute(
        "SELECT id, user_id, title, target_node_id FROM plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
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
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    nodes = db.execute("SELECT * FROM nodes WHERE plan_id = ?", (plan_id,)).fetchall()

    parsed_nodes = []
    for node in nodes:
        parsed_nodes.append(
            {
                "id": node["id"],
                "name": node["name"],
                "status": node["status"],
                "x": node["x"],
                "y": node["y"],
                "why": node["why"],
                "what": parse_json_field(node["what"]),
                "mastery": parse_json_field(node["mastery"]),
                "prompt": node["prompt"],
                "resources": parse_json_field(node["resources"]),
                "isTarget": bool(node["is_target"]),
            }
        )

    edges = db.execute("SELECT * FROM edges WHERE plan_id = ?", (plan_id,)).fetchall()
    parsed_edges = [
        {"from_node": e["from_node_id"], "to_node": e["to_node_id"]} for e in edges
    ]

    db.execute(
        "UPDATE plans SET last_access_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,)
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "planId": plan["id"],
            "title": plan["title"],
            "nodes": parsed_nodes,
            "edges": parsed_edges,
        },
    }


@router.put(
    "/plans/{plan_id}/nodes/{node_id}/status",
    response_model=NodeStatusUpdateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_node_status(
    plan_id: str,
    node_id: str,
    req: NodeStatusUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    valid_statuses = ["unlearned", "learned", "skipped"]
    if req.status.value not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {"code": "INVALID_STATUS", "message": "Invalid status"},
            },
        )

    # Get plan and user_id first
    plan = db.execute(
        "SELECT user_id FROM plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            },
        )
    user_id = plan["user_id"]
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    # Check node existence
    node = db.execute(
        "SELECT name FROM nodes WHERE id = ? AND plan_id = ?", (node_id, plan_id)
    ).fetchone()
    if not node:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NODE_NOT_FOUND", "message": "Node not found"},
            },
        )
    node_name = node["name"]

    # 1. Update node status
    db.execute(
        "UPDATE nodes SET status = ? WHERE id = ? AND plan_id = ?",
        (req.status.value, node_id, plan_id),
    )

    # 2. Update plan progress
    nodes = db.execute(
        "SELECT status FROM nodes WHERE plan_id = ?", (plan_id,)
    ).fetchall()
    total = len([n for n in nodes if n["status"] != "skipped"])
    progress = len([n for n in nodes if n["status"] == "learned"])
    db.execute(
        "UPDATE plans SET progress = ?, total = ? WHERE id = ?",
        (progress, total, plan_id),
    )

    # Auto-archive plan when all nodes are completed
    if total > 0 and progress == total:
        db.execute(
            "UPDATE plans SET status = 'archived' WHERE id = ? AND status = 'active'",
            (plan_id,),
        )

    # 3. Record learning session
    session_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, plan_id, node_id, node_name, req.status.value),
    )

    # 4. Update user profile if learned
    if req.status.value == "learned":
        # Check if user profile exists
        profile = db.execute(
            "SELECT id, mastered_knowledge FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        mastered_list = []
        if profile:
            mastered_list = parse_json_field(profile["mastered_knowledge"])
            if node_name not in mastered_list:
                mastered_list.append(node_name)
                db.execute(
                    "UPDATE user_profiles SET mastered_knowledge = ? WHERE user_id = ?",
                    (mastered_list, user_id),
                )
        else:
            # Create profile if not exists (though it should usually exist)
            profile_id = "profile_" + str(uuid.uuid4())
            mastered_list = [node_name]
            db.execute(
                "INSERT INTO user_profiles (id, user_id, mastered_knowledge) VALUES (?, ?, ?)",
                (profile_id, user_id, mastered_list),
            )

    db.commit()

    return {
        "success": True,
        "data": {
            "nodeId": node_id,
            "status": req.status.value,
            "plan": {"progress": progress, "total": total},
        },
    }


@router.put(
    "/plans/{plan_id}/nodes/{node_id}/position",
    response_model=NodePositionUpdateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_node_position(
    plan_id: str,
    node_id: str,
    req: NodePositionUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    if req.x is None or req.y is None:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_POSITION",
                    "message": "x and y are required",
                },
            },
        )

    plan = db.execute(
        "SELECT user_id FROM plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
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
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    result = db.execute(
        "UPDATE nodes SET x = ?, y = ? WHERE id = ? AND plan_id = ?",
        (req.x, req.y, node_id, plan_id),
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NODE_NOT_FOUND", "message": "Node not found"},
            },
        )

    db.commit()

    return {"success": True, "data": {"nodeId": node_id, "x": req.x, "y": req.y}}


@router.put(
    "/plans/{plan_id}/nodes/positions",
    response_model=BulkPositionUpdateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_nodes_positions(
    plan_id: str,
    req: BulkPositionUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = db.execute(
        "SELECT id, user_id FROM plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
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
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    updated = 0
    for pos in req.positions:
        node_id = pos.get("nodeId")
        x = pos.get("x")
        y = pos.get("y")
        if node_id is not None and x is not None and y is not None:
            result = db.execute(
                "UPDATE nodes SET x = ?, y = ? WHERE id = ? AND plan_id = ?",
                (x, y, node_id, plan_id),
            )
            updated += result.rowcount

    db.commit()

    return {"success": True, "data": {"updated": updated}}


class ApplyChangesRequest(BaseModel):
    keep: List[str] = []
    remove: List[str] = []
    add: List[str] = []
    newTitle: str


@router.post("/plans/{plan_id}/apply-changes")
def apply_changes(
    plan_id: str,
    req: ApplyChangesRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = db.execute(
        "SELECT id, user_id FROM plans WHERE id = ?", (plan_id,)
    ).fetchone()
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
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    for node_id in req.remove:
        db.execute("DELETE FROM nodes WHERE id = ? AND plan_id = ?", (node_id, plan_id))

    for node_name in req.add:
        new_id = f"n_{uuid.uuid4().hex[:10]}"
        db.execute(
            "INSERT INTO nodes (id, plan_id, name, status, x, y, why, what, mastery, prompt, resources) "
            "VALUES (?, ?, ?, 'unlearned', 0, 0, '', '[]', '[]', '', '[]')",
            (new_id, plan_id, node_name),
        )

    db.execute("UPDATE plans SET title = ? WHERE id = ?", (req.newTitle, plan_id))

    # 重新计算 progress/total
    all_nodes = db.execute("SELECT status FROM nodes WHERE plan_id = ?", (plan_id,)).fetchall()
    new_total = len([n for n in all_nodes if n["status"] != "skipped"])
    new_progress = len([n for n in all_nodes if n["status"] == "learned"])
    db.execute("UPDATE plans SET progress = ?, total = ? WHERE id = ?", (new_progress, new_total, plan_id))

    db.commit()

    return {"success": True, "data": {"planId": plan_id}}
