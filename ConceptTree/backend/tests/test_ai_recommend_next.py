"""AIService.recommend_next unit tests: validates the 'next node to learn' LLM feature.

The recommend-next feature uses an LLM to analyse the current learning graph
and suggest the most appropriate next concept node for the learner. Because
the LLM is an external dependency, all tests in this module use mocks
(``@pytest.mark.no_db`` — no database required either).

This module validates four key scenarios:
1. Happy path: the LLM returns a node ID and reason; the service returns a
   typed RecommendNextAIResult with success=True.
2. All complete: the LLM returns null node ID (nothing left to learn); the
   service returns success=True with recommended_node_id=None.
3. LLM failure: an exception from the LLM client is caught and surfaced as
   an error result with code 'AI_SERVICE_ERROR'.
4. Prompt construction: graph node names and the learning goal are included
   in the LLM prompt (confirming context is passed correctly).

Primary reader: a developer extending or debugging the recommend-next feature,
or verifying that LLM errors are handled gracefully.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai_service import AIService
from models import RecommendNextAIResult

pytestmark = pytest.mark.no_db


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
        """The service returns a typed result with the recommended node ID and a non-empty reason.

        When the LLM responds with a node ID and explanation, the service must
        parse the response into a ``RecommendNextAIResult`` with success=True and
        the expected recommended_node_id.
        Expected: result is RecommendNextAIResult, success=True,
        recommended_node_id='n2', reason is non-empty.
        """
        mock_llm_result = {
            "recommended_node_id": "n2",
            "reason": "链式法则的前置知识矩阵乘法已掌握，是通往目标的关键路径",
        }

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(return_value=mock_llm_result)
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
        """The service returns success=True with recommended_node_id=None when all nodes are done.

        When the LLM signals that the learner has completed all nodes (by
        returning null for recommended_node_id), the service must surface this
        as a successful result — not an error.
        Expected: success=True, recommended_node_id is None.
        """
        mock_llm_result = {
            "recommended_node_id": None,
            "reason": "所有知识点已完成，学习目标达成",
        }

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(return_value=mock_llm_result)
            mock_get_client.return_value = mock_client

            service = AIService()
            result = await service.recommend_next(
                graph={
                    **GRAPH_FIXTURE,
                    "nodes": [
                        {"id": "n1", "name": "矩阵乘法", "status": "learned"},
                    ],
                },
                user_profile=PROFILE_FIXTURE,
                learning_history={**HISTORY_FIXTURE, "learned_nodes": ["n1"]},
                learning_goal="理解反向传播",
            )

        assert result.success is True
        assert result.data.recommended_node_id is None

    @pytest.mark.asyncio
    async def test_returns_error_on_llm_failure(self):
        """An exception from the LLM client is caught and returned as an error result.

        The service must never raise an unhandled exception; LLM errors should
        be translated into a structured failure result with error code
        'AI_SERVICE_ERROR'.
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
        assert result.error is not None
        assert result.error.code == "AI_SERVICE_ERROR"

    @pytest.mark.asyncio
    async def test_passes_graph_context_to_llm(self):
        """The LLM prompt includes graph node names and the learning goal.

        This test captures the raw prompt passed to the LLM client and
        asserts that key context (node names from the graph and the learning
        goal string) appears in the user prompt — confirming the service
        correctly serialises graph context for the LLM.
        Expected: '矩阵乘法' and '理解反向传播' appear in the captured user prompt.
        """
        captured_prompt = {}

        async def capture_call(system_prompt, user_prompt, **kwargs):
            captured_prompt["system"] = system_prompt
            captured_prompt["user"] = user_prompt
            return {"recommended_node_id": "n2", "reason": "test"}

        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = capture_call
            mock_get_client.return_value = mock_client

            service = AIService()
            await service.recommend_next(
                graph=GRAPH_FIXTURE,
                user_profile=PROFILE_FIXTURE,
                learning_history=HISTORY_FIXTURE,
                learning_goal="理解反向传播",
            )

        assert "矩阵乘法" in captured_prompt["user"]
        assert "理解反向传播" in captured_prompt["user"]
