"""
Stats Router — read-only aggregations powering the user's statistics dashboard.

This router exposes two endpoints that summarise learning activity across all
of a user's plans. All data is aggregated on the fly from five underlying
tables: ``plans``, ``nodes``, ``learning_sessions``, ``notes``, and
``user_profiles``. No writes occur here.

Key facts for frontend developers:
  1. ``/stats/overview`` returns 6 metrics in a single call — use it to
     populate the entire dashboard summary card.
  2. The "this week" window is the **last 7 calendar days from UTC now**
     (timezone-unaware; may differ from a user's local week boundary).
  3. ``/stats/distribution`` only counts ``learned`` nodes that have a
     non-empty ``domain`` field; nodes without a domain are silently excluded.

Endpoints
---------
GET /stats/overview      — 6 aggregate metrics for the dashboard summary
GET /stats/distribution  — breakdown of learned nodes by subject domain
"""

from datetime import datetime, timedelta
import json

from fastapi import APIRouter, Depends

from database import get_db
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["stats"])


def parse_json_field(field_value, default=None):
    """Safely decode a JSON-encoded database column value.

    Returns the parsed Python object, or ``default`` when the value is empty
    or not valid JSON. Already-parsed lists and dicts are returned as-is.

    Args:
        field_value: Raw database column value (string, list, dict, or None).
        default: Fallback value on empty or unparseable input; defaults to
            an empty list ``[]`` when not specified.

    Returns:
        Parsed Python object, or ``default``.
    """
    if default is None:
        default = []
    if not field_value:
        return default
    if isinstance(field_value, (list, dict)):
        return field_value
    try:
        return json.loads(field_value)
    except json.JSONDecodeError:
        return default


@router.get("/stats/overview")
def get_stats_overview(
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Return 6 aggregated metrics for the user's learning dashboard.

    Aggregates data across five tables in a single request so the dashboard
    summary card can be populated with one API call. The six metrics are:

    - ``completedPlans`` — archived plans where ``progress == total > 0``
      (i.e. every non-skipped node was marked learned before archiving).
    - ``activePlans`` — plans with ``status = "active"``.
    - ``masteredNodes`` — unique concept names in the user's
      ``user_profiles.mastered_knowledge`` list (count, not names).
    - ``totalNotes`` — total rows in ``notes`` belonging to this user.
    - ``thisWeek.completedNodes`` — ``learning_sessions`` rows with
      ``action = "learned"`` in the last 7 UTC days.
    - ``thisWeek.newNotes`` — ``notes`` rows created in the last 7 UTC days.

    **Note (unverified):** "last 7 days" is computed from ``datetime.utcnow()``
    with no timezone conversion, which may not match the user's local week.

    Args:
        current_user_id: Injected from the auth token; all queries are scoped
            to this user.
        db: Injected database connection.

    Returns:
        JSON ``{"success": true, "data": { completedPlans, activePlans,
        masteredNodes, totalNotes, thisWeek: { completedNodes, newNotes } }}``.
    """
    completed_plans = db.execute(
        (
            "SELECT COUNT(*) as count FROM plans "
            "WHERE user_id = ? AND status = 'archived' "
            "AND progress = total AND total > 0"
        ),
        (current_user_id,),
    ).fetchone()["count"]

    active_plans = db.execute(
        (
            "SELECT COUNT(*) as count FROM plans "
            "WHERE user_id = ? AND status = 'active'"
        ),
        (current_user_id,),
    ).fetchone()["count"]

    profile = db.execute(
        "SELECT mastered_knowledge FROM user_profiles WHERE user_id = ?",
        (current_user_id,),
    ).fetchone()
    mastered_knowledge = 0
    if profile:
        mastered_list = parse_json_field(profile["mastered_knowledge"])
        mastered_knowledge = len(mastered_list)

    total_notes = db.execute(
        "SELECT COUNT(*) as count FROM notes WHERE user_id = ?",
        (current_user_id,),
    ).fetchone()["count"]

    week_ago = datetime.utcnow() - timedelta(days=7)

    completed_nodes_this_week = db.execute(
        """SELECT COUNT(*) as count FROM learning_sessions
           WHERE user_id = ? AND action = 'learned' AND created_at >= ?""",
        (current_user_id, week_ago),
    ).fetchone()["count"]

    new_notes_this_week = db.execute(
        (
            "SELECT COUNT(*) as count FROM notes "
            "WHERE user_id = ? AND created_at >= ?"
        ),
        (current_user_id, week_ago),
    ).fetchone()["count"]

    return {
        "success": True,
        "data": {
            "completedPlans": completed_plans,
            "activePlans": active_plans,
            "masteredNodes": mastered_knowledge,
            "totalNotes": total_notes,
            "thisWeek": {
                "completedNodes": completed_nodes_this_week,
                "newNotes": new_notes_this_week,
            },
        },
    }


@router.get("/stats/distribution")
def get_stats_distribution(
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Return the distribution of learned nodes broken down by subject domain.

    Groups all ``learned`` nodes (across all of the user's plans) by their
    ``domain`` field and computes each domain's count and percentage share of
    the total. Results are sorted by count descending so the most-studied
    domain appears first.

    Nodes with a ``NULL`` or empty ``domain`` are excluded from the results.
    Percentages are rounded to the nearest integer; the sum may not equal
    exactly 100% due to rounding.

    Args:
        current_user_id: Injected from the auth token; all queries are scoped
            to this user.
        db: Injected database connection.

    Returns:
        JSON ``{"success": true, "data": { "distribution": [ { "domain",
        "count", "percentage" }, ... ], "total" }}``. ``total`` is the count
        of all learned nodes that have a domain (the denominator for
        percentages). Returns an empty ``distribution`` list and ``total: 0``
        when no learned nodes with domains exist.
    """
    rows = db.execute(
        """SELECT n.domain, COUNT(*) as count
           FROM nodes n
           JOIN plans p ON n.plan_id = p.id
           WHERE p.user_id = ? AND n.status = 'learned'
             AND n.domain IS NOT NULL AND n.domain != ''
           GROUP BY n.domain
           ORDER BY count DESC""",
        (current_user_id,),
    ).fetchall()

    total = sum(row["count"] for row in rows)

    distribution = []
    for row in rows:
        percentage = round(row["count"] * 100 / total) if total > 0 else 0
        distribution.append(
            {
                "domain": row["domain"],
                "count": row["count"],
                "percentage": percentage,
            }
        )

    return {
        "success": True,
        "data": {"distribution": distribution, "total": total},
    }
