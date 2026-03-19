"""
Graph Router — manages the visual knowledge graph for a learning plan.

This router is the primary data source for the interactive graph canvas.
A *plan* consists of *nodes* (learning concepts) linked by *edges* (prerequisite
dependencies). Every mutation here targets a single plan that belongs to the
authenticated user.

Key behaviours frontend developers must know:
  1. Fetching the graph also updates ``plans.last_access_at`` (used for recency sort).
  2. Marking a node ``learned`` has three cascading side-effects: plan progress is
     recalculated, a ``learning_sessions`` row is inserted, and the user's
     ``mastered_knowledge`` list in ``user_profiles`` grows.
  3. Position endpoints (single and bulk) are purely cosmetic — they only update
     canvas XY coordinates and have no effect on learning logic.

Endpoints
---------
GET  /plans/{plan_id}/graph                — full graph data (nodes + edges)
PUT  /plans/{plan_id}/nodes/{node_id}/status   — update one node's learning status
PUT  /plans/{plan_id}/nodes/{node_id}/position — update one node's canvas position
PUT  /plans/{plan_id}/nodes/positions          — bulk-update canvas positions
POST /plans/{plan_id}/apply-changes            — apply AI-suggested structural edits
"""

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


def parse_json_field(field_value, default=[]):
    """Safely decode a JSON-encoded database column value.

    Returns the parsed Python object, or ``default`` when the value is empty
    or not valid JSON. Already-parsed lists and dicts are returned as-is so
    the function is safe to call regardless of the DB driver's auto-parsing.

    Args:
        field_value: Raw database column value (string, list, dict, or None).
        default: Fallback value returned on empty or unparseable input.

    Returns:
        Parsed Python object, or ``default``.
    """
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
    """Return the full graph (nodes + edges) for a learning plan.

    This is the primary endpoint the graph canvas calls on load. It returns
    every node's content fields (``why``, ``what``, ``mastery``, ``resources``)
    along with their canvas positions (``x``, ``y``) and current learning
    ``status``. As a side-effect, the plan's ``last_access_at`` timestamp is
    refreshed so the plan list sorts by recency correctly.

    Args:
        plan_id: The plan whose graph to fetch.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        ``GraphApiResponse`` containing ``planId``, ``title``, ``nodes``, and
        ``edges``.

    Raises:
        HTTPException 404: Plan does not exist (``PLAN_NOT_FOUND``).
        HTTPException 403: Authenticated user does not own this plan.
    """
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
    """Mark a node as learned, unlearned, or skipped — with cascading updates.

    This is the core learning-progress endpoint. Setting a node to ``learned``
    triggers three additional writes beyond the node update itself:

    1. **Plan progress** — ``plans.progress`` and ``plans.total`` are
       recalculated. ``total`` excludes ``skipped`` nodes so skipped concepts
       don't inflate the goal.
    2. **Learning session** — A row is inserted into ``learning_sessions`` for
       audit and history features.
    3. **User profile** — The concept name is appended to
       ``user_profiles.mastered_knowledge`` (only on ``learned``; reversals are
       not removed from the profile list).

    Args:
        plan_id: The plan that owns the node.
        node_id: The node whose status to update.
        req: Request body containing the new ``status`` value
             (``"learned"``, ``"unlearned"``, or ``"skipped"``).
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        ``NodeStatusUpdateResponse`` with the updated ``nodeId``, ``status``,
        and the recalculated plan ``progress``/``total``.

    Raises:
        HTTPException 400: ``status`` is not one of the three valid values
            (``INVALID_STATUS``).
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan or node not found (``PLAN_NOT_FOUND`` /
            ``NODE_NOT_FOUND``).
    """
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
    """Persist a single node's canvas position after the user drags it.

    This is a purely cosmetic update — only the ``x`` and ``y`` canvas
    coordinates change. No learning state, progress, or session records are
    affected. Both ``x`` and ``y`` are required; omitting either returns 400.

    Args:
        plan_id: The plan that owns the node.
        node_id: The node to reposition.
        req: Request body with ``x`` and ``y`` canvas coordinates (both
             required; floats accepted).
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        JSON with ``nodeId``, ``x``, and ``y`` confirming the saved position.

    Raises:
        HTTPException 400: Either ``x`` or ``y`` is missing (``INVALID_POSITION``).
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan or node not found.
    """
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
    """Persist canvas positions for multiple nodes in a single request.

    Use this instead of repeated single-position calls when the layout changes
    for many nodes at once (e.g., after an auto-layout or canvas pan-to-fit).
    Entries in the ``positions`` list that are missing ``nodeId``, ``x``, or
    ``y`` are silently skipped. The response reports how many rows were actually
    updated.

    Args:
        plan_id: The plan whose nodes to reposition.
        req: Request body with a ``positions`` list, each entry containing
             ``nodeId``, ``x``, and ``y``.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        JSON with ``updated`` — the count of node rows successfully written.

    Raises:
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
    """
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
    """Request body for applying AI-suggested structural edits to a plan.

    Attributes:
        keep: Node IDs that already exist in the plan and should be retained
              unchanged (informational — no database action taken for these).
        remove: Node IDs to delete from the plan permanently.
        add: Concept names (strings) for new nodes to create. Each is inserted
             at position (0, 0) with ``status = "unlearned"`` and empty content
             fields; the frontend is responsible for positioning them.
        newTitle: The updated plan title to write, even if unchanged.
    """

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
    """Apply AI-suggested structural changes — add/remove nodes and rename the plan.

    This endpoint is called after the user accepts the AI's recommendations for
    revising an existing plan. It performs three ordered operations:

    1. **Delete** all nodes in ``req.remove`` (and their edges via cascade).
    2. **Insert** new placeholder nodes for each name in ``req.add``, placed at
       origin (0, 0) with blank content fields.
    3. **Rename** the plan to ``req.newTitle``.

    Nodes in ``req.keep`` require no database action and are accepted solely to
    document which nodes the AI decided to retain.

    Args:
        plan_id: The plan to modify.
        req: ``ApplyChangesRequest`` with ``keep``, ``remove``, ``add``, and
             ``newTitle``.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        JSON with ``planId`` confirming the targeted plan was updated.

    Raises:
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
    """
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
    db.commit()

    return {"success": True, "data": {"planId": plan_id}}
