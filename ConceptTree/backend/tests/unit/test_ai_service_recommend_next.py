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
        assert result.data.recommendedNodeId == "n2"
        assert len(result.data.reason) > 0

    @pytest.mark.asyncio
    async def test_returns_null_node_id_when_all_complete(self):
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
        assert result.data.recommendedNodeId is None

    @pytest.mark.asyncio
    async def test_returns_error_on_llm_failure(self):
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
