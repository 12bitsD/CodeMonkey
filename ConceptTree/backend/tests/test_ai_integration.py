"""Integration tests for the AI service using a real LLM connection.

Unlike the unit tests that mock the LLM client, these tests call the actual
LLM API configured via the LLM_API_KEY environment variable. They validate
that:
1. parse-goal produces a meaningful interpretation containing the goal keyword.
2. parse-goal extracts background information when the user provides context.
3. generate-graph produces a structurally valid graph (correct node count range,
   target node exists, all edge references point to real nodes).
4. parse-goal handles edge-case inputs (empty string) gracefully.

All tests are skipped automatically when LLM_API_KEY is not set, so they
do not block CI environments that lack API access.

Primary reader: a developer verifying end-to-end AI quality after changing
the LLM provider, prompt templates, or response parsing logic.
"""

import pytest
import os

from services.ai_service import get_ai_service

pytestmark = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY not set"
)


@pytest.mark.asyncio
async def test_parse_goal_basic():
    """parse-goal returns an interpretation containing the goal keyword.

    Submits 'I want to learn Python' and checks that the interpretation
    mentions 'Python' in some form — confirming the LLM understood the goal.
    Expected: success=True, data is not None, 'python' in interpretation
    (case-insensitive), suggestedNodeCount in [1, 15].
    """
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
    """parse-goal extracts background information when the user provides context.

    The input mentions both a goal ('understand backpropagation') and
    background context ('have Python basics but weak math'). The service
    must populate the backgroundSummary field with at least 2 items.
    Expected: success=True, len(data.backgroundSummary) >= 2.
    """
    service = get_ai_service()

    result = await service.parse_goal("我想理解反向传播，我有Python基础但数学不好")

    assert result.success is True
    assert result.data is not None
    assert len(result.data.backgroundSummary) >= 2


@pytest.mark.asyncio
async def test_generate_graph_basic():
    """generate-graph returns a structurally valid knowledge graph.

    Validates three structural invariants:
    1. The graph contains between 3 and 15 nodes.
    2. The targetNodeId references a real node in the nodes list.
    3. Every edge's from_node and to_node reference real node IDs.
    Expected: success=True, 3 <= len(nodes) <= 15, target exists,
    all edge endpoints are valid node IDs.
    """
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

    target_exists = any(
        node.id == result.data.targetNodeId for node in result.data.nodes
    )
    assert target_exists, "Target node must exist in graph"

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
    """parse-goal handles an empty string input gracefully without crashing.

    An empty string is an edge case; the service should either succeed with
    a generic interpretation or return a structured error — but never raise
    an unhandled exception.
    Expected: if success is True, data is not None; if success is False,
    error is not None.
    """
    service = get_ai_service()

    result = await service.parse_goal("")

    if result.success:
        assert result.data is not None
    else:
        assert result.error is not None
