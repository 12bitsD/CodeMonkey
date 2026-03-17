"""学习历史服务"""

from typing import Dict, List, Any


async def get_learning_history(user_id: str, plan_id: str, db) -> Dict[str, Any]:
    """获取用户学习历史，用于AI推荐

    Args:
        user_id: 用户ID
        plan_id: 计划ID
        db: 数据库连接

    Returns:
        {
            "last_node": str | None,
            "last_session": str | None,
            "learned_nodes": List[str],
            "skipped_nodes": List[str]
        }
    """
    # 获取最后学习的节点
    last_session = await db.fetchone(
        """SELECT node_name, created_at 
           FROM learning_sessions 
           WHERE user_id = :user_id AND plan_id = :plan_id
           ORDER BY created_at DESC LIMIT 1""",
        {"user_id": user_id, "plan_id": plan_id},
    )

    # 获取已学节点（去重）
    learned_rows = await db.fetch(
        """SELECT DISTINCT node_id 
           FROM learning_sessions 
           WHERE user_id = :user_id AND plan_id = :plan_id AND action = 'learned'""",
        {"user_id": user_id, "plan_id": plan_id},
    )

    # 获取跳过节点（去重）
    skipped_rows = await db.fetch(
        """SELECT DISTINCT node_id 
           FROM learning_sessions 
           WHERE user_id = :user_id AND plan_id = :plan_id AND action = 'skipped'""",
        {"user_id": user_id, "plan_id": plan_id},
    )

    return {
        "last_node": last_session["node_name"] if last_session else None,
        "last_session": str(last_session["created_at"]) if last_session else None,
        "learned_nodes": [row["node_id"] for row in learned_rows],
        "skipped_nodes": [row["node_id"] for row in skipped_rows],
    }
