from __future__ import annotations

import json
from typing import Any, Optional

from psycopg2.errors import UndefinedTable


def build_idempotency_id(user_id: str, endpoint: str, key: str) -> str:
    return f"{user_id}:{endpoint}:{key}"[:500]


def normalize_idempotency_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    normalized = key.strip()
    if not normalized:
        return None
    return normalized[:200]


def get_idempotent_response(db, user_id: str, endpoint: str, key: Optional[str]) -> Optional[dict[str, Any]]:
    normalized = normalize_idempotency_key(key)
    if not normalized:
        return None

    try:
        row = db.execute(
            "SELECT response FROM idempotency_keys WHERE id = ? AND user_id = ? AND endpoint = ?",
            (build_idempotency_id(user_id, endpoint, normalized), user_id, endpoint),
        ).fetchone()
    except UndefinedTable:
        db.rollback()
        return None
    if not row:
        return None

    response = row["response"]
    if isinstance(response, str):
        return json.loads(response)
    return response


def store_idempotent_response(
    db,
    user_id: str,
    endpoint: str,
    key: Optional[str],
    response: dict[str, Any],
) -> None:
    normalized = normalize_idempotency_key(key)
    if not normalized:
        return

    savepoint = "idempotency_store"
    db.execute(f"SAVEPOINT {savepoint}")
    try:
        db.execute(
            """
            INSERT INTO idempotency_keys (id, user_id, endpoint, response)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
            """,
            (build_idempotency_id(user_id, endpoint, normalized), user_id, endpoint, response),
        )
    except UndefinedTable:
        db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
    finally:
        db.execute(f"RELEASE SAVEPOINT {savepoint}")
