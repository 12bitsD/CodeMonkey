"""AIService.clarify_goal unit tests with existing node context.

When the clarify-goal API is called with a planId, the router fetches the plan's
current nodes and passes them to AIService.clarify_goal as 'existing_nodes'. This
module tests that the service correctly integrates those nodes into the LLM prompt
and parses the response into typed GraphChanges.

All tests mock the LLM client to avoid real API calls.
Tests are marked no_db so no database setup is required.

This module validates:
1. Node IDs and names are included in the LLM prompt when nodes are supplied.
2. The returned GraphChanges reflect the LLM's keep/remove/add suggestions.
3. The service works correctly with existing_nodes=None (no plan context).
4. LLM failures are caught and returned as AI_SERVICE_ERROR results.

Primary reader: a developer debugging why existing node context is missing from
the LLM prompt, or verifying the clarify-goal response parsing logic.
"""

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
        """Node IDs and names from existing_nodes appear in the LLM user prompt.

        Captures the raw prompt sent to the LLM and asserts that node identifiers
        and names are present — confirming the service serialises node context
        correctly for the LLM to reference during its analysis.
        Expected: 'n1', '矩阵乘法', and 'n3' in captured user prompt; result.success
        is True; changes reflect the mocked keep/remove/add lists.
        """
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
        """clarify_goal succeeds when existing_nodes is None (no plan context).

        When called without plan context, the service must still work and
        return a valid result. The LLM may suggest creating a new plan.
        Expected: result.success=True, changes.keep=[].
        """
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
        """An LLM exception is caught and returned as an error with code AI_SERVICE_ERROR.

        The service must never propagate an unhandled exception; LLM failures
        must be wrapped in a structured error result.
        Expected: result.success=False, error.code='AI_SERVICE_ERROR'.
        """
        with patch("services.ai_service.get_llm_client") as mock:
            mock.return_value = MagicMock(
                chat_json=AsyncMock(side_effect=Exception("LLM timeout"))
            )
            service = AIService()
            result = await service.clarify_goal("a", "b", existing_nodes=EXISTING_NODES)

        assert result.success is False
        assert result.error.code == "AI_SERVICE_ERROR"
