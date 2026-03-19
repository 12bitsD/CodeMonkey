"""recommend-next API validates the 'what should I learn next?' endpoint.

The recommend-next endpoint takes a planId, fetches the plan's graph and
learning history, calls the AI service, and returns the recommended node ID
with a reason. The AI service is mocked in all tests to isolate routing
behaviour from LLM calls.

This module validates:
1. The endpoint is auth-protected (HTTP 401 without a token).
2. A valid request returns the mocked recommended node ID and reason.
3. A non-existent planId returns HTTP 404.
4. Another user's planId returns HTTP 403.

Primary reader: a developer debugging the recommend-next routing logic
or verifying that AI responses are correctly forwarded to the client.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def make_plan(client, auth_headers):
    """Create a three-node backpropagation learning plan and return its ID.

    The plan has node n1 (learned: matrix multiplication) → n2 (unlearned:
    chain rule) → n3 (target: backpropagation). This reflects a realistic
    partial-progress learning scenario for the recommend-next tests.
    """
    plan_data = {
        "title": "反向传播",
        "originalInput": "input",
        "nodes": [
            {
                "id": "n1",
                "name": "矩阵乘法",
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
                "name": "链式法则",
                "status": "unlearned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
            },
            {
                "id": "n3",
                "name": "反向传播",
                "status": "unlearned",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
            },
        ],
        "edges": [
            {"from_node": "n1", "to_node": "n2"},
            {"from_node": "n2", "to_node": "n3"},
        ],
        "targetNodeId": "n3",
    }
    resp = client.post("/api/plans", json=plan_data, headers=auth_headers)
    return resp.json()["data"]["id"]


def test_recommend_next_requires_auth(client):
    """recommend-next rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post("/api/ai/recommend-next", json={"planId": "p1"})
    assert resp.status_code == 401


def test_recommend_next_returns_node_id(client, auth_headers_a):
    """recommend-next returns the mocked recommended node ID and reason.

    Creates a plan, mocks the AI service to return node 'n2' with a reason,
    and confirms the API response mirrors the mocked data.
    Expected: HTTP 200, success=True, data.recommended_node_id='n2', reason present.
    """
    plan_id = make_plan(client, auth_headers_a)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = MagicMock()
    mock_result.data.recommended_node_id = "n2"
    mock_result.data.reason = "链式法则的前置知识已完成"
    mock_result.data.model_dump.return_value = {
        "recommended_node_id": "n2",
        "reason": "链式法则的前置知识已完成",
    }

    with patch("routers.ai.get_ai_service") as mock_svc_factory:
        mock_svc = MagicMock()
        mock_svc.recommend_next = AsyncMock(return_value=mock_result)
        mock_svc_factory.return_value = mock_svc

        resp = client.post(
            "/api/ai/recommend-next",
            json={"planId": plan_id},
            headers=auth_headers_a,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["recommended_node_id"] == "n2"
    assert "reason" in body["data"]


def test_recommend_next_plan_not_found(client, auth_headers_a):
    """recommend-next for a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.post(
        "/api/ai/recommend-next",
        json={"planId": "nonexistent"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_recommend_next_forbidden_for_other_user(
    client, auth_headers_a, auth_headers_b
):
    """User B cannot request a recommendation for a plan owned by user A.

    Plan ownership is enforced: the recommend-next endpoint must return
    HTTP 403 when the requester is not the plan creator.
    Expected: HTTP 403.
    """
    plan_id = make_plan(client, auth_headers_a)

    resp = client.post(
        "/api/ai/recommend-next",
        json={"planId": plan_id},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403
