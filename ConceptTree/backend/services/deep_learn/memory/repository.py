"""Memory Repository — CRUD for the three memory tables.

All write functions catch exceptions and log; they never raise.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from database import DbSession
from models_memory import (
    EpisodicRecord,
    LongTermMemory,
    ProceduralPattern,
    VALID_PROCEDURAL_KEYS,
)

logger = logging.getLogger(__name__)

_NOW = lambda: datetime.now(timezone.utc).isoformat()


# ── LongTerm ──────────────────────────────────────────────────────────────────

def get_long_term(db: DbSession, user_id: str) -> Optional[LongTermMemory]:
    try:
        row = db.execute(
            "SELECT user_id, learning_style, mastered_concepts, weak_concepts, updated_at"
            " FROM user_learning_profile WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return LongTermMemory(
            user_id=str(row["user_id"]),
            learning_style=_load_json(row["learning_style"], {}),
            mastered_concepts=_load_json(row["mastered_concepts"], []),
            weak_concepts=_load_json(row["weak_concepts"], []),
            updated_at=str(row["updated_at"]),
        )
    except Exception as e:
        logger.error("get_long_term failed: %s", e)
        return None


def upsert_long_term_style(db: DbSession, user_id: str, style: dict) -> None:
    try:
        existing = get_long_term(db, user_id)
        if existing is None:
            db.execute(
                "INSERT INTO user_learning_profile (user_id, learning_style, updated_at)"
                " VALUES (?, ?::jsonb, NOW())"
                " ON CONFLICT (user_id) DO UPDATE"
                " SET learning_style = user_learning_profile.learning_style || ?::jsonb,"
                "     updated_at = NOW()",
                (user_id, json.dumps(style), json.dumps(style)),
            )
        else:
            merged = {**existing.learning_style, **style}
            db.execute(
                "UPDATE user_learning_profile SET learning_style = ?::jsonb, updated_at = NOW()"
                " WHERE user_id = ?",
                (json.dumps(merged), user_id),
            )
        db.commit()
    except Exception as e:
        logger.error("upsert_long_term_style failed: %s", e)


def add_mastered_concept(db: DbSession, user_id: str, concept: str, node_id: str) -> None:
    try:
        _ensure_profile(db, user_id)
        row = db.execute(
            "SELECT mastered_concepts FROM user_learning_profile WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        concepts: list[dict] = _load_json(row["mastered_concepts"] if row else "[]", [])
        if any(c.get("concept") == concept and c.get("node_id") == node_id for c in concepts):
            return
        concepts.append({"concept": concept, "node_id": node_id, "mastered_at": _NOW()})
        db.execute(
            "UPDATE user_learning_profile SET mastered_concepts = ?::jsonb, updated_at = NOW()"
            " WHERE user_id = ?",
            (json.dumps(concepts), user_id),
        )
        db.commit()
    except Exception as e:
        logger.error("add_mastered_concept failed: %s", e)


def upsert_weak_concept(db: DbSession, user_id: str, concept: str, node_id: str) -> None:
    try:
        _ensure_profile(db, user_id)
        row = db.execute(
            "SELECT weak_concepts FROM user_learning_profile WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        concepts: list[dict] = _load_json(row["weak_concepts"] if row else "[]", [])
        for c in concepts:
            if c.get("concept") == concept and c.get("node_id") == node_id:
                c["occurrences"] = c.get("occurrences", 1) + 1
                break
        else:
            concepts.append({"concept": concept, "node_id": node_id, "first_seen_at": _NOW(), "occurrences": 1})
        db.execute(
            "UPDATE user_learning_profile SET weak_concepts = ?::jsonb, updated_at = NOW()"
            " WHERE user_id = ?",
            (json.dumps(concepts), user_id),
        )
        db.commit()
    except Exception as e:
        logger.error("upsert_weak_concept failed: %s", e)


# ── Episodic ──────────────────────────────────────────────────────────────────

def write_episodic_record(db: DbSession, record: EpisodicRecord) -> str:
    try:
        db.execute(
            "INSERT INTO learning_session_records"
            " (id, user_id, node_id, plan_id, session_id, summary,"
            "  concepts_covered, weak_points, strong_points, test_score,"
            "  passed, conversation_turns, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?::jsonb, ?, ?, ?, ?)"
            " ON CONFLICT (id) DO NOTHING",
            (
                record.id, record.user_id, record.node_id, record.plan_id,
                record.session_id, record.summary,
                json.dumps(record.concepts_covered),
                json.dumps(record.weak_points),
                json.dumps(record.strong_points),
                record.test_score, record.passed, record.conversation_turns,
                record.created_at,
            ),
        )
        db.commit()
        return record.id
    except Exception as e:
        logger.error("write_episodic_record failed: %s", e)
        return record.id


def get_recent_episodic_for_node(
    db: DbSession, user_id: str, node_id: str, limit: int = 1
) -> list[EpisodicRecord]:
    try:
        rows = db.execute(
            "SELECT id, user_id, node_id, plan_id, session_id, summary,"
            " concepts_covered, weak_points, strong_points, test_score,"
            " passed, conversation_turns, created_at"
            " FROM learning_session_records"
            " WHERE user_id = ? AND node_id = ?"
            " ORDER BY created_at DESC LIMIT ?",
            (user_id, node_id, limit),
        ).fetchall()
        return [_row_to_episodic(r) for r in rows]
    except Exception as e:
        logger.error("get_recent_episodic_for_node failed: %s", e)
        return []


def count_completed_sessions(db: DbSession, user_id: str) -> int:
    try:
        row = db.execute(
            "SELECT COUNT(*) AS cnt FROM learning_session_records WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["cnt"]) if row else 0
    except Exception as e:
        logger.error("count_completed_sessions failed: %s", e)
        return 0


def get_all_episodic_since(db: DbSession, user_id: str, since_count: int) -> list[EpisodicRecord]:
    try:
        rows = db.execute(
            "SELECT id, user_id, node_id, plan_id, session_id, summary,"
            " concepts_covered, weak_points, strong_points, test_score,"
            " passed, conversation_turns, created_at"
            " FROM learning_session_records"
            " WHERE user_id = ?"
            " ORDER BY created_at DESC LIMIT ?",
            (user_id, since_count),
        ).fetchall()
        return [_row_to_episodic(r) for r in rows]
    except Exception as e:
        logger.error("get_all_episodic_since failed: %s", e)
        return []


def has_episodic_record(db: DbSession, session_id: str) -> bool:
    try:
        row = db.execute(
            "SELECT id FROM learning_session_records WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        return row is not None
    except Exception as e:
        logger.error("has_episodic_record failed: %s", e)
        return False


# ── Procedural ────────────────────────────────────────────────────────────────

def get_procedural_patterns(
    db: DbSession, user_id: str, min_confidence: float = 0.0
) -> list[ProceduralPattern]:
    try:
        rows = db.execute(
            "SELECT user_id, pattern_key, pattern_value, confidence, sample_count, updated_at"
            " FROM teaching_patterns"
            " WHERE user_id = ? AND confidence >= ?"
            " ORDER BY confidence DESC",
            (user_id, min_confidence),
        ).fetchall()
        return [
            ProceduralPattern(
                user_id=str(r["user_id"]),
                pattern_key=r["pattern_key"],
                pattern_value=r["pattern_value"],
                confidence=float(r["confidence"]),
                sample_count=int(r["sample_count"]),
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        ]
    except Exception as e:
        logger.error("get_procedural_patterns failed: %s", e)
        return []


def upsert_procedural_pattern(
    db: DbSession, user_id: str, key: str, value: str, new_confidence: float
) -> None:
    if key not in VALID_PROCEDURAL_KEYS:
        logger.warning("upsert_procedural_pattern: unknown key '%s', skipping", key)
        return
    try:
        db.execute(
            "INSERT INTO teaching_patterns (user_id, pattern_key, pattern_value, confidence, sample_count, updated_at)"
            " VALUES (?, ?, ?, ?, 1, NOW())"
            " ON CONFLICT (user_id, pattern_key) DO UPDATE"
            " SET pattern_value = EXCLUDED.pattern_value,"
            "     confidence = EXCLUDED.confidence,"
            "     sample_count = teaching_patterns.sample_count + 1,"
            "     updated_at = NOW()",
            (user_id, key, value, new_confidence),
        )
        db.commit()
    except Exception as e:
        logger.error("upsert_procedural_pattern failed: %s", e)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_profile(db: DbSession, user_id: str) -> None:
    db.execute(
        "INSERT INTO user_learning_profile (user_id) VALUES (?)"
        " ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    db.commit()


def _load_json(raw, default):
    if raw is None:
        return default
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def _row_to_episodic(r) -> EpisodicRecord:
    return EpisodicRecord(
        id=str(r["id"]),
        user_id=str(r["user_id"]),
        node_id=r["node_id"],
        plan_id=r["plan_id"],
        session_id=str(r["session_id"]),
        summary=r["summary"] or "",
        concepts_covered=_load_json(r["concepts_covered"], []),
        weak_points=_load_json(r["weak_points"], []),
        strong_points=_load_json(r["strong_points"], []),
        test_score=r["test_score"],
        passed=bool(r["passed"]),
        conversation_turns=int(r["conversation_turns"]),
        created_at=str(r["created_at"]),
    )
