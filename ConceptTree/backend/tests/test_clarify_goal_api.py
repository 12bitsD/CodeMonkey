"""clarify-goal API validates goal refinement with optional plan context.

When a learner wants to adjust their learning goal, the clarify-goal endpoint
compares the old and new goals and suggests whether to modify the existing plan
or create a new one. If a planId is provided, the endpoint fetches the plan's
current nodes and passes them to the AI service for richer analysis.

This module validates:
1. The endpoint is auth-protected (HTTP 401 without a token).
2. The endpoint works without a planId (graceful degradation).
3. When a planId is supplied, the current plan's nodes are retrieved and
   forwarded to the AI service as context.
4. Supplying another user's planId is silently ignored — existing_nodes
   is treated as empty rather than exposing another user's data.

The AI service is mocked in all tests to isolate API routing behaviour
from LLM responses.

Primary reader: a developer debugging plan-context enrichment in the
clarify-goal flow, or verifying cross-user data isolation.
"""

from unittest.mock import patch, AsyncMock, MagicMock


def make_plan_with_nodes(client, auth_headers):
    """Create a two-node learning plan and return its ID.

    Helper used by tests that need an existing plan to reference via planId.
    The plan has a 'learned' prerequisite node (n1 → n2 edge) and an
    'unlearned' target node, so node context is non-trivial.
    """
    plan_data = {
        "title": "学Python",
        "originalInput": "学Python",
        "nodes": [
            {
                "id": "n1",
                "name": "变量与类型",
                "status": "learned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
            },
            {
                "id": "n2",
                "name": "函数基础",
                "status": "unlearned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
            },
        ],
        "edges": [{"from_node": "n1", "to_node": "n2"}],
        "targetNodeId": "n2",
    }
    resp = client.post("/api/plans", json=plan_data, headers=auth_headers)
    return resp.json()["data"]["id"]


def mock_clarify_result(is_large=False):
    """Return a mock AI service result for the clarify-goal operation.

    ``is_large=True`` simulates a large goal change (suggestion='create_new');
    ``is_large=False`` simulates a minor refinement (suggestion='modify').
    """
    result = MagicMock()
    result.success = True
    result.data = MagicMock()
    result.data.model_dump.return_value = {
        "interpretation": "新目标",
        "isLargeChange": is_large,
        "suggestion": "modify" if not is_large else "create_new",
        "reason": "小幅调整",
        "changes": {"keep": ["n1"], "remove": ["n2"], "add": ["新概念"]},
    }
    return result


def test_clarify_goal_requires_auth(client):
    """The clarify-goal endpoint rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post(
        "/api/ai/clarify-goal", json={"originalGoal": "x", "newGoal": "yyyyy"}
    )
    assert resp.status_code == 401


def test_clarify_goal_without_plan_id_still_works(client, auth_headers_a):
    """clarify-goal succeeds when no planId is provided (no existing context needed).

    Without a planId, the endpoint calls the AI service with empty node
    context. The response must still be a valid success.
    Expected: HTTP 200, success=True.
    """
    with patch("routers.ai.get_ai_service") as mock_svc:
        mock_svc.return_value.clarify_goal = AsyncMock(
            return_value=mock_clarify_result()
        )
        resp = client.post(
            "/api/ai/clarify-goal",
            json={"originalGoal": "学Python", "newGoal": "学Python数据分析"},
            headers=auth_headers_a,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_clarify_goal_with_plan_id_passes_nodes_to_service(client, auth_headers_a):
    """When planId is provided, the plan's nodes are forwarded to the AI service.

    Creates a two-node plan, calls clarify-goal with its planId, and captures
    the kwargs passed to the AI service. Both node IDs (n1, n2) must appear
    in the existing_nodes argument — confirming the router fetched the plan's
    nodes and enriched the AI call with them.
    Expected: HTTP 200; captured existing_nodes contains 2 items with ids n1 and n2.
    """
    plan_id = make_plan_with_nodes(client, auth_headers_a)
    captured_kwargs = {}

    async def capture_clarify(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_clarify_result()

    with patch("routers.ai.get_ai_service") as mock_svc:
        mock_svc.return_value.clarify_goal = capture_clarify
        resp = client.post(
            "/api/ai/clarify-goal",
            json={
                "originalGoal": "学Python",
                "newGoal": "学Python数据分析",
                "planId": plan_id,
            },
            headers=auth_headers_a,
        )

    assert resp.status_code == 200
    assert "existing_nodes" in captured_kwargs
    nodes = captured_kwargs["existing_nodes"]
    assert len(nodes) == 2
    node_ids = {n["id"] for n in nodes}
    assert "n1" in node_ids
    assert "n2" in node_ids


def test_clarify_goal_ignores_other_users_plan(client, auth_headers_a, auth_headers_b):
    """Supplying another user's planId results in empty existing_nodes, not a 403.

    The endpoint does not error on cross-user planId access — it silently
    treats the plan as not found for the requesting user and calls the AI
    service with existing_nodes=[]. This prevents information leakage while
    still returning a valid response.
    Expected: HTTP 200; captured existing_nodes is an empty list.
    """
    plan_id = make_plan_with_nodes(client, auth_headers_a)
    captured_kwargs = {}

    async def capture_clarify(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_clarify_result()

    with patch("routers.ai.get_ai_service") as mock_svc:
        mock_svc.return_value.clarify_goal = capture_clarify
        resp = client.post(
            "/api/ai/clarify-goal",
            json={
                "originalGoal": "学Python",
                "newGoal": "学Python数据分析",
                "planId": plan_id,
            },
            headers=auth_headers_b,
        )

    assert resp.status_code == 200
    assert captured_kwargs.get("existing_nodes") == []
