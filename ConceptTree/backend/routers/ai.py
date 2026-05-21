from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Optional, AsyncGenerator
import asyncio
import json

from database import ensure_schema_columns, get_db, get_db_context
from services.ai_service import get_ai_service
from services.learning_history import get_learning_history
from models import (
    ErrorResponse,
    UserBackgroundInput,
    LearningPurpose,
    ExplainTopicRequest,
    ChatRequest,
)
from utils.auth import get_current_user_id


router = APIRouter(prefix="/api/ai", tags=["AI"])


class ParseGoalRequest(BaseModel):
    input: str
    userBackground: Optional[UserBackgroundInput] = None

    @field_validator("input")
    @classmethod
    def validate_input_length(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Input must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("Input must be less than 2000 characters")
        return v


class GenerateGraphRequest(BaseModel):
    input: str
    interpretation: str
    userBackground: Optional[UserBackgroundInput] = None
    learning_purpose: str = "apply"  # F1: explore / apply / master


class ParseGoalResponseWrapper(BaseModel):
    success: bool
    data: dict


# generate-graph 改为 SSE，不再使用 Pydantic response_model


@router.post(
    "/parse-goal",
    response_model=ParseGoalResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def parse_goal(
    request: ParseGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """AI解析学习目标"""
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None
    result = await ai_service.parse_goal(request.input, user_background=user_bg)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )

    return {"success": True, "data": result.data.model_dump() if result.data else {}}


async def _stream_graph_nodes(
    request: GenerateGraphRequest,
    current_user_id: str,
) -> AsyncGenerator[str, None]:
    """F5 — SSE 生成器：调用 LLM 后逐节点流式返回。"""
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None

    result = await ai_service.generate_graph(
        interpretation=request.interpretation,
        original_input=request.input,
        user_background=user_bg,
        learning_purpose=request.learning_purpose,
    )

    if not result.success:
        err = result.error.model_dump() if result.error else {"code": "UNKNOWN", "message": "Unknown error"}
        yield f"data: {json.dumps({'type': 'error', 'error': err}, ensure_ascii=False)}\n\n"
        return

    data = result.data

    # 先发送元信息（interpretation + targetNodeId）
    yield f"data: {json.dumps({'type': 'meta', 'interpretation': data.interpretation, 'targetNodeId': data.targetNodeId, 'totalNodes': len(data.nodes)}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0)

    # 逐节点流式发送
    for node in data.nodes:
        yield f"data: {json.dumps({'type': 'node', 'node': node.model_dump()}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)  # 50ms 间隔，给前端渲染时间

    # 发送所有边
    edges_payload = [e.model_dump() for e in data.edges]
    yield f"data: {json.dumps({'type': 'edges', 'edges': edges_payload}, ensure_ascii=False)}\n\n"

    # 完成信号
    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"


@router.post("/generate-graph")
async def generate_graph(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """AI生成知识图谱 — SSE 流式返回（F5）。
    响应格式：text/event-stream，每条 data 行为 JSON，type 字段区分类型：
      meta   → {interpretation, targetNodeId, totalNodes}
      node   → {node: GraphNode}
      edges  → {edges: [...]}
      done   → {}
      error  → {error: {code, message}}
    """
    return StreamingResponse(
        _stream_graph_nodes(request, current_user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-graph-v2")
async def generate_graph_v2(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """
    Multi-agent knowledge graph generation, streamed as SSE.

    Event types:
      skeleton          -> {nodes, edges, targetNodeId, total_nodes}
      node_ready        -> {node_id, why, what, mastery, prompt, resources}
      node_error        -> non-fatal node content failure
      integration_done  -> {revised_nodes}
      done
      error             -> fatal failure
    """
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None

    return StreamingResponse(
        ai_service.generate_graph_v2_stream(
            interpretation=request.interpretation,
            original_input=request.input,
            user_background=user_bg,
            learning_purpose=request.learning_purpose,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class ClarifyGoalRequest(BaseModel):
    originalGoal: str
    newGoal: str
    planId: Optional[str] = None

    @field_validator("newGoal")
    @classmethod
    def validate_new_goal_length(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("New goal must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("New goal must be less than 2000 characters")
        return v


class ClarifyGoalResponseWrapper(BaseModel):
    success: bool
    data: dict


@router.post(
    "/clarify-goal",
    response_model=ClarifyGoalResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def clarify_goal(
    request: ClarifyGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    existing_nodes = []
    if request.planId:
        plan = db.execute(
            "SELECT user_id FROM plans WHERE id = ?", (request.planId,)
        ).fetchone()
        if plan:
            if plan["user_id"] != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "FORBIDDEN", "message": "Forbidden"},
                )
            rows = db.execute(
                "SELECT id, name, status FROM nodes WHERE plan_id = ?",
                (request.planId,),
            ).fetchall()
            existing_nodes = [
                {"id": r["id"], "name": r["name"], "status": r["status"]} for r in rows
            ]

    ai_service = get_ai_service()
    result = await ai_service.clarify_goal(
        original_goal=request.originalGoal,
        new_goal=request.newGoal,
        existing_nodes=existing_nodes,
    )
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )
    return {"success": True, "data": result.data.model_dump() if result.data else {}}


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _deterministic_recommend_next(nodes, edges) -> dict:
    def row_get(row, key, default=None):
        if hasattr(row, "get"):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default

    node_list = [
        {
            "id": n["id"],
            "name": n["name"],
            "status": n["status"],
            "is_target": bool(n["is_target"]),
            "target_end_date": row_get(n, "target_end_date"),
        }
        for n in nodes
    ]
    if not node_list:
        return {
            "recommended_node_id": None,
            "reason": "当前计划还没有可推荐的节点。",
            "recommendation_source": "local",
        }

    node_by_id = {node["id"]: node for node in node_list}
    prerequisites_by_node = {}
    for edge in edges:
        prerequisites_by_node.setdefault(edge["to_node_id"], []).append(edge["from_node_id"])

    unlearned_nodes = [node for node in node_list if node["status"] == "unlearned"]
    ready_nodes = []
    for node in unlearned_nodes:
        prerequisite_ids = prerequisites_by_node.get(node["id"], [])
        if all(node_by_id.get(prereq, {}).get("status") != "unlearned" for prereq in prerequisite_ids):
            ready_nodes.append(node)

    candidates = ready_nodes or unlearned_nodes
    if not candidates:
        return {
            "recommended_node_id": None,
            "reason": "当前计划没有未学习节点，可以复盘或归档计划。",
            "recommendation_source": "local",
        }

    def sort_key(node):
        due = str(node["target_end_date"] or "9999-12-31T23:59:59")
        return (due, 0 if node["is_target"] else 1, node["name"])

    selected = sorted(candidates, key=sort_key)[0]
    if ready_nodes:
        reason = "基于本地依赖关系推荐：这个节点的前置节点已经完成或不阻塞当前学习。"
    else:
        reason = "基于本地规则推荐：当前没有完全就绪节点，先从未学习节点中选择一个继续推进。"

    return {
        "recommended_node_id": selected["id"],
        "reason": reason,
        "recommendation_source": "local",
    }


@router.post("/explain-topic")
async def explain_topic(
    request: ExplainTopicRequest,
    http_request: Request,
    current_user_id: str = Depends(get_current_user_id),
):
    """F7: AI 解释 what 列表中的某个主题，带 content_cache 缓存。

    所有 DB 读取使用独立 get_db_context() 连接，避免 DI 生命周期与 StreamingResponse 冲突。
    """
    node_id = request.nodeId
    topic_index = request.topicIndex
    cache_key = str(topic_index)

    # ── 1. 同步完成 ownership check + cache read ──
    node_id_exists = False
    cached_text = None

    with get_db_context() as db:
        row = db.execute(
            "SELECT plan_id, content_cache FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()

        if row:
            node_id_exists = True
            plan_row = db.execute(
                "SELECT user_id FROM plans WHERE id = ?", (row["plan_id"],)
            ).fetchone()
            if not plan_row or plan_row["user_id"] != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail={"success": False, "error": {"code": "FORBIDDEN", "message": "Forbidden"}},
                )

            # Check cache
            cache = row["content_cache"] or {}
            if isinstance(cache, str):
                try:
                    cache = json.loads(cache)
                except Exception:
                    cache = {}
            cached_text = cache.get(cache_key)

    # ── 2. 构建 SSE 生成器（不依赖 db session）──
    ai_service = get_ai_service()
    topic_text = request.topicText
    node_name = request.nodeContext.nodeName
    plan_title = request.nodeContext.planTitle
    why = request.nodeContext.why

    async def _stream() -> AsyncGenerator[str, None]:
        import logging
        _log = logging.getLogger("ai.explain_topic")
        try:
            # Cache hit → replay in one chunk
            if cached_text:
                yield f"data: {json.dumps({'type': 'chunk', 'text': cached_text}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'cached': True})}\n\n"
                return

            # Cache miss → stream from LLM, write cache with fresh DB connection
            accumulated: list[str] = []
            chunk_count = 0
            try:
                async for chunk in ai_service.explain_topic_stream(
                    topic_text=topic_text,
                    node_name=node_name,
                    plan_title=plan_title,
                    why=why,
                ):
                    if await http_request.is_disconnected():
                        return
                    accumulated.append(chunk)
                    chunk_count += 1
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)
                _log.info(f"explain_topic_stream finished: {chunk_count} chunks")
            except Exception as e:
                _log.error(f"explain_topic_stream error: {type(e).__name__}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': {'code': 'AI_ERROR', 'message': str(e)}})}\n\n"
                return
        except Exception as outer_e:
            _log.error(f"_stream() outer error: {type(outer_e).__name__}: {outer_e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': {'code': 'STREAM_ERROR', 'message': str(outer_e)}})}\n\n"
            return

        # Write to cache
        full_text = "".join(accumulated)
        if full_text and node_id_exists:
            try:
                with get_db_context() as db2:
                    db2.execute(
                        "UPDATE nodes SET content_cache = content_cache || ? WHERE id = ?",
                        ({cache_key: full_text}, node_id),
                    )
                    db2.commit()
            except Exception:
                pass  # cache write failure is non-fatal

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _stream_chat(
    request: ChatRequest,
    current_user_id: str,
    http_request: Request | None = None,
) -> AsyncGenerator[str, None]:
    """F4: SSE generator for contextual chat."""
    ai_service = get_ai_service()
    node_name = request.nodeContext.nodeName if request.nodeContext else ""
    plan_title = request.nodeContext.planTitle if request.nodeContext else None

    messages_input = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        if request.enableWebSearch:
            yield f"data: {json.dumps({'type': 'search_status', 'status': 'searching'}, ensure_ascii=False)}\n\n"

        session = await ai_service.prepare_chat_session(
            messages_input=messages_input,
            node_name=node_name,
            plan_title=plan_title,
            enable_web_search=request.enableWebSearch,
        )

        async for chunk in ai_service.stream_chat_session(session):
            if http_request and await http_request.is_disconnected():
                return
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

        if request.enableWebSearch:
            if session["sources"]:
                yield f"data: {json.dumps({'type': 'sources', 'sources': session['sources']}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'search_status', 'status': 'done'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'search_status', 'status': 'fallback'}, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': {'code': 'AI_ERROR', 'message': str(e)}})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    http_request: Request,
    current_user_id: str = Depends(get_current_user_id),
):
    """F4: AI 聊天助手 — SSE 流式对话，结合节点学习上下文。"""
    return StreamingResponse(
        _stream_chat(request, current_user_id, http_request),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


class RecommendNextRequest(BaseModel):
    planId: str


class RecommendNextResponseWrapper(BaseModel):
    success: bool
    data: dict


@router.post(
    "/recommend-next",
    response_model=RecommendNextResponseWrapper,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def recommend_next(
    request: RecommendNextRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    plan = db.execute(
        "SELECT id, user_id, title, target_node_id FROM plans WHERE id = ?",
        (request.planId,),
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

    ensure_schema_columns(db, {"nodes": ("target_end_date",)})

    nodes = db.execute(
        "SELECT id, name, status, is_target, target_end_date FROM nodes WHERE plan_id = ?",
        (request.planId,),
    ).fetchall()
    edges = db.execute(
        "SELECT from_node_id, to_node_id FROM edges WHERE plan_id = ?",
        (request.planId,),
    ).fetchall()
    profile_row = db.execute(
        "SELECT occupation, math_level, programming_level, abilities FROM user_profiles WHERE user_id = ?",
        (current_user_id,),
    ).fetchone()

    graph = {
        "nodes": [
            {
                "id": n["id"],
                "name": n["name"],
                "status": n["status"],
                "isTarget": bool(n["is_target"]),
            }
            for n in nodes
        ],
        "edges": [
            {"from_node": e["from_node_id"], "to_node": e["to_node_id"]} for e in edges
        ],
        "target_node_id": plan["target_node_id"],
    }
    local_recommendation = _deterministic_recommend_next(nodes, edges)

    user_profile = {}
    if profile_row:
        abilities = profile_row["abilities"]
        if isinstance(abilities, str):
            abilities = json.loads(abilities)
        user_profile = {
            "occupation": profile_row["occupation"] or "",
            "math_level": profile_row["math_level"] or "入门",
            "programming_level": profile_row["programming_level"] or "入门",
            "abilities": abilities or [],
        }

    history = get_learning_history(
        user_id=current_user_id, plan_id=request.planId, db=db
    )

    ai_service = get_ai_service()
    try:
        result = await asyncio.wait_for(
            ai_service.recommend_next(
                graph=graph,
                user_profile=user_profile,
                learning_history=history,
                learning_goal=plan["title"],
            ),
            timeout=8,
        )
    except Exception:
        result = None

    if not result or not result.success:
        return {"success": True, "data": local_recommendation}

    payload = result.data.model_dump(by_alias=True) if result.data else {}
    if not payload.get("recommended_node_id"):
        payload = local_recommendation
    else:
        payload["recommendation_source"] = "ai"
    return {
        "success": True,
        "data": payload,
    }
