"""MemoryContextBuilder — pure string assembly, no LLM calls."""

from __future__ import annotations

import logging

from database import DbSession
from models_deep_learn import SessionState
from services.deep_learn.memory import repository as repo

logger = logging.getLogger(__name__)


class MemoryContextBuilder:
    MAX_LENGTH = 800

    def build(self, db: DbSession, user_id: str, node_id: str, session: SessionState) -> str:
        try:
            return self._build_unsafe(db, user_id, node_id, session)
        except Exception as e:
            logger.error("MemoryContextBuilder.build failed: %s", e)
            idx = session.current_concept_index
            total = len(session.what_list)
            d = session.difficulty_level
            return f"[Memory Context]\n暂无历史记忆。当前进度 {idx + 1}/{total}；当前难度 {d}/5。"

    def _build_unsafe(self, db: DbSession, user_id: str, node_id: str, session: SessionState) -> str:
        lt = repo.get_long_term(db, user_id)
        episodic_list = repo.get_recent_episodic_for_node(db, user_id, node_id, limit=1)
        procedural = repo.get_procedural_patterns(db, user_id, min_confidence=0.6)[:3]

        # Long-term line
        if lt:
            style = lt.learning_style or {}
            style_summary = "、".join(f"{k}={v}" for k, v in style.items()) if style else "无偏好记录"
            recent_mastered = lt.mastered_concepts[-5:] if lt.mastered_concepts else []
            mastered_str = "、".join(c.get("concept", "") for c in recent_mastered) if recent_mastered else "无"
        else:
            style_summary = "无偏好记录"
            mastered_str = "无"
        lt_line = f"长期记忆：{style_summary}。已掌握跨节点概念：{mastered_str}。"

        # Episodic line
        if episodic_list:
            ep = episodic_list[0]
            ep_summary = ep.summary if ep.summary else "（无摘要）"
            ep_line = f"情节记忆：{ep_summary}"
        else:
            ep_line = "情节记忆：首次学习此节点"

        # Procedural line
        if procedural:
            proc_parts = [f"{p.pattern_key}={p.pattern_value}" for p in procedural]
            proc_line = f"程序记忆：{'；'.join(proc_parts)}。"
        else:
            proc_line = "程序记忆：无。"

        # Current state line
        idx = session.current_concept_index
        total = len(session.what_list)
        weak_str = "、".join(session.weak_points) if session.weak_points else "无"
        state_line = f"当前状态：本次进度 {idx + 1}/{total}；已识别弱点：{weak_str}；难度 {session.difficulty_level}/5。"

        full = "\n".join(["[Memory Context]", lt_line, ep_line, proc_line, state_line])

        if len(full) <= self.MAX_LENGTH:
            return full

        # Over budget — drop procedural line first
        without_proc = "\n".join(["[Memory Context]", lt_line, ep_line, state_line])
        if len(without_proc) <= self.MAX_LENGTH:
            return without_proc

        # Still over — truncate mastered list
        short_lt = f"长期记忆：{style_summary}。已掌握跨节点概念：（省略）。"
        minimal = "\n".join(["[Memory Context]", short_lt, ep_line, state_line])
        return minimal[: self.MAX_LENGTH]
