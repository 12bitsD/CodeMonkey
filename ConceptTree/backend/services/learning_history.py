"""Queries the database for a user's learning session history on a single plan.

This module provides one function — :func:`get_learning_history` — that
summarises what a user has done in a given learning plan.  The result dict
is passed directly to :meth:`~services.ai_service.AIService.recommend_next`
so the LLM knows which nodes are already learned or skipped.

Primary reader: backend developer wiring the recommendation endpoint or
writing tests against the ``learning_sessions`` table.

Key things to understand:
  1. Three SQL queries are executed per call: last session lookup, learned
     nodes, and skipped nodes — all scoped to ``(user_id, plan_id)``.
  2. The ``action`` column in ``learning_sessions`` uses two string values
     that drive the query filters: ``'learned'`` and ``'skipped'``.
  3. The returned dict shape is fixed and consumed directly by the AI layer;
     changing key names here requires updating the prompt configs too.
"""

from typing import Dict, Any


def get_learning_history(user_id: str, plan_id: str, db) -> Dict[str, Any]:
    """Return a summary of a user's learning activity for one plan.

    Executes three queries against the ``learning_sessions`` table to
    build a snapshot of the user's progress:

    - **last_node / last_session**: name and timestamp of the most recently
      visited node, useful for resuming a session.
    - **learned_nodes**: distinct node IDs where ``action = 'learned'``.
    - **skipped_nodes**: distinct node IDs where ``action = 'skipped'``.

    This dict is consumed by
    :meth:`~services.ai_service.AIService.recommend_next` to inform the
    LLM which prerequisite nodes have already been completed.

    Args:
        user_id: The authenticated user's ID.
        plan_id: The learning plan's ID whose history to retrieve.
        db: An active SQLite database connection (as provided by the
            FastAPI dependency injector via ``Depends(get_db)``).

    Returns:
        A dict with four keys:

        .. code-block:: python

            {
                "last_node":     str | None,   # name of the last visited node
                "last_session":  str | None,   # ISO timestamp of last session
                "learned_nodes": list[str],    # node IDs marked 'learned'
                "skipped_nodes": list[str],    # node IDs marked 'skipped'
            }
    """
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
