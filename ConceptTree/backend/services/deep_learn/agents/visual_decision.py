"""Decide whether a teaching turn needs a diagram or an optional illustration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from models_memory import VisualDecision
from services.llm.client import get_llm_client
from services.llm.language import apply_response_language

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "llm" / "configs" / "deep_learn_visual_decision.json"


class VisualDecisionAgent:
    def __init__(self) -> None:
        self._config: Optional[dict] = None

    def _get_config(self) -> dict:
        if self._config is None:
            self._config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return self._config

    async def decide(
        self,
        *,
        teaching_content: str,
        concept: str,
        node_name: str,
        language: str,
    ) -> VisualDecision:
        try:
            config = self._get_config()
            system = apply_response_language(config["system_prompt"], language, json_mode=True)
            params = config.get("model_params", {})
            user = (
                f"[response_language] {language}\n"
                f"[node] {node_name}\n"
                f"[concept] {concept}\n"
                f"[teaching_content]\n{teaching_content}\n\n"
                "Return the visual decision JSON now."
            )
            raw = await get_llm_client().chat_json(
                system,
                user,
                temperature=params.get("temperature", 0.2),
                max_tokens=params.get("max_tokens", 1400),
            )
            return VisualDecision(**raw)
        except Exception as error:
            logger.warning("VisualDecisionAgent.decide failed: %s", error)
            reason = f"visual decision failed: {error}"[:240]
            return VisualDecision(visual_type="none", reason=reason)

