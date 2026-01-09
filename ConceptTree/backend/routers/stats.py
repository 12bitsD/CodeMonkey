from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import json

from database import get_db

router = APIRouter(prefix="/api", tags=["stats"])

USER_ID = "u_test"


def parse_json_field(field_value, default=[]):
    if not field_value:
        return default
    try:
        return json.loads(field_value)
    except json.JSONDecodeError:
        return default


@router.get("/stats/overview")
def get_stats_overview(db=Depends(get_db)):
    completed_plans = db.execute(
        "SELECT COUNT(*) as count FROM plans WHERE user_id = ? AND status = 'archived' AND progress = total AND total > 0",
        (USER_ID,)
    ).fetchone()["count"]

    active_plans = db.execute(
        "SELECT COUNT(*) as count FROM plans WHERE user_id = ? AND status = 'active'",
        (USER_ID,)
    ).fetchone()["count"]

    profile = db.execute(
        "SELECT mastered_knowledge FROM user_profiles WHERE user_id = ?",
        (USER_ID,)
    ).fetchone()
    mastered_knowledge = 0
    if profile:
        mastered_list = parse_json_field(profile["mastered_knowledge"])
        mastered_knowledge = len(mastered_list)

    total_notes = db.execute(
        "SELECT COUNT(*) as count FROM notes WHERE user_id = ?",
        (USER_ID,)
    ).fetchone()["count"]

    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    completed_nodes_this_week = db.execute(
        """SELECT COUNT(*) as count FROM learning_sessions 
           WHERE user_id = ? AND action = 'learned' AND created_at >= ?""",
        (USER_ID, week_ago)
    ).fetchone()["count"]

    new_notes_this_week = db.execute(
        "SELECT COUNT(*) as count FROM notes WHERE user_id = ? AND created_at >= ?",
        (USER_ID, week_ago)
    ).fetchone()["count"]

    return {
        "success": True,
        "data": {
            "summary": {
                "completedPlans": completed_plans,
                "activePlans": active_plans,
                "masteredKnowledge": mastered_knowledge,
                "totalNotes": total_notes
            },
            "thisWeek": {
                "completedNodes": completed_nodes_this_week,
                "newNotes": new_notes_this_week
            }
        }
    }


@router.get("/stats/distribution")
def get_stats_distribution(db=Depends(get_db)):
    rows = db.execute(
        """SELECT n.domain, COUNT(*) as count
           FROM nodes n
           JOIN plans p ON n.plan_id = p.id
           WHERE p.user_id = ? AND n.status = 'learned' AND n.domain IS NOT NULL AND n.domain != ''
           GROUP BY n.domain
           ORDER BY count DESC""",
        (USER_ID,)
    ).fetchall()

    total = sum(row["count"] for row in rows)

    distribution = []
    for row in rows:
        percentage = round(row["count"] * 100 / total) if total > 0 else 0
        distribution.append({
            "domain": row["domain"],
            "count": row["count"],
            "percentage": percentage
        })

    return {
        "success": True,
        "data": {
            "distribution": distribution,
            "total": total
        }
    }
