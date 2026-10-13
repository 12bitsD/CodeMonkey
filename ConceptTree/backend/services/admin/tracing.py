from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
from contextvars import ContextVar
import logging
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Any, Iterator

from fastapi import HTTPException

from config import settings
from database import DbSession, get_db_context


logger = logging.getLogger(__name__)

_TRACE_CONTEXT: ContextVar[dict[str, str] | None] = ContextVar(
    "admin_trace_context", default=None
)
_QUEUE: Queue[dict[str, Any]] = Queue(maxsize=1000)
_STOP = Event()
_WORKER_LOCK = Lock()
_WORKER: Thread | None = None
_RETENTION_PRUNED = False


@contextmanager
def trace_scope(
    *, session_id: str, user_id: str, request_id: str | None = None
) -> Iterator[None]:
    token = _TRACE_CONTEXT.set(
        {"session_id": session_id, "user_id": user_id, "request_id": request_id or ""}
    )
    try:
        yield
    finally:
        _TRACE_CONTEXT.reset(token)


def emit_trace_event(
    *,
    event_type: str,
    event_name: str,
    status: str = "ok",
    session_id: str | None = None,
    user_id: str | None = None,
    request_id: str | None = None,
    duration_ms: float | None = None,
    provider: str | None = None,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    retry_count: int = 0,
    error_code: str | None = None,
    attributes: dict[str, Any] | None = None,
    redacted_input: str | None = None,
    redacted_output: str | None = None,
) -> bool:
    context = _TRACE_CONTEXT.get() or {}
    resolved_session_id = session_id or context.get("session_id")
    resolved_user_id = user_id or context.get("user_id")
    if not resolved_session_id or not resolved_user_id:
        return False

    event = {
        "session_id": resolved_session_id,
        "user_id": resolved_user_id,
        "request_id": request_id or context.get("request_id") or None,
        "event_type": event_type[:64],
        "event_name": event_name[:128],
        "status": status[:32],
        "duration_ms": duration_ms,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "retry_count": max(retry_count, 0),
        "error_code": error_code,
        "attributes": attributes or {},
        "redacted_input": (redacted_input or "")[:500] or None,
        "redacted_output": (redacted_output or "")[:500] or None,
    }
    start_trace_buffer()
    try:
        _QUEUE.put_nowait(event)
        return True
    except Full:
        if status == "error":
            try:
                _QUEUE.get_nowait()
                _QUEUE.task_done()
                _QUEUE.put_nowait(event)
                return True
            except (Empty, Full):
                pass
        logger.warning("Trace buffer full; dropping event type=%s", event_type)
        return False


def _insert_event(db: DbSession, event: dict[str, Any]) -> None:
    db.execute(
        """
        INSERT INTO session_trace_events (
          session_id, user_id, request_id, event_type, event_name, status,
          duration_ms, provider, model, input_tokens, output_tokens,
          estimated_cost_usd, retry_count, error_code, attributes,
          redacted_input, redacted_output
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["session_id"], event["user_id"], event["request_id"],
            event["event_type"], event["event_name"], event["status"],
            event["duration_ms"], event["provider"], event["model"],
            event["input_tokens"], event["output_tokens"],
            event["estimated_cost_usd"], event["retry_count"],
            event["error_code"], event["attributes"],
            event["redacted_input"], event["redacted_output"],
        ),
    )


def _persist_batch(batch: list[dict[str, Any]]) -> None:
    global _RETENTION_PRUNED
    try:
        with get_db_context() as db:
            for event in batch:
                _insert_event(db, event)
            db.commit()
    except Exception as error:
        logger.warning("Trace persistence failed; dropping %d events: %s", len(batch), error)
        return

    if not _RETENTION_PRUNED:
        try:
            with get_db_context() as db:
                db.execute(
                    """
                    DELETE FROM session_trace_events
                    WHERE created_at < NOW() - (? * INTERVAL '1 day')
                    """,
                    (max(settings.ADMIN_TRACE_RETENTION_DAYS, 1),),
                )
                db.commit()
            _RETENTION_PRUNED = True
        except Exception as error:
            logger.warning("Trace retention cleanup failed: %s", error)


def _worker_loop() -> None:
    while not _STOP.is_set() or not _QUEUE.empty():
        try:
            first = _QUEUE.get(timeout=0.25)
        except Empty:
            continue
        batch = [first]
        while len(batch) < 50:
            try:
                batch.append(_QUEUE.get_nowait())
            except Empty:
                break
        _persist_batch(batch)
        for _ in batch:
            _QUEUE.task_done()


def start_trace_buffer() -> None:
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER and _WORKER.is_alive():
            return
        _STOP.clear()
        _WORKER = Thread(target=_worker_loop, name="admin-trace-writer", daemon=True)
        _WORKER.start()


def stop_trace_buffer(timeout: float = 2.0) -> None:
    global _WORKER
    with _WORKER_LOCK:
        worker = _WORKER
        if not worker:
            return
        _STOP.set()
    worker.join(timeout=timeout)
    with _WORKER_LOCK:
        if _WORKER is worker and not worker.is_alive():
            _WORKER = None


def _encode_trace_cursor(created_at: Any, event_id: str) -> str:
    raw = f"{created_at}|{event_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_trace_cursor(cursor: str | None) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        created_at, event_id = raw.rsplit("|", 1)
        if not created_at or not event_id:
            raise ValueError
        return created_at, event_id
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_CURSOR", "message": "分页游标无效"},
        )


def list_session_trace(
    db: DbSession,
    session_id: str,
    *,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    decoded = _decode_trace_cursor(cursor)
    cursor_time, cursor_id = decoded if decoded else (None, None)
    rows = db.execute(
        """
        SELECT id, session_id, request_id, event_type, event_name, status,
               duration_ms, provider, model, input_tokens, output_tokens,
               estimated_cost_usd, retry_count, error_code, attributes,
               redacted_input, redacted_output, created_at
        FROM session_trace_events
        WHERE session_id = ?
          AND (? IS NULL OR (created_at, id) > (?::timestamptz, ?::uuid))
        ORDER BY created_at ASC, id ASC
        LIMIT ?
        """,
        (session_id, cursor_time, cursor_time, cursor_id, limit + 1),
    ).fetchall()
    has_more = len(rows) > limit
    visible = rows[:limit]
    items = [
        {
            "id": str(row["id"]),
            "sessionId": str(row["session_id"]),
            "requestId": row["request_id"],
            "eventType": row["event_type"],
            "eventName": row["event_name"],
            "status": row["status"],
            "durationMs": row["duration_ms"],
            "provider": row["provider"],
            "model": row["model"],
            "inputTokens": row["input_tokens"],
            "outputTokens": row["output_tokens"],
            "estimatedCostUsd": float(row["estimated_cost_usd"] or 0),
            "retryCount": row["retry_count"],
            "errorCode": row["error_code"],
            "attributes": row["attributes"] or {},
            "redactedInput": row["redacted_input"],
            "redactedOutput": row["redacted_output"],
            "createdAt": row["created_at"],
        }
        for row in visible
    ]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = _encode_trace_cursor(last["created_at"], str(last["id"]))
    return {"items": items, "nextCursor": next_cursor}
