from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from database import DbSession
from models_deep_learn import SessionState


_ALLOWED_UPDATE_FIELDS = {
    "state", "current_concept_index", "difficulty_level", "wrong_count_current",
    "concepts_status", "weak_points", "recent_turns", "conversation_summary",
    "test_questions", "test_current_index", "test_results",
    "ended_at", "status",
}


def _row_to_state(row: dict) -> SessionState:
    return SessionState(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        node_id=row["node_id"],
        plan_id=row["plan_id"],
        state=row["state"],
        current_concept_index=row["current_concept_index"],
        difficulty_level=row["difficulty_level"],
        wrong_count_current=row["wrong_count_current"],
        concepts_status=row["concepts_status"] or {},
        weak_points=row["weak_points"] or [],
        recent_turns=row["recent_turns"] or [],
        what_list=row["what_list"] or [],
        test_questions=row["test_questions"] or [],
        test_current_index=row["test_current_index"],
        test_results=row["test_results"] or [],
        status=row["status"],
    )


def get_active_session(db: DbSession, user_id: str, node_id: str) -> Optional[SessionState]:
    row = db.execute(
        "SELECT * FROM deep_learn_sessions "
        "WHERE user_id=? AND node_id=? AND status='in_progress' "
        "ORDER BY updated_at DESC LIMIT 1",
        (user_id, node_id),
    ).fetchone()
    return _row_to_state(row) if row else None


def get_session_by_id(db: DbSession, session_id: str, user_id: str) -> Optional[SessionState]:
    row = db.execute(
        "SELECT * FROM deep_learn_sessions WHERE id=? AND user_id=?",
        (session_id, user_id),
    ).fetchone()
    return _row_to_state(row) if row else None


def create_session(
    db: DbSession, *, user_id: str, node_id: str, plan_id: str, what_list: list[str],
) -> SessionState:
    session_id = str(uuid.uuid4())
    concepts_status = {str(i): "pending" for i in range(len(what_list))}
    row = db.execute(
        "INSERT INTO deep_learn_sessions "
        "(id, user_id, node_id, plan_id, what_list, concepts_status) "
        "VALUES (?, ?, ?, ?, ?, ?) RETURNING *",
        (session_id, user_id, node_id, plan_id, what_list, concepts_status),
    ).fetchone()
    db.commit()
    return _row_to_state(row)


def update_session(db: DbSession, session_id: str, **fields) -> None:
    safe = {k: v for k, v in fields.items() if k in _ALLOWED_UPDATE_FIELDS}
    if not safe:
        return
    set_parts = ", ".join(f"{k}=?" for k in safe)
    values = list(safe.values()) + [session_id]
    db.execute(
        f"UPDATE deep_learn_sessions SET {set_parts}, updated_at=NOW() WHERE id=?",
        values,
    )
    db.commit()


def abandon_session(db: DbSession, session_id: str) -> None:
    update_session(db, session_id, status="abandoned", ended_at=datetime.now(timezone.utc))
