from datetime import date, datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Depends, Header
from psycopg2 import InterfaceError, OperationalError
from pydantic import BaseModel
from typing import List
import json
import uuid

from database import ensure_schema_columns, get_db, get_db_context, transaction
from services.ai_service import get_ai_service
from services.search_service import SearchServiceError, get_search_service
from utils.auth import get_current_user_id
from utils.idempotency import get_idempotent_response, store_idempotent_response
from models import (
    GraphApiResponse,
    NodeStatusUpdateRequest,
    NodePositionUpdateRequest,
    NodeStatusUpdateResponse,
    NodePositionUpdateResponse,
    BulkPositionUpdateRequest,
    BulkPositionUpdateResponse,
    ErrorResponse,
    NodeUpdate,
    ResourceSearchRequest,
    ResourceSearchResponse,
)

router = APIRouter(prefix="/api", tags=["graph"])

_RESOURCE_SEARCH_COLUMNS_READY = False
_RESOURCE_SEARCH_COLUMNS_LOCK = Lock()
_NODE_MANAGEMENT_COLUMNS_READY = False
_NODE_MANAGEMENT_COLUMNS_LOCK = Lock()


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


def _normalize_resource_key(resource):
    url = str(resource.get("url") or "").strip().lower()
    if url:
        return ("url", url)
    name = str(resource.get("name") or "").strip().lower()
    return ("name", name)


def _build_default_resource_query(node_name: str, plan_title: str | None = None) -> str:
    base = node_name.strip()
    if plan_title:
        return f"{base} {plan_title.strip()} 学习资源 教程"
    return f"{base} 学习资源 教程"


def _merge_search_resources(existing_resources, cached_items, search_results):
    seen = set()
    for resource in existing_resources or []:
        seen.add(_normalize_resource_key(resource))
    for resource in cached_items or []:
        seen.add(_normalize_resource_key(resource))

    merged = list(cached_items or [])
    for result in search_results:
        mapped = {
            "name": (result.get("title") or "").strip(),
            "url": (result.get("url") or "").strip(),
            "reason": (result.get("snippet") or "").strip(),
            "source": "web_search",
        }
        if not mapped["name"] or not mapped["url"]:
            continue
        key = _normalize_resource_key(mapped)
        if key in seen:
            continue
        seen.add(key)
        merged.append(mapped)

    return merged


def _ensure_resource_search_cache_column(db) -> None:
    global _RESOURCE_SEARCH_COLUMNS_READY
    if _RESOURCE_SEARCH_COLUMNS_READY:
        return
    with _RESOURCE_SEARCH_COLUMNS_LOCK:
        if _RESOURCE_SEARCH_COLUMNS_READY:
            return
        ensure_schema_columns(db, {"nodes": ("resource_search_cache",)})
        _RESOURCE_SEARCH_COLUMNS_READY = True


def _ensure_node_management_columns(db) -> None:
    global _NODE_MANAGEMENT_COLUMNS_READY
    if _NODE_MANAGEMENT_COLUMNS_READY:
        return
    with _NODE_MANAGEMENT_COLUMNS_LOCK:
        if _NODE_MANAGEMENT_COLUMNS_READY:
            return
        ensure_schema_columns(
            db,
            {"nodes": ("resource_search_cache", "target_end_date")},
        )
        _NODE_MANAGEMENT_COLUMNS_READY = True


def _format_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _row_get(row, key, default=None):
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def _normalize_node_target_end_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        target_date = value.date()
        normalized = value.isoformat()
    elif isinstance(value, date):
        target_date = value
        normalized = value.isoformat()
    elif isinstance(value, str):
        raw = value.strip()
        try:
            if len(raw) == 10:
                parsed = date.fromisoformat(raw)
                target_date = parsed
                normalized = parsed.isoformat()
            else:
                parsed_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                target_date = parsed_dt.date()
                normalized = parsed_dt.isoformat()
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TARGET_END_DATE",
                        "message": "节点截止日期格式无效，请通过日历选择日期",
                    },
                },
            ) from exc
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TARGET_END_DATE",
                    "message": "节点截止日期格式无效，请通过日历选择日期",
                },
            },
        )

    if target_date < date.today():
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "TARGET_END_DATE_IN_PAST",
                    "message": "节点截止日期不能早于今天",
                },
            },
        )

    return normalized


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
    _ensure_node_management_columns(db)

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
                "contentCache": parse_json_field(node["content_cache"]) or {},
                "resourceSearchCache": parse_json_field(
                    node.get("resource_search_cache"), {}
                )
                or {},
                "isTarget": bool(node["is_target"]),
                "phase": node["phase"],
                "phase_order": node["phase_order"] or 0,
                "depth_level": node["depth_level"] or 2,
                "targetEndDate": _format_datetime(
                    _row_get(node, "target_end_date")
                ),
            }
        )

    edges = db.execute("SELECT * FROM edges WHERE plan_id = ?", (plan_id,)).fetchall()
    parsed_edges = [
        {"from_node": e["from_node_id"], "to_node": e["to_node_id"]} for e in edges
    ]

    with transaction(db):
        db.execute(
            "UPDATE plans SET last_access_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,)
        )

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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
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
    endpoint = f"PUT /api/plans/{plan_id}/nodes/{node_id}/status"
    cached_response = get_idempotent_response(db, current_user_id, endpoint, idempotency_key)
    if cached_response:
        return cached_response

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

    response_data = None
    with transaction(db):
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
                (
                    "UPDATE plans "
                    "SET status = 'archived', archived_reason = 'completed' "
                    "WHERE id = ? AND status = 'active'"
                ),
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

        response_data = {
            "success": True,
            "data": {
                "nodeId": node_id,
                "status": req.status.value,
                "plan": {"progress": progress, "total": total},
            },
        }
        store_idempotent_response(
            db,
            current_user_id,
            endpoint,
            idempotency_key,
            response_data,
        )

    return response_data


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

    with transaction(db):
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
    with transaction(db):
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

    return {"success": True, "data": {"updated": updated}}


@router.put(
    "/plans/{plan_id}/nodes/{node_id}",
    response_model=NodeStatusUpdateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_node(
    plan_id: str,
    node_id: str,
    req: NodeUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _ensure_node_management_columns(db)
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

    node = db.execute(
        "SELECT id FROM nodes WHERE id = ? AND plan_id = ?", (node_id, plan_id)
    ).fetchone()
    if not node:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NODE_NOT_FOUND", "message": "Node not found"},
            },
        )

    field_map = {
        "status": "status",
        "x": "x",
        "y": "y",
        "why": "why",
        "what": "what",
        "mastery": "mastery",
        "prompt": "prompt",
        "resources": "resources",
        "targetEndDate": "target_end_date",
    }
    json_fields = {"what", "mastery", "resources"}
    updates = []
    params = []
    for field_name, value in req.model_dump(exclude_unset=True).items():
        column = field_map.get(field_name)
        if not column:
            continue
        updates.append(f"{column} = ?")
        if field_name == "targetEndDate":
            params.append(_normalize_node_target_end_date(value))
        elif field_name == "status" and hasattr(value, "value"):
            params.append(value.value)
        elif field_name in json_fields:
            params.append(json.dumps(value or []))
        else:
            params.append(value)

    if updates:
        params.extend([node_id, plan_id])
        with transaction(db):
            db.execute(
                f"UPDATE nodes SET {', '.join(updates)} WHERE id = ? AND plan_id = ?",
                tuple(params),
            )

    updated = db.execute(
        "SELECT id, status, target_end_date FROM nodes WHERE id = ? AND plan_id = ?",
        (node_id, plan_id),
    ).fetchone()
    return {
        "success": True,
        "data": {
            "nodeId": node_id,
            "status": updated["status"],
            "targetEndDate": _format_datetime(_row_get(updated, "target_end_date")),
        },
    }


@router.post(
    "/plans/{plan_id}/nodes/{node_id}/search-resources",
    response_model=ResourceSearchResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def search_node_resources(
    plan_id: str,
    node_id: str,
    req: ResourceSearchRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    plan = None
    node = None

    for attempt in range(2):
        try:
            with get_db_context() as read_db:
                plan = read_db.execute(
                    "SELECT id, user_id, title FROM plans WHERE id = ?",
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

                node = read_db.execute(
                    (
                        "SELECT id, name, resources, resource_search_cache "
                        "FROM nodes WHERE id = ? AND plan_id = ?"
                    ),
                    (node_id, plan_id),
                ).fetchone()
                if not node:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "success": False,
                            "error": {"code": "NODE_NOT_FOUND", "message": "Node not found"},
                        },
                    )
                break
        except (OperationalError, InterfaceError) as exc:
            if attempt == 1:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "success": False,
                        "error": {
                            "code": "RESOURCE_SEARCH_UNAVAILABLE",
                            "message": "数据库连接暂时中断，请稍后重试",
                        },
                    },
                ) from exc

    query = (req.query or "").strip() or (
        f'{node["name"]} {plan["title"]} 学习资源 教程'.strip()
        if plan["title"]
        else f'{node["name"]} 学习资源 教程'
    )
    base_resources = parse_json_field(node["resources"], []) or []
    base_cache = parse_json_field(node.get("resource_search_cache"), {}) or {}

    ai_service = get_ai_service()
    search_service = get_search_service()
    try:
        results = await search_service.search(query)
    except SearchServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "RESOURCE_SEARCH_UNAVAILABLE",
                    "message": str(exc),
                },
            },
        ) from exc

    summary_map = await ai_service.summarize_resource_results(
        node_name=node["name"],
        query=query,
        results=results,
    )
    summarized_results = [
        {
            **result,
            "snippet": summary_map.get(result.get("url", "").strip())
            or result.get("snippet", ""),
        }
        for result in results
    ]

    resource_search_cache = None
    resources_added = 0

    for attempt in range(2):
        try:
            with get_db_context() as write_db:
                _ensure_resource_search_cache_column(write_db)
                latest_node = write_db.execute(
                    (
                        "SELECT resources, resource_search_cache "
                        "FROM nodes WHERE id = ? AND plan_id = ?"
                    ),
                    (node_id, plan_id),
                ).fetchone()
                latest_resources = (
                    parse_json_field(latest_node["resources"], []) if latest_node else base_resources
                ) or []
                latest_cache = (
                    parse_json_field(latest_node.get("resource_search_cache"), {})
                    if latest_node
                    else base_cache
                ) or {}
                cached_items = latest_cache.get("items", [])
                merged_items = _merge_search_resources(
                    latest_resources,
                    cached_items,
                    summarized_results,
                )

                resource_search_cache = {
                    "items": merged_items,
                    "query": query,
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }
                resources_added = max(0, len(merged_items) - len(cached_items))

                with transaction(write_db):
                    write_db.execute(
                        "UPDATE nodes SET resource_search_cache = ? WHERE id = ? AND plan_id = ?",
                        (resource_search_cache, node_id, plan_id),
                    )
                break
        except (OperationalError, InterfaceError) as exc:
            if attempt == 1:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "success": False,
                        "error": {
                            "code": "RESOURCE_CACHE_WRITE_FAILED",
                            "message": "资源已检索到，但写入缓存失败，请稍后重试",
                        },
                    },
                ) from exc

    return {
        "success": True,
        "data": {
            "nodeId": node_id,
            "resourceSearchCache": resource_search_cache,
            "resourcesAdded": resources_added,
        },
    }


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

    with transaction(db):
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

    return {"success": True, "data": {"planId": plan_id}}
