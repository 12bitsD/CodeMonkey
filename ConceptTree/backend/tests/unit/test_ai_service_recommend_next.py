"""AIService.recommend_next unit tests — canonical unit-test directory version.

This is the unit-test directory's version of the recommend-next service tests.
It is functionally equivalent to ``tests/test_ai_recommend_next.py`` but lives
in ``tests/unit/`` to be grouped with other pure unit tests that run without a
database. All LLM interactions are mocked via ``unittest.mock``.

This module validates four key scenarios:
1. Happy path: the LLM returns a node ID and reason; the service returns a
   typed RecommendNextAIResult with success=True and the expected data.
2. All complete: the LLM returns null node ID (learner is done); the service
   returns success=True with recommended_node_id=None.
3. LLM failure: an exception from the LLM client is translated into a
   structured error result with code 'AI_SERVICE_ERROR'.
4. Prompt construction: graph node names and the learning goal appear in the
   user prompt sent to the LLM.

Primary reader: a developer working on the recommend-next feature in the
unit-test context, or verifying that prompt construction is correct.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai_service import AIService
from models import RecommendNextAIResult


GRAPH_FIXTURE = {
    "nodes": [
        {"id": "n1", "name": "矩阵乘法", "status": "learned"},
        {"id": "n2", "name": "链式法则", "status": "unlearned"},
        {"id": "n3", "name": "反向传播", "status": "unlearned", "isTarget": True},
    ],
    "edges": [
        {"from_node": "n1", "to_node": "n2"},
        {"from_node": "n2", "to_node": "n3"},
    ],
    "target_node_id": "n3",
}

PROFILE_FIXTURE = {
    "occupation": "大三学生",
    "math_level": "入门",
    "abilities": ["Python基础"],
}

HISTORY_FIXTURE = {
    "last_node": "矩阵乘法",
    "learned_nodes": ["n1"],
    "skipped_nodes": [],
}


class TestAIServiceRecommendNext:
    @pytest.mark.asyncio
    async def test_returns_recommendation_with_reason(self):
        """The service returns a typed RecommendNextAIResult with the mocked node ID.

        When the LLM responds with a node ID and explanation, the service must
        parse the response into a ``RecommendNextAIResult`` with success=True.
        Expected: isinstance(result, RecommendNextAIResult), success=True,
        recommended_node_id='n2', len(reason) > 0.
        """
        mock_result = {
            "recommended_node_id": "n2",
            "reason": "链式法则的前置知识矩阵乘法已掌握，是通往目标的关键路径",
        }

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(return_value=mock_result)
            mock_get_client.return_value = mock_client

            service = AIService()
            result = await service.recommend_next(
                graph=GRAPH_FIXTURE,
                user_profile=PROFILE_FIXTURE,
                learning_history=HISTORY_FIXTURE,
                learning_goal="理解反向传播",
            )

        assert isinstance(result, RecommendNextAIResult)
        assert result.success is True
        assert result.data.recommended_node_id == "n2"
        assert len(result.data.reason) > 0

    @pytest.mark.asyncio
    async def test_returns_null_node_id_when_all_complete(self):
        """The service returns success=True with recommended_node_id=None when done.

        When the LLM signals completion (null node ID), the service must treat
        this as a successful result, not an error.
        Expected: success=True, recommended_node_id is None.
        """
        mock_result = {
            "recommended_node_id": None,
            "reason": "所有知识点已完成，学习目标达成",
        }

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(return_value=mock_result)
            mock_get_client.return_value = mock_client

            service = AIService()
            result = await service.recommend_next(
                graph={
                    **GRAPH_FIXTURE,
                    "nodes": [{"id": "n1", "name": "矩阵乘法", "status": "learned"}],
                },
                user_profile=PROFILE_FIXTURE,
                learning_history={**HISTORY_FIXTURE, "learned_nodes": ["n1"]},
                learning_goal="理解反向传播",
            )

        assert result.success is True
        assert result.data.recommended_node_id is None

    @pytest.mark.asyncio
    async def test_returns_error_on_llm_failure(self):
        """An LLM exception is caught and returned as an error result.

        The service must never raise an unhandled exception; LLM errors should
        be translated into a structured failure result with code 'AI_SERVICE_ERROR'.
        Expected: success=False, error.code='AI_SERVICE_ERROR'.
        """
        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(side_effect=Exception("LLM timeout"))
            mock_get_client.return_value = mock_client

            service = AIService()
            result = await service.recommend_next(
                graph=GRAPH_FIXTURE,
                user_profile=PROFILE_FIXTURE,
                learning_history=HISTORY_FIXTURE,
                learning_goal="理解反向传播",
            )

        assert result.success is False
        assert result.error.code == "AI_SERVICE_ERROR"

    @pytest.mark.asyncio
    async def test_passes_graph_context_to_llm(self):
        """Graph node names and the learning goal appear in the LLM user prompt.

        Captures the raw prompt to verify that key context strings (node names
        from the graph fixture and the learning goal) are included in the
        user prompt sent to the LLM.
        Expected: '矩阵乘法' and '理解反向传播' in captured user prompt.
        """
        captured = {}

        async def capture(system_prompt, user_prompt, **kwargs):
            captured["user"] = user_prompt
            return {"recommended_node_id": "n2", "reason": "test"}

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = capture
            mock_get_client.return_value = mock_client

            service = AIService()
            await service.recommend_next(
                graph=GRAPH_FIXTURE,
                user_profile=PROFILE_FIXTURE,
                learning_history=HISTORY_FIXTURE,
                learning_goal="理解反向传播",
            )

        assert "矩阵乘法" in captured["user"]
        assert "理解反向传播" in captured["user"]
