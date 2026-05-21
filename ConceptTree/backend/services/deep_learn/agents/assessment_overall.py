from __future__ import annotations

import json
import logging
import os

from models_deep_learn import AssessmentOverallOutput
from services.llm.client import get_llm_client

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../llm/configs/deep_learn_assessment_overall.json",
)


def _load_system_prompt() -> str:
    with open(os.path.normpath(_CONFIG_PATH), "r", encoding="utf-8") as f:
        return json.load(f)["system_prompt"]


_FALLBACK = AssessmentOverallOutput(
    passed=False, confidence=0.0, ready_for_test=False, reason="评估服务暂不可用"
)


class AssessmentOverallAgent:
    def __init__(self) -> None:
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = _load_system_prompt()
        return self._system_prompt

    async def run_readiness(
        self, *,
        node_name: str,
        concepts_done: list[str],
        concepts_skipped: list[str],
        weak_points: list[str],
    ) -> AssessmentOverallOutput:
        system_prompt = self._get_system_prompt()
        user_prompt = (
            f"[场景标识] A（readiness — 判断是否准备好测试）\n"
            f"[节点] {node_name}\n"
            f"[已完成概念] {concepts_done}\n"
            f"[已跳过概念] {concepts_skipped}\n"
            f"[已记录弱点] {weak_points}\n"
            "请判断用户是否准备好进行综合测试，填写 ready_for_test 字段。"
        )
        try:
            raw = await get_llm_client().chat_json(
                system_prompt, user_prompt, temperature=0.3, max_tokens=1024
            )
            return AssessmentOverallOutput(**raw)
        except Exception as e:
            logger.error("AssessmentOverallAgent.run_readiness failed: %s", e)
            return _FALLBACK

    async def run_final_judge(
        self, *,
        node_name: str,
        test_qa_pairs: list[dict],
        weak_points: list[str],
    ) -> AssessmentOverallOutput:
        system_prompt = self._get_system_prompt()
        user_prompt = (
            f"[场景标识] B（test — 判断综合测试是否通过）\n"
            f"[节点] {node_name}\n"
            f"[测试问答记录] {json.dumps(test_qa_pairs, ensure_ascii=False)}\n"
            f"[已记录弱点] {weak_points}\n"
            "请判断用户是否真正掌握该节点，填写 passed 字段；ready_for_test 直接等于 passed。"
        )
        try:
            raw = await get_llm_client().chat_json(
                system_prompt, user_prompt, temperature=0.3, max_tokens=1024
            )
            return AssessmentOverallOutput(**raw)
        except Exception as e:
            logger.error("AssessmentOverallAgent.run_final_judge failed: %s", e)
            return _FALLBACK
