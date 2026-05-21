import pytest

from services.deep_learn.agents.assessment_per_question import AssessmentPerQuestionAgent


@pytest.mark.asyncio
async def test_assessment_rejects_copied_question_without_llm(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM should not be called for copied questions")

    monkeypatch.setattr("services.llm.client.UnifiedLLMClient.chat_json", fail_if_called, raising=False)

    agent = AssessmentPerQuestionAgent()
    question = "解释动量法的一阶动量公式如何通过指数移动平均来实现平滑更新？"
    result = await agent.run(
        concept="动量法",
        question=question,
        user_answer=question,
        prev_wrong_count=0,
        weak_points=[],
    )

    assert result.is_correct is False
    assert result.wrong_count == 1
    assert "机械复述题目" in result.update_weak_points


@pytest.mark.asyncio
async def test_assessment_rejects_too_short_answer_without_llm(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM should not be called for thin answers")

    monkeypatch.setattr("services.llm.client.UnifiedLLMClient.chat_json", fail_if_called, raising=False)

    agent = AssessmentPerQuestionAgent()
    result = await agent.run(
        concept="动量法",
        question="请解释动量法为什么能缓解梯度方向震荡。",
        user_answer="能加速收敛。",
        prev_wrong_count=1,
        weak_points=[],
    )

    assert result.is_correct is False
    assert result.wrong_count == 2
    assert "回答缺少推理证据" in result.update_weak_points
