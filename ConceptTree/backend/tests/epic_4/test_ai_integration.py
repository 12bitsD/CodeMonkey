"""Integration tests for AI service with real LLM"""

import pytest
import os

from services.ai_service import get_ai_service

# Skip tests if no API key configured
pytestmark = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY not set"
)


@pytest.mark.asyncio
async def test_parse_goal_basic():
    """Test parse-goal with simple input"""
    service = get_ai_service()

    result = await service.parse_goal("我想学Python")

    assert result.success is True
    assert result.data is not None
    assert (
        "Python" in result.data.interpretation
        or "python" in result.data.interpretation.lower()
    )
    assert result.data.suggestedNodeCount > 0
    assert result.data.suggestedNodeCount <= 15


@pytest.mark.asyncio
async def test_parse_goal_with_background():
    """Test parse-goal extracts background information"""
    service = get_ai_service()

    result = await service.parse_goal("我想理解反向传播，我有Python基础但数学不好")

    assert result.success is True
    assert result.data is not None
    assert len(result.data.backgroundSummary) >= 2


@pytest.mark.asyncio
async def test_generate_graph_basic():
    """Test generate-graph creates a valid graph"""
    service = get_ai_service()

    result = await service.generate_graph(
        interpretation="理解Python基础语法",
        original_input="我想学Python",
        user_background=None,
    )

    assert result.success is True
    assert result.data is not None
    assert len(result.data.nodes) >= 3
    assert len(result.data.nodes) <= 15

    # Target node must exist
    target_exists = any(
        node.id == result.data.targetNodeId for node in result.data.nodes
    )
    assert target_exists, "Target node must exist in graph"

    # All edge references must be valid
    node_ids = {node.id for node in result.data.nodes}
    for edge in result.data.edges:
        assert edge.from_node in node_ids, (
            f"Edge from {edge.from_node} references non-existent node"
        )
        assert edge.to_node in node_ids, (
            f"Edge to {edge.to_node} references non-existent node"
        )


@pytest.mark.asyncio
async def test_parse_goal_empty_input():
    """Test parse-goal handles edge cases gracefully"""
    service = get_ai_service()

    result = await service.parse_goal("")

    # Should either succeed with generic interpretation or fail gracefully
    if result.success:
        assert result.data is not None
    else:
        assert result.error is not None
