from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from database import DbSession


def mask_email(email: str) -> str:
    local, separator, domain = (email or "").partition("@")
    if not separator:
        return "***"
    visible = local[:1]
    return f"{visible}***@{domain}"


def _encode_cursor(created_at: Any, row_id: str) -> str:
    raw = f"{created_at}|{row_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        created_at, row_id = decoded.rsplit("|", 1)
        if not created_at or not row_id:
            raise ValueError
        return created_at, row_id
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_CURSOR", "message": "分页游标无效"},
        )


def get_overview(db: DbSession, start: datetime, end: datetime) -> dict[str, Any]:
    row = db.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM users) AS total_users,
          (SELECT COUNT(*) FROM users WHERE created_at >= ? AND created_at < ?) AS new_users,
          (SELECT COUNT(*) FROM plans WHERE created_at >= ? AND created_at < ?) AS plans_created,
          (SELECT COUNT(*) FROM plans WHERE status = 'active') AS active_plans,
          (SELECT COUNT(*) FROM learning_sessions WHERE created_at >= ? AND created_at < ?) AS learning_events,
          (SELECT COUNT(*) FROM deep_learn_sessions WHERE created_at >= ? AND created_at < ?) AS deep_sessions,
          (SELECT COUNT(*) FROM deep_learn_sessions WHERE status = 'completed' AND ended_at >= ? AND ended_at < ?) AS completed_sessions,
          (SELECT COUNT(*) FROM notes WHERE created_at >= ? AND created_at < ?) AS notes_created,
          (SELECT COUNT(*) FROM session_trace_events WHERE status = 'error' AND created_at >= ? AND created_at < ?) AS trace_errors,
          (SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0)
             FROM session_trace_events WHERE created_at >= ? AND created_at < ?) AS total_tokens,
          (SELECT COALESCE(SUM(estimated_cost_usd), 0)
             FROM session_trace_events WHERE created_at >= ? AND created_at < ?) AS estimated_cost_usd,
          (SELECT COUNT(estimated_cost_usd) > 0
             FROM session_trace_events WHERE created_at >= ? AND created_at < ?) AS cost_tracking_available,
          (SELECT COUNT(DISTINCT user_id) FROM (
             SELECT user_id FROM learning_sessions WHERE created_at >= ? AND created_at < ?
             UNION
             SELECT user_id FROM deep_learn_sessions WHERE updated_at >= ? AND updated_at < ?
           ) activity) AS active_users
        """,
        (
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end,
            start, end, start, end,
        ),
    ).fetchone()
    values = dict(row or {})
    started = int(values.get("deep_sessions") or 0)
    completed = int(values.get("completed_sessions") or 0)
    return {
        "totalUsers": int(values.get("total_users") or 0),
        "newUsers": int(values.get("new_users") or 0),
        "plansCreated": int(values.get("plans_created") or 0),
        "activePlans": int(values.get("active_plans") or 0),
        "learningEvents": int(values.get("learning_events") or 0),
        "deepSessions": started,
        "completedSessions": completed,
        "notesCreated": int(values.get("notes_created") or 0),
        "traceErrors": int(values.get("trace_errors") or 0),
        "totalTokens": int(values.get("total_tokens") or 0),
        "estimatedCostUsd": float(values.get("estimated_cost_usd") or 0),
        "costTrackingAvailable": bool(values.get("cost_tracking_available")),
        "activeUsers": int(values.get("active_users") or 0),
        "completionRate": round(completed / started, 4) if started else 0,
    }


def get_timeseries(db: DbSession, start: datetime, end: datetime) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        WITH days AS (
          SELECT generate_series(date_trunc('day', ?::timestamptz),
                                 date_trunc('day', ?::timestamptz),
                                 interval '1 day') AS day
        ), activity AS (
          SELECT date_trunc('day', created_at) AS day, COUNT(DISTINCT user_id) AS active_users
          FROM learning_sessions WHERE created_at >= ? AND created_at < ? GROUP BY 1
        ), deep AS (
          SELECT date_trunc('day', created_at) AS day, COUNT(*) AS sessions
          FROM deep_learn_sessions WHERE created_at >= ? AND created_at < ? GROUP BY 1
        )
        SELECT days.day,
               COALESCE(activity.active_users, 0) AS active_users,
               COALESCE(deep.sessions, 0) AS deep_sessions
        FROM days
        LEFT JOIN activity USING (day)
        LEFT JOIN deep USING (day)
        ORDER BY days.day
        """,
        (start, end, start, end, start, end),
    ).fetchall()
    return [
        {
            "day": row["day"],
            "activeUsers": int(row["active_users"] or 0),
            "deepSessions": int(row["deep_sessions"] or 0),
        }
        for row in rows
    ]


def list_users(
    db: DbSession,
    *,
    limit: int,
    cursor: str | None,
    query: str | None,
) -> dict[str, Any]:
    decoded = _decode_cursor(cursor)
    cursor_time, cursor_id = decoded if decoded else (None, None)
    normalized_query = query.strip() if query and query.strip() else None
    rows = db.execute(
        """
        SELECT users.id, users.email, users.created_at,
               (SELECT COUNT(*) FROM plans WHERE plans.user_id = users.id) AS plan_count,
               (SELECT COUNT(*) FROM deep_learn_sessions
                  WHERE deep_learn_sessions.user_id = users.id) AS deep_session_count,
               (SELECT COUNT(*) FROM notes WHERE notes.user_id = users.id) AS note_count,
               (SELECT MAX(updated_at) FROM deep_learn_sessions
                  WHERE deep_learn_sessions.user_id = users.id) AS last_active_at
        FROM users
        WHERE (? IS NULL OR users.email ILIKE '%' || ? || '%' OR users.id = ?)
          AND (? IS NULL OR (users.created_at, users.id) < (?::timestamptz, ?))
        ORDER BY users.created_at DESC, users.id DESC
        LIMIT ?
        """,
        (
            normalized_query,
            normalized_query,
            normalized_query,
            cursor_time,
            cursor_time,
            cursor_id,
            limit + 1,
        ),
    ).fetchall()
    has_more = len(rows) > limit
    visible = rows[:limit]
    items = [
        {
            "id": str(row["id"]),
            "email": mask_email(row["email"]),
            "createdAt": row["created_at"],
            "lastActiveAt": row["last_active_at"],
            "planCount": row["plan_count"],
            "deepSessionCount": row["deep_session_count"],
            "noteCount": row["note_count"],
        }
        for row in visible
    ]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = _encode_cursor(last["created_at"], str(last["id"]))
    return {"items": items, "nextCursor": next_cursor}


def get_user_detail(db: DbSession, user_id: str) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT users.id, users.email, users.created_at,
               user_profiles.occupation, user_profiles.education,
               user_profiles.programming_level, user_profiles.math_level,
               user_profiles.mastered_knowledge,
               (SELECT COUNT(*) FROM plans WHERE plans.user_id = users.id) AS plan_count,
               (SELECT COUNT(*) FROM deep_learn_sessions WHERE deep_learn_sessions.user_id = users.id) AS deep_session_count,
               (SELECT COUNT(*) FROM notes WHERE notes.user_id = users.id) AS note_count
        FROM users
        LEFT JOIN user_profiles ON user_profiles.user_id = users.id
        WHERE users.id = ?
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "email": mask_email(row["email"]),
        "createdAt": row["created_at"],
        "profile": {
            "occupation": row["occupation"],
            "education": row["education"],
            "programmingLevel": row["programming_level"],
            "mathLevel": row["math_level"],
            "masteredKnowledgeCount": len(row["mastered_knowledge"] or []),
        },
        "planCount": row["plan_count"],
        "deepSessionCount": row["deep_session_count"],
        "noteCount": row["note_count"],
    }


def list_sessions(
    db: DbSession,
    *,
    limit: int,
    cursor: str | None,
    user_id: str | None,
    status: str | None,
    state: str | None,
) -> dict[str, Any]:
    decoded = _decode_cursor(cursor)
    cursor_time, cursor_id = decoded if decoded else (None, None)
    rows = db.execute(
        """
        SELECT sessions.id, sessions.user_id, users.email, sessions.plan_id,
               plans.title AS plan_title, sessions.node_id, nodes.name AS node_name,
               sessions.state, sessions.status, sessions.created_at, sessions.updated_at,
               sessions.ended_at, sessions.test_results,
               COALESCE(jsonb_array_length(sessions.recent_turns), 0) AS recent_turn_count
        FROM deep_learn_sessions AS sessions
        JOIN users ON users.id = sessions.user_id
        JOIN plans ON plans.id = sessions.plan_id
        JOIN nodes ON nodes.id = sessions.node_id
        WHERE (? IS NULL OR sessions.user_id = ?)
          AND (? IS NULL OR sessions.status = ?)
          AND (? IS NULL OR sessions.state = ?)
          AND (? IS NULL OR (sessions.created_at, sessions.id) < (?::timestamptz, ?))
        ORDER BY sessions.created_at DESC, sessions.id DESC
        LIMIT ?
        """,
        (
            user_id,
            user_id,
            status,
            status,
            state,
            state,
            cursor_time,
            cursor_time,
            cursor_id,
            limit + 1,
        ),
    ).fetchall()
    has_more = len(rows) > limit
    visible = rows[:limit]
    items = []
    for row in visible:
        items.append(
            {
                "id": str(row["id"]),
                "user": {"id": str(row["user_id"]), "email": mask_email(row["email"])},
                "plan": {"id": str(row["plan_id"]), "title": row["plan_title"]},
                "node": {"id": str(row["node_id"]), "name": row["node_name"]},
                "state": row["state"],
                "status": row["status"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "endedAt": row["ended_at"],
                "recentTurnCount": row["recent_turn_count"],
                "testResultCount": len(row["test_results"] or []),
            }
        )
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = _encode_cursor(last["created_at"], str(last["id"]))
    return {"items": items, "nextCursor": next_cursor}


def get_session_detail(db: DbSession, session_id: str) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT sessions.*, users.email, plans.title AS plan_title, nodes.name AS node_name
        FROM deep_learn_sessions AS sessions
        JOIN users ON users.id = sessions.user_id
        JOIN plans ON plans.id = sessions.plan_id
        JOIN nodes ON nodes.id = sessions.node_id
        WHERE sessions.id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    turns = row["recent_turns"] or []
    return {
        "id": str(row["id"]),
        "user": {"id": str(row["user_id"]), "email": mask_email(row["email"])},
        "plan": {"id": str(row["plan_id"]), "title": row["plan_title"]},
        "node": {"id": str(row["node_id"]), "name": row["node_name"]},
        "state": row["state"],
        "status": row["status"],
        "difficultyLevel": row["difficulty_level"],
        "currentConceptIndex": row["current_concept_index"],
        "weakPoints": row["weak_points"] or [],
        "conceptsStatus": row["concepts_status"] or {},
        "testResults": row["test_results"] or [],
        "conversationSummary": row["conversation_summary"],
        "recentTurns": [
            {
                "role": turn.get("role"),
                "type": turn.get("type"),
                "contentLength": len(str(turn.get("content") or "")),
            }
            for turn in turns
        ],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "endedAt": row["ended_at"],
    }


def get_ai_usage(db: DbSession, start: datetime, end: datetime) -> dict[str, Any]:
    rows = db.execute(
        """
        SELECT provider, model, COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE status = 'error') AS errors,
               COUNT(estimated_cost_usd) AS priced_calls,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens,
               COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
               COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
        FROM session_trace_events
        WHERE provider IS NOT NULL AND created_at >= ? AND created_at < ?
        GROUP BY provider, model
        ORDER BY calls DESC
        """,
        (start, end),
    ).fetchall()
    return {
        "models": [
            {
                "provider": row["provider"],
                "model": row["model"],
                "calls": int(row["calls"] or 0),
                "errors": int(row["errors"] or 0),
                "inputTokens": int(row["input_tokens"] or 0),
                "outputTokens": int(row["output_tokens"] or 0),
                "estimatedCostUsd": float(row["estimated_cost_usd"] or 0),
                "avgDurationMs": round(float(row["avg_duration_ms"] or 0), 2),
                "costTrackingAvailable": int(row["priced_calls"] or 0) > 0,
            }
            for row in rows
        ]
    }
