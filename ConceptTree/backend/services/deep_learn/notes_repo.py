from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def save_completion_note(
    db,
    *,
    user_id: str,
    node_id: str,
    session_id: str,
    content: str,
) -> Optional[str]:
    """Insert a completion note. Returns the new note UUID, or None on failure."""
    try:
        db.execute(
            """
            INSERT INTO completion_notes (user_id, node_id, session_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, node_id, session_id, content),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM completion_notes WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return str(row["id"]) if row else None
    except Exception:
        logger.exception("save_completion_note failed (non-fatal)")
        return None


def get_completion_note_by_id(db, note_id: str) -> Optional[dict]:
    """Fetch a completion note by its UUID. Returns None if not found."""
    try:
        row = db.execute(
            "SELECT id, user_id, node_id, session_id, content, created_at FROM completion_notes WHERE id=?",
            (note_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "node_id": row["node_id"],
            "session_id": str(row["session_id"]),
            "content": row["content"],
            "created_at": str(row["created_at"]),
        }
    except Exception:
        logger.exception("get_completion_note_by_id failed")
        return None


def get_completion_note_by_session(db, session_id: str) -> Optional[dict]:
    """Fetch the completion note for a session. Returns None if not found."""
    try:
        row = db.execute(
            "SELECT id, user_id, node_id, session_id, content, created_at FROM completion_notes WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "node_id": row["node_id"],
            "session_id": str(row["session_id"]),
            "content": row["content"],
            "created_at": str(row["created_at"]),
        }
    except Exception:
        logger.exception("get_completion_note_by_session failed")
        return None
