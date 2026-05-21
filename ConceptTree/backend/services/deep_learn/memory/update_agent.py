"""MemoryUpdateAgent — LLM-powered session summarization and procedural aggregation."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from models_memory import EpisodicRecord, ProceduralPattern, VALID_PROCEDURAL_KEYS
from services.llm.client import get_llm_client

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../../llm/configs/deep_learn_memory_update.json")
)

_VALID_VALUES: dict[str, Optional[set[str]]] = {
    "effective_analogy_type": {"code", "math", "daily", "visual"},
    "optimal_question_density": {"1", "2", "3"},
    "preferred_explanation_order": {"concrete_first", "abstract_first"},
    "common_misconception_pattern": None,  # free text
    "ideal_pace": {"slow", "normal", "fast"},
}


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class MemoryUpdateAgent:
    def __init__(self) -> None:
        self._config: Optional[dict] = None

    def _get_config(self) -> dict:
        if self._config is None:
            self._config = _load_config()
        return self._config

    async def summarize(
        self,
        *,
        session_data: dict,
        concepts_covered: list[str],
        test_results: list[dict],
    ) -> str:
        try:
            cfg = self._get_config()
            system = cfg["system_prompt"]
            params = cfg.get("model_params", {})
            user = (
                "【场景 A · summarize】\n"
                f"concepts_covered: {concepts_covered}\n"
                f"test_results: {json.dumps(test_results, ensure_ascii=False)}\n"
                f"session_data: {json.dumps(session_data, ensure_ascii=False)}"
            )
            raw = await get_llm_client().chat_json(
                system, user,
                temperature=params.get("temperature", 0.4),
                max_tokens=params.get("max_tokens", 1200),
            )
            return raw.get("summary", "（自动摘要生成失败，请人工查看 conversation_history）")
        except Exception as e:
            logger.error("MemoryUpdateAgent.summarize failed: %s", e)
            return "（自动摘要生成失败，请人工查看 conversation_history）"

    async def aggregate_procedural(
        self, *, recent_records: list[EpisodicRecord]
    ) -> list[ProceduralPattern]:
        try:
            cfg = self._get_config()
            system = cfg["system_prompt"]
            params = cfg.get("model_params", {})
            summaries = [f"- session {i+1}: {r.summary}" for i, r in enumerate(recent_records)]
            user = "【场景 B · aggregate_procedural】\n最近 session 摘要：\n" + "\n".join(summaries)
            raw = await get_llm_client().chat_json(
                system, user,
                temperature=params.get("temperature", 0.4),
                max_tokens=params.get("max_tokens", 1200),
            )
            patterns_raw = raw.get("patterns", [])
            now = datetime.now(timezone.utc).isoformat()
            result: list[ProceduralPattern] = []
            seen_keys: set[str] = set()
            for item in patterns_raw:
                key = item.get("key", "")
                value = str(item.get("value", ""))
                confidence = float(item.get("confidence", 0.5))
                if key not in VALID_PROCEDURAL_KEYS:
                    logger.warning("aggregate_procedural: unknown key '%s', skipping", key)
                    continue
                if key in seen_keys:
                    continue
                allowed = _VALID_VALUES.get(key)
                if allowed is not None and value not in allowed:
                    logger.warning("aggregate_procedural: invalid value '%s' for key '%s', skipping", value, key)
                    continue
                seen_keys.add(key)
                result.append(ProceduralPattern(
                    user_id="",  # caller fills
                    pattern_key=key,
                    pattern_value=value,
                    confidence=max(0.0, min(1.0, confidence)),
                    sample_count=1,  # caller uses upsert which increments
                    updated_at=now,
                ))
            return result
        except Exception as e:
            logger.error("MemoryUpdateAgent.aggregate_procedural failed: %s", e)
            return []
