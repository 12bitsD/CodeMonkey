def test_ai_parse_goal_requires_auth(client):
    resp = client.post("/api/ai/parse-goal", json={"input": "我想学反向传播"})
    assert resp.status_code == 401


def test_ai_generate_graph_requires_auth(client):
    resp = client.post(
        "/api/ai/generate-graph",
        json={"input": "我想学反向传播", "interpretation": "反向传播"},
    )
    assert resp.status_code == 401


def test_ai_parse_goal_success(client, auth_headers_a):
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": "我想学反向传播"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
