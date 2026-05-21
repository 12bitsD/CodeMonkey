from __future__ import annotations

import json
import logging
import os
from typing import AsyncGenerator, Optional

from models_deep_learn import TeachingMode, TeachingOutput
from services.llm.client import get_llm_client
from services.llm.providers import LLMMessage

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../llm/configs/deep_learn_teaching.json")


def _load_system_prompt() -> str:
    with open(os.path.normpath(_CONFIG_PATH), "r", encoding="utf-8") as f:
        return json.load(f)["system_prompt"]


_MODE_INSTRUCTIONS: dict[str, str] = {
    "normal": "按标准节奏讲解当前概念，然后出 3 道题。",
    "expand": "对当前概念进行更深入展开，补充细节和边界情况，然后出 3 道更深的题。",
    "reteach": "换一个全新的角度或类比重新讲解当前概念，不要重复之前的表述。",
    "probe_stuck": "用户连续答错。不要继续给答案。只问一个澄清问题（你在哪一步卡住？），questions 字段返回空数组。",
    "review_weak": "用户还没准备好测试。重点复习弱点概念，出题侧重弱点。",
}


def _format_recent_turns(turns: list[dict]) -> str:
    if not turns:
        return "（无）"
    lines = []
    for t in turns:
        role = "用户" if t.get("role") == "user" else "AI"
        content = t.get("content", "")
        if t.get("kind") == "questions" and isinstance(content, list):
            content = "；".join(str(item) for item in content)
        lines.append(f"{role}：{content}")
    return "\n".join(lines)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _decode_json_escape(sequence: str) -> str:
    mapping = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    if sequence.startswith("u") and len(sequence) == 5:
        try:
            return chr(int(sequence[1:], 16))
        except ValueError:
            return ""
    return mapping.get(sequence, sequence)


def _extract_json_string_value(buffer: str, key: str) -> tuple[str, bool]:
    marker = f'"{key}"'
    start = buffer.find(marker)
    if start < 0:
        return "", False
    colon = buffer.find(":", start + len(marker))
    if colon < 0:
        return "", False
    pos = colon + 1
    while pos < len(buffer) and buffer[pos].isspace():
        pos += 1
    if pos >= len(buffer) or buffer[pos] != '"':
        return "", False

    pos += 1
    chars: list[str] = []
    while pos < len(buffer):
        char = buffer[pos]
        if char == '"':
            return "".join(chars), True
        if char == "\\":
            if pos + 1 >= len(buffer):
                break
            escape = buffer[pos + 1]
            if escape == "u":
                if pos + 6 > len(buffer):
                    break
                chars.append(_decode_json_escape(buffer[pos + 1:pos + 6]))
                pos += 6
                continue
            chars.append(_decode_json_escape(escape))
            pos += 2
            continue
        chars.append(char)
        pos += 1
    return "".join(chars), False


class TeachingAgent:
    def __init__(self) -> None:
        self._system_prompt: Optional[str] = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = _load_system_prompt()
        return self._system_prompt

    def _build_prompts(
        self, *,
        node_name: str,
        node_why: str,
        current_concept: str,
        concept_index: int,
        total_concepts: int,
        difficulty_level: int,
        weak_points: list[str],
        recent_turns: list[dict],
        mode: TeachingMode,
        memory_context: str = "",
    ) -> tuple[str, str]:
        system_prompt = self._get_system_prompt()

        mode_instr = _MODE_INSTRUCTIONS.get(mode, _MODE_INSTRUCTIONS["normal"])
        if mode == "review_weak":
            weak_str = "、".join(weak_points) if weak_points else "无"
            mode_instr = f"用户还没准备好测试。重点复习以下弱点：{weak_str}。出题侧重弱点。"

        memory_block = f"{memory_context}\n\n" if memory_context else ""
        user_prompt = (
            f"[节点] {node_name}\n"
            f"[学习目的] {node_why}\n"
            f"[当前概念] {current_concept}（第 {concept_index + 1} 个，共 {total_concepts} 个）\n"
            f"[当前难度] {difficulty_level}/5\n"
            f"[已识别弱点] {', '.join(weak_points) or '无'}\n"
            f"{memory_block}"
            f"[最近对话]\n{_format_recent_turns(recent_turns[-8:])}\n\n"
            f"[本次模式] {mode_instr}"
        )
        return system_prompt, user_prompt

    async def run(
        self, *,
        node_name: str,
        node_why: str,
        current_concept: str,
        concept_index: int,
        total_concepts: int,
        difficulty_level: int,
        weak_points: list[str],
        recent_turns: list[dict],
        mode: TeachingMode,
        memory_context: str = "",
    ) -> TeachingOutput:
        system_prompt, user_prompt = self._build_prompts(
            node_name=node_name,
            node_why=node_why,
            current_concept=current_concept,
            concept_index=concept_index,
            total_concepts=total_concepts,
            difficulty_level=difficulty_level,
            weak_points=weak_points,
            recent_turns=recent_turns,
            mode=mode,
            memory_context=memory_context,
        )

        for attempt in range(2):
            try:
                raw = await get_llm_client().chat_json(
                    system_prompt, user_prompt, temperature=0.6, max_tokens=2048
                )
                output = TeachingOutput(**raw)
                if not output.content:
                    raise ValueError("content is empty")
                return output
            except Exception as e:
                if attempt == 0:
                    logger.warning("TeachingAgent attempt 1 failed: %s — retrying", e)
                else:
                    logger.error("TeachingAgent failed after 2 attempts: %s", e)

        return TeachingOutput(
            content="抱歉，AI 生成内容时遇到问题，请稍后重试。",
            questions=[],
        )

    async def stream_run(self, **kwargs) -> AsyncGenerator[dict, None]:
        system_prompt, user_prompt = self._build_prompts(**kwargs)
        buffer = ""
        emitted_content = ""

        try:
            async for chunk in get_llm_client().chat_stream(
                [
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                temperature=0.6,
                max_tokens=2048,
            ):
                buffer += chunk
                partial_content, _complete = _extract_json_string_value(buffer, "content")
                if len(partial_content) > len(emitted_content):
                    delta = partial_content[len(emitted_content):]
                    emitted_content = partial_content
                    if delta:
                        yield {"type": "content", "text": delta}

            raw = json.loads(_strip_json_fence(buffer))
            output = TeachingOutput(**raw)
            if not output.content:
                raise ValueError("content is empty")

            if len(output.content) > len(emitted_content):
                yield {"type": "content", "text": output.content[len(emitted_content):]}

            yield {"type": "done", "output": output}
        except Exception as e:
            logger.warning("TeachingAgent.stream_run failed, falling back to non-stream JSON: %s", e)
            output = await self.run(**kwargs)
            if not emitted_content and output.content:
                yield {"type": "content", "text": output.content}
            yield {"type": "done", "output": output}
