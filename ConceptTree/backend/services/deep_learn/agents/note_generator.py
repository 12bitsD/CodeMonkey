from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from models_deep_learn import NoteGeneratorOutput, SessionState
from services.llm.client import get_llm_client
from services.llm.language import apply_response_language
from services.llm.providers import LLMMessage

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "llm" / "configs" / "deep_learn_note_gen.json"
_MAX_TURNS_FOR_NOTE = 20  # cap recent_turns to avoid exceeding token budget


def _load_system_prompt(node_name: str, node_why: str) -> tuple[dict, str]:
    """Load config and render system_prompt placeholders. Returns (model_params, system_prompt)."""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    model_params = config.get("model_params", {})
    sys_prompt = config.get("system_prompt", "")
    sys_prompt = sys_prompt.replace("{{node_name}}", node_name)
    sys_prompt = sys_prompt.replace("{{node_why}}", node_why or "深入理解该知识点")
    return model_params, sys_prompt


def _summarize_turns(recent_turns: list[dict], max_turns: int = _MAX_TURNS_FOR_NOTE) -> str:
    """Convert recent_turns to a compact text summary for the note generator prompt."""
    if not recent_turns:
        return "（无对话记录）"
    capped = recent_turns[-max_turns:]
    lines: list[str] = []
    for turn in capped:
        role = turn.get("role", "unknown")
        kind = turn.get("kind", "text")
        content = turn.get("content", "")
        if kind in ("mermaid", "dalle_image", "dalle_pending"):
            continue  # skip image turns
        if isinstance(content, list):
            content = " / ".join(str(c) for c in content)
        prefix = "AI" if role == "assistant" else "用户"
        lines.append(f"{prefix}: {str(content)[:200]}")
    return "\n".join(lines) or "（无文字对话记录）"


class NoteGeneratorAgent:
    def __init__(self) -> None:
        self.llm_client = get_llm_client()

    async def generate(
        self,
        *,
        session: SessionState,
        node_name: str,
        node_why: str,
        language: str = "zh-CN",
    ) -> NoteGeneratorOutput:
        concepts_covered = [
            session.what_list[i]
            for i in range(len(session.what_list))
            if session.concepts_status.get(str(i)) in ("done", "skipped")
        ]

        turns_summary = _summarize_turns(session.recent_turns)

        user_prompt = (
            f"本次学习覆盖的概念：{', '.join(concepts_covered) or '（无记录）'}\n"
            f"弱点记录：{', '.join(session.weak_points) or '（无）'}\n"
            f"对话摘要：\n{turns_summary}"
        )

        model_params, sys_prompt = _load_system_prompt(node_name, node_why)
        sys_prompt = apply_response_language(sys_prompt, language)

        messages = [
            LLMMessage(role="system", content=sys_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_client.chat(
            messages=messages,
            temperature=model_params.get("temperature", 0.7),
            max_tokens=model_params.get("max_tokens", 2000),
        )

        content = response.content.strip() if response.content else ""
        if not content:
            content = (
                f"# {node_name} 学习笔记\n\n本次深度学习已完成。\n\n覆盖概念：{', '.join(concepts_covered)}"
                if language == "zh-CN"
                else f"# {node_name} Learning Notes\n\nThis Deep Learn session is complete.\n\nConcepts covered: {', '.join(concepts_covered)}"
            )

        return NoteGeneratorOutput(content=content)
