import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def make_plan(client, auth_headers):
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
    resp = client.post("/api/ai/recommend-next", json={"planId": "p1"})
    assert resp.status_code == 401


def test_recommend_next_returns_node_id(client, auth_headers_a):
    plan_id = make_plan(client, auth_headers_a)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = MagicMock()
    mock_result.data.recommendedNodeId = "n2"
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


def test_recommend_next_falls_back_to_local_rule_when_ai_fails(client, auth_headers_a):
    plan_id = make_plan(client, auth_headers_a)

    mock_result = MagicMock()
    mock_result.success = False
    mock_result.error = MagicMock()
    mock_result.error.model_dump.return_value = {
        "code": "AI_ERROR",
        "message": "Invalid API Key",
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
    assert body["data"]["recommended_node_id"].endswith("_n2")
    assert body["data"]["recommendation_source"] == "local"


def test_recommend_next_plan_not_found(client, auth_headers_a):
    resp = client.post(
        "/api/ai/recommend-next",
        json={"planId": "nonexistent"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_recommend_next_forbidden_for_other_user(
    client, auth_headers_a, auth_headers_b
):
    plan_id = make_plan(client, auth_headers_a)

    resp = client.post(
        "/api/ai/recommend-next",
        json={"planId": plan_id},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403
