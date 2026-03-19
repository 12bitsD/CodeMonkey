"""AI endpoints smoke tests: auth protection and basic success for core AI calls.

The AI feature lets users describe a learning goal; the backend uses an LLM
to parse the intent (parse-goal) and then generate a knowledge graph
(generate-graph). This module validates:
1. Both AI endpoints are auth-protected — unauthenticated calls return HTTP 401.
2. A valid parse-goal request from an authenticated user returns HTTP 200
   with success=True (live LLM call; requires a configured LLM service).

Primary reader: a developer checking that auth guards are in place or
running a quick sanity check after deploying a new LLM backend.
"""


def test_ai_parse_goal_requires_auth(client):
    """parse-goal rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post("/api/ai/parse-goal", json={"input": "我想学反向传播"})
    assert resp.status_code == 401


def test_ai_generate_graph_requires_auth(client):
    """generate-graph rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post(
        "/api/ai/generate-graph",
        json={"input": "我想学反向传播", "interpretation": "反向传播"},
    )
    assert resp.status_code == 401


def test_ai_parse_goal_success(client, auth_headers_a):
    """parse-goal returns HTTP 200 with success=True for a valid authenticated request.

    This is a live call against the configured LLM service. If the LLM is
    not reachable, the endpoint should still return a structured error rather
    than an unhandled exception.
    Expected: HTTP 200, success=True.
    """
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": "我想学反向传播"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
