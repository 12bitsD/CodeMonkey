"""ImageTriggerAgent — decides whether a teaching chunk needs an image."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from models_memory import ImageTriggerOutput
from services.llm.client import get_llm_client

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../llm/configs/deep_learn_image_trigger.json")
)


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class ImageTriggerAgent:
    def __init__(self) -> None:
        self._config: Optional[dict] = None

    def _get_config(self) -> dict:
        if self._config is None:
            self._config = _load_config()
        return self._config

    async def decide(
        self,
        *,
        teaching_content: str,
        concept: str,
        node_name: str,
        previous_image_count: int = 0,
    ) -> ImageTriggerOutput:
        if previous_image_count >= 5:
            return ImageTriggerOutput(needs_image=False, reason="suppressed: image count >= 5")

        try:
            cfg = self._get_config()
            system = cfg["system_prompt"]
            params = cfg.get("model_params", {})
            user = (
                f"[节点] {node_name}\n"
                f"[概念] {concept}\n"
                f"[本 session 已生图次数] {previous_image_count}\n"
                f"[刚讲完的内容]\n{teaching_content}\n\n"
                "请决策是否需要图，按系统 prompt 规则输出 JSON。"
            )
            raw = await get_llm_client().chat_json(
                system, user,
                temperature=params.get("temperature", 0.3),
                max_tokens=params.get("max_tokens", 600),
            )
            return ImageTriggerOutput(
                needs_image=bool(raw.get("needs_image", False)),
                image_type=raw.get("image_type"),
                mermaid_code=raw.get("mermaid_code"),
                dalle_prompt=raw.get("dalle_prompt"),
                reason=raw.get("reason", ""),
            )
        except Exception as e:
            logger.error("ImageTriggerAgent.decide failed: %s", e)
            return ImageTriggerOutput(needs_image=False, reason=f"error: {e}")
