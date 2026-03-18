from unittest.mock import patch, AsyncMock, MagicMock


def make_plan_with_nodes(client, auth_headers):
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
    resp = client.post(
        "/api/ai/clarify-goal", json={"originalGoal": "x", "newGoal": "yyyyy"}
    )
    assert resp.status_code == 401


def test_clarify_goal_without_plan_id_still_works(client, auth_headers_a):
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
