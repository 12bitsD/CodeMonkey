"""AI input validation: short and empty goal strings are rejected before hitting the LLM.

Request validation happens at the API layer (before any LLM call) to avoid
wasting LLM quota on inputs that are too short to produce meaningful results.
This module validates:
1. A single-character input to parse-goal returns HTTP 422 (validation error).
2. An empty string input to parse-goal returns HTTP 422.
3. The generate-graph endpoint requires authentication (HTTP 401 without a token).

Primary reader: a developer checking that Pydantic validators on AI request
models enforce minimum input length requirements.
"""


def test_parse_goal_input_too_short(client, auth_headers_a):
    """A single-character goal input is rejected with HTTP 422 before reaching the LLM.

    The minimum meaningful input length is enforced via Pydantic validation;
    a one-character string such as '学' cannot be a valid learning goal.
    Expected: HTTP 422 (Unprocessable Entity — validation failed).
    """
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": "学"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 422


def test_parse_goal_input_empty(client, auth_headers_a):
    """An empty string goal input is rejected with HTTP 422.

    An empty input cannot describe any learning goal; it must be rejected
    at the validation layer rather than forwarded to the LLM.
    Expected: HTTP 422.
    """
    resp = client.post(
        "/api/ai/parse-goal",
        json={"input": ""},
        headers=auth_headers_a,
    )
    assert resp.status_code == 422


def test_generate_graph_requires_auth(client):
    """generate-graph rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post(
        "/api/ai/generate-graph",
        json={"input": "我想学Python", "interpretation": "学Python"},
    )
    assert resp.status_code == 401
