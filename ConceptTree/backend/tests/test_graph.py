"""Graph API validates retrieval of a plan's knowledge graph (nodes and edges).

A learning plan is represented as a directed graph where nodes are concepts
and edges indicate prerequisite relationships. This module validates:
1. The graph endpoint is auth-protected.
2. After creating a plan with nodes and edges, the graph response contains
   the correct edge shape (from_node/to_node fields).

Primary reader: a developer debugging missing edges in the graph view or
verifying the shape of the graph response payload.
"""


def test_get_graph_requires_auth(client):
    """Fetching a plan's graph without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.get("/api/plans/p_any/graph")
    assert resp.status_code == 401


def test_get_graph_success_and_edges_shape(client, auth_headers_a):
    """A plan's graph is returned with correctly shaped edge objects.

    Creates a plan with two nodes (g1 → g2) and one edge, then fetches the
    graph and verifies that the edges array contains objects with 'from_node'
    and 'to_node' keys — confirming the API contract matches what the
    frontend expects.
    Expected: HTTP 200, success=True, at least one edge object with both
    from_node and to_node fields present.
    """
    plan_data = {
        "title": "图谱计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "g1",
                "name": "A",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            },
            {
                "id": "g2",
                "name": "B",
                "status": "unlearned",
                "x": 10,
                "y": 10,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
        ],
        "edges": [{"from_node": "g1", "to_node": "g2"}],
        "targetNodeId": "g2",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)
    assert graph.status_code == 200
    body = graph.json()
    assert body["success"] is True
    edges = body["data"]["edges"]
    assert edges and "from_node" in edges[0] and "to_node" in edges[0]
