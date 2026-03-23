def test_parse_goal_input_too_short(client, auth_headers_a):
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": "学"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_parse_goal_input_empty(client, auth_headers_a):
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": ""},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_generate_graph_requires_auth(client):
    resp = client.post(
        "/api/ai/generate-graph",
        json={"input": "我想学Python", "interpretation": "学Python"},
    )
    assert resp.status_code == 401
