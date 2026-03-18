import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai_service import AIService

pytestmark = pytest.mark.no_db

EXISTING_NODES = [
    {"id": "n1", "name": "矩阵乘法", "status": "learned"},
    {"id": "n2", "name": "链式法则", "status": "unlearned"},
    {"id": "n3", "name": "反向传播", "status": "unlearned"},
]

MOCK_RESULT = {
    "interpretation": "用Python实现反向传播",
    "isLargeChange": False,
    "suggestion": "modify",
    "reason": "目标更具体",
    "changes": {"keep": ["n1", "n2"], "remove": ["n3"], "add": ["Python实现基础"]},
}


class TestClarifyGoalWithNodes:
    @pytest.mark.asyncio
    async def test_includes_node_ids_in_llm_prompt(self):
        captured = {}

        async def capture(system_prompt, user_prompt, **kwargs):
            captured["user"] = user_prompt
            return MOCK_RESULT

        with patch("services.ai_service.get_llm_client") as mock:
            mock.return_value = MagicMock(chat_json=capture)
            service = AIService()
            result = await service.clarify_goal(
                original_goal="学Python",
                new_goal="学Python数据分析",
                existing_nodes=EXISTING_NODES,
            )

        assert "n1" in captured["user"]
        assert "矩阵乘法" in captured["user"]
        assert "n3" in captured["user"]
        assert result.success is True
        assert result.data.changes.keep == ["n1", "n2"]
        assert result.data.changes.remove == ["n3"]
        assert result.data.changes.add == ["Python实现基础"]

    @pytest.mark.asyncio
    async def test_works_without_existing_nodes(self):
        with patch("services.ai_service.get_llm_client") as mock:
            mock.return_value = MagicMock(
                chat_json=AsyncMock(
                    return_value={
                        "interpretation": "全新目标",
                        "isLargeChange": True,
                        "suggestion": "create_new",
                        "reason": "完全不同",
                        "changes": {"keep": [], "remove": [], "add": []},
                    }
                )
            )
            service = AIService()
            result = await service.clarify_goal(
                "学Python", "学Java", existing_nodes=None
            )

        assert result.success is True
        assert result.data.changes.keep == []

    @pytest.mark.asyncio
    async def test_returns_error_on_llm_failure(self):
        with patch("services.ai_service.get_llm_client") as mock:
            mock.return_value = MagicMock(
                chat_json=AsyncMock(side_effect=Exception("LLM timeout"))
            )
            service = AIService()
            result = await service.clarify_goal("a", "b", existing_nodes=EXISTING_NODES)

        assert result.success is False
        assert result.error.code == "AI_SERVICE_ERROR"
