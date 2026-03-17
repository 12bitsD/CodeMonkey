from typing import Dict, Any


def get_learning_history(user_id: str, plan_id: str, db) -> Dict[str, Any]:
    last = db.execute(
        "SELECT node_name, created_at FROM learning_sessions "
        "WHERE user_id = ? AND plan_id = ? ORDER BY created_at DESC LIMIT 1",
        [user_id, plan_id],
    ).fetchone()

    learned = db.execute(
        "SELECT DISTINCT node_id FROM learning_sessions "
        "WHERE user_id = ? AND plan_id = ? AND action = 'learned'",
        [user_id, plan_id],
    ).fetchall()

    skipped = db.execute(
        "SELECT DISTINCT node_id FROM learning_sessions "
        "WHERE user_id = ? AND plan_id = ? AND action = 'skipped'",
        [user_id, plan_id],
    ).fetchall()

    return {
        "last_node": last["node_name"] if last else None,
        "last_session": str(last["created_at"]) if last else None,
        "learned_nodes": [r["node_id"] for r in learned],
        "skipped_nodes": [r["node_id"] for r in skipped],
    }
