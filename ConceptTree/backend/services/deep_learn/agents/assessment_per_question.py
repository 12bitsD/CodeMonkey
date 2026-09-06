from __future__ import annotations

import json
import logging
import os
import re
from difflib import SequenceMatcher

from models_deep_learn import AssessmentPerQuestionOutput
from services.llm.client import get_llm_client
from services.llm.language import apply_response_language

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../llm/configs/deep_learn_assessment_per_question.json",
)


def _load_system_prompt() -> str:
    with open(os.path.normpath(_CONFIG_PATH), "r", encoding="utf-8") as f:
        return json.load(f)["system_prompt"]


def _normalize_for_similarity(value: str) -> str:
    return re.sub(r"[\W_]+", "", value or "", flags=re.UNICODE).lower()


def _looks_like_question_copy(question: str, answer: str) -> bool:
    q = _normalize_for_similarity(question)
    a = _normalize_for_similarity(answer)
    if len(q) < 16 or len(a) < 16:
        return False
    if q in a and len(a) <= int(len(q) * 1.35):
        return True
    return SequenceMatcher(None, q, a).ratio() >= 0.82


def _looks_too_thin(answer: str) -> bool:
    normalized = _normalize_for_similarity(answer)
    return len(normalized) < 24


class AssessmentPerQuestionAgent:
    def __init__(self) -> None:
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = _load_system_prompt()
        return self._system_prompt

    async def run(
        self, *,
        concept: str,
        question: str,
        user_answer: str,
        prev_wrong_count: int,
        weak_points: list[str],
        language: str = "zh-CN",
    ) -> AssessmentPerQuestionOutput:
        system_prompt = apply_response_language(
            self._get_system_prompt(),
            language,
            json_mode=True,
        )
        is_chinese = language == "zh-CN"
        if _looks_too_thin(user_answer):
            return AssessmentPerQuestionOutput(
                is_correct=False,
                quality_score=0.0,
                explanation="回答太短，还看不出完整理解。" if is_chinese else "The answer is too short to demonstrate a complete understanding.",
                feedback="请补充核心机制、你的判断依据，以及一个具体例子或推理过程。" if is_chinese else "Add the core mechanism, the basis for your judgment, and one concrete example or reasoning path.",
                update_weak_points=["回答缺少推理证据" if is_chinese else "Answer lacks supporting reasoning"],
                difficulty_delta=0,
                wrong_count=prev_wrong_count + 1,
            )
        if _looks_like_question_copy(question, user_answer):
            return AssessmentPerQuestionOutput(
                is_correct=False,
                quality_score=0.0,
                explanation="这更像是在复述题目，还不能证明你已经理解。" if is_chinese else "This mostly repeats the question and does not yet demonstrate understanding.",
                feedback="请用自己的话回答：给出核心原理、关键判断依据，并补一个具体例子或推理过程。" if is_chinese else "Answer in your own words: state the core principle, explain the deciding evidence, and add one concrete example or reasoning path.",
                update_weak_points=["机械复述题目" if is_chinese else "Repeated the question mechanically"],
                difficulty_delta=0,
                wrong_count=prev_wrong_count + 1,
            )
        user_prompt = (
            f"[概念] {concept}\n"
            f"[题目] {question}\n"
            f"[用户回答] {user_answer}\n"
            f"[当前累计错误次数] {prev_wrong_count}\n"
            f"[已记录弱点] {weak_points}"
        )

        try:
            raw = await get_llm_client().chat_json(
                system_prompt, user_prompt, temperature=0.3, max_tokens=800
            )
            output = AssessmentPerQuestionOutput(**raw)
            output.quality_score = max(0.0, min(1.0, output.quality_score))
            if output.is_correct and output.quality_score < 0.65:
                output.is_correct = False
                output.wrong_count = prev_wrong_count + 1
            if output.difficulty_delta not in (-1, 0, 1):
                output.difficulty_delta = 0
            return output
        except Exception as e:
            logger.error("AssessmentPerQuestionAgent failed: %s", e)
            return AssessmentPerQuestionOutput(
                is_correct=False,
                quality_score=0.0,
                explanation="评估暂不可用" if is_chinese else "Assessment is temporarily unavailable.",
                feedback="",
                wrong_count=prev_wrong_count + 1,
            )
