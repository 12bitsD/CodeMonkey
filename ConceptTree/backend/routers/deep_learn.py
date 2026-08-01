from __future__ import annotations

import logging
from threading import Lock
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from database import DbSession, ensure_schema_columns, get_db, get_db_context
from models_deep_learn import (
    CommandRequest,
    CreateSessionData,
    CreateSessionRequest,
    MessageRequest,
)
from services.deep_learn.notes_repo import get_completion_note_by_id
from services.deep_learn.service import DeepLearnService
from services.deep_learn.session_repo import get_session_by_id
from utils.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deep-learn", tags=["DeepLearn"])
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

_service = DeepLearnService()
_DEEP_LEARN_SCHEMA_READY = False
_DEEP_LEARN_SCHEMA_LOCK = Lock()


def _ensure_deep_learn_schema(db: DbSession) -> None:
    global _DEEP_LEARN_SCHEMA_READY
    if _DEEP_LEARN_SCHEMA_READY:
        return
    with _DEEP_LEARN_SCHEMA_LOCK:
        if _DEEP_LEARN_SCHEMA_READY:
            return
        ensure_schema_columns(
            db,
            {
                "deep_learn_sessions": (
                    "id",
                    "user_id",
                    "plan_id",
                    "node_id",
                    "state",
                    "current_concept_index",
                    "difficulty_level",
                    "wrong_count_current",
                    "concepts_status",
                    "weak_points",
                    "recent_turns",
                    "what_list",
                    "conversation_summary",
                    "test_questions",
                    "test_current_index",
                    "test_results",
                    "status",
                    "created_at",
                    "updated_at",
                    "ended_at",
                ),
            },
        )
        _DEEP_LEARN_SCHEMA_READY = True


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
) -> dict:
    _ensure_deep_learn_schema(db)
    row = db.execute(
        "SELECT id FROM plans WHERE id=? AND user_id=?", (req.plan_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问该计划"})

    session, node_meta = await _service.get_or_create_session(
        db=db, user_id=user_id, node_id=req.node_id, plan_id=req.plan_id,
    )
    is_resumed = session.state != "INITIALIZING"
    data = CreateSessionData(
        session_id=session.id,
        state=session.state,
        is_resumed=is_resumed,
        node_name=node_meta["node_name"],
        node_why=node_meta["node_why"],
        what_list=session.what_list,
        concepts_status=session.concepts_status,
        weak_points=session.weak_points,
        current_concept_index=session.current_concept_index,
        recent_turns=session.recent_turns if is_resumed else [],
    )
    return {"success": True, "data": data.model_dump()}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
) -> dict:
    _ensure_deep_learn_schema(db)
    session = get_session_by_id(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在"})
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问"})
    node_meta = _service._fetch_node_meta(db, session.node_id)
    return {"success": True, "data": {**session.model_dump(), **node_meta}}


@router.post("/sessions/{session_id}/initialize")
async def initialize(
    session_id: str,
    http_request: Request,
    background_tasks: BackgroundTasks,
    language: Literal["en-US", "zh-CN"] = "en-US",
    user_id: str = Depends(get_current_user_id),
):
    with get_db_context() as db:
        _ensure_deep_learn_schema(db)
        session = get_session_by_id(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在"})
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问"})

    with get_db_context() as db:
        node_meta = _service._fetch_node_meta(db, session.node_id)

    async def gen():
        async for event in _service.stream_initialize(
            session,
            node_meta,
            background_tasks=background_tasks,
            language=language,
        ):
            if await http_request.is_disconnected():
                return
            yield event

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    req: MessageRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    with get_db_context() as db:
        _ensure_deep_learn_schema(db)
        session = get_session_by_id(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在"})
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问"})

    with get_db_context() as db:
        node_meta = _service._fetch_node_meta(db, session.node_id)

    async def gen():
        async for event in _service.stream_message(
            session,
            node_meta,
            req.content,
            background_tasks=background_tasks,
            language=req.language,
        ):
            if await http_request.is_disconnected():
                return
            yield event

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/sessions/{session_id}/command")
async def send_command(
    session_id: str,
    req: CommandRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    with get_db_context() as db:
        _ensure_deep_learn_schema(db)
        session = get_session_by_id(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在"})
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问"})

    with get_db_context() as db:
        node_meta = _service._fetch_node_meta(db, session.node_id)

    async def gen():
        async for event in _service.stream_command(
            session,
            node_meta,
            req.command,
            background_tasks=background_tasks,
            language=req.language,
        ):
            if await http_request.is_disconnected():
                return
            yield event

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/notes/{note_id}")
async def get_completion_note(
    note_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
):
    """
    Fetch a completion note by ID.
    Returns 404 if not found, 403 if the note does not belong to the requesting user.
    """
    note = get_completion_note_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "笔记不存在"})
    if note["user_id"] != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问"})
    return {
        "id": note["id"],
        "node_id": note["node_id"],
        "session_id": note["session_id"],
        "content": note["content"],
        "created_at": note["created_at"],
    }
