"""apply-changes API validates incremental plan graph mutations.

When a learner refines their goal, the apply-changes endpoint modifies an
existing plan's graph in-place: it removes specified nodes, retains others
(preserving their learning status), and adds placeholder nodes for new concepts.

This module validates:
1. The endpoint is auth-protected (HTTP 401 without a token).
2. Missing plan returns HTTP 404; another user's plan returns HTTP 403.
3. Removing nodes actually removes them from the graph.
4. Nodes in the 'keep' list retain their current learning status (e.g. 'learned').
5. Adding new concept names creates stub nodes in the graph.
6. The plan title is updated to the new title provided in the request.

The AI service is not called in these tests — apply-changes is a pure
graph-mutation operation driven by client-supplied instructions.

Primary reader: a developer debugging plan graph mutations or verifying
that learning progress is not lost when a plan is refined.
"""

from unittest.mock import patch, AsyncMock, MagicMock


def make_plan(client, auth_headers):
    """Create a three-node Python learning plan and return its ID.

    The plan has nodes n1 (learned), n2 (unlearned), n3 (unlearned/target)
    connected in a chain (n1→n2→n3). Tests use this fixture to verify that
    remove/keep/add operations produce the expected graph changes.
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
                "isTarget": False,
            },
            {
                "id": "n3",
                "name": "文件读写",
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


def test_apply_changes_requires_auth(client):
    """apply-changes rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post("/api/plans/p1/apply-changes", json={})
    assert resp.status_code == 401


def test_apply_changes_plan_not_found(client, auth_headers_a):
    """apply-changes for a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.post(
        "/api/plans/nonexistent/apply-changes",
        json={"keep": [], "remove": [], "add": [], "newTitle": "新目标"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_apply_changes_forbidden_for_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot apply changes to a plan owned by user A.

    Plan ownership is enforced: apply-changes is restricted to the plan creator.
    Expected: HTTP 403.
    """
    plan_id = make_plan(client, auth_headers_a)
    resp = client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={"keep": ["n1"], "remove": ["n3"], "add": [], "newTitle": "新目标"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_apply_changes_removes_nodes(client, auth_headers_a):
    """Nodes in the 'remove' list are deleted from the graph; 'keep' nodes remain.

    Removes n3 ('文件读写') and keeps n1, n2. After the operation, the graph
    must not contain '文件读写' but must still contain '变量与类型' and '函数基础'.
    Expected: HTTP 200, success=True; graph node names confirm removal and retention.
    """
    plan_id = make_plan(client, auth_headers_a)

    resp = client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={
            "keep": ["n1", "n2"],
            "remove": ["n3"],
            "add": [],
            "newTitle": "学Python函数",
        },
        headers=auth_headers_a,
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a).json()
    node_names = [n["name"] for n in graph["data"]["nodes"]]
    assert "文件读写" not in node_names
    assert "变量与类型" in node_names
    assert "函数基础" in node_names


def test_apply_changes_preserves_learned_status(client, auth_headers_a):
    """Nodes in the 'keep' list retain their original learning status.

    Node n1 has status='learned'. After applying changes that keep n1,
    its status must still be 'learned' — learning progress is never lost
    during plan refinement.
    Expected: the retained node '变量与类型' still has status='learned'.
    """
    plan_id = make_plan(client, auth_headers_a)

    resp = client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={"keep": ["n1", "n2"], "remove": ["n3"], "add": [], "newTitle": "新目标"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a).json()
    learned = next(n for n in graph["data"]["nodes"] if n["name"] == "变量与类型")
    assert learned["status"] == "learned"


def test_apply_changes_adds_stub_nodes(client, auth_headers_a):
    """New concept names in the 'add' list are created as stub nodes in the graph.

    Adds 'NumPy基础' and 'pandas入门' while removing n3. The graph must
    subsequently contain nodes with those names.
    Expected: HTTP 200; graph contains nodes named 'NumPy基础' and 'pandas入门'.
    """
    plan_id = make_plan(client, auth_headers_a)

    resp = client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={
            "keep": ["n1", "n2"],
            "remove": ["n3"],
            "add": ["NumPy基础", "pandas入门"],
            "newTitle": "Python数据分析",
        },
        headers=auth_headers_a,
    )
    assert resp.status_code == 200

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a).json()
    node_names = [n["name"] for n in graph["data"]["nodes"]]
    assert "NumPy基础" in node_names
    assert "pandas入门" in node_names


def test_apply_changes_updates_plan_title(client, auth_headers_a):
    """The plan's title is updated to the 'newTitle' value provided in the request.

    After applying changes with newTitle='Python数据分析', a GET /plans
    request must return that plan with the updated title.
    Expected: plan title in the listing matches 'Python数据分析'.
    """
    plan_id = make_plan(client, auth_headers_a)

    client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={
            "keep": ["n1"],
            "remove": ["n2", "n3"],
            "add": [],
            "newTitle": "Python数据分析",
        },
        headers=auth_headers_a,
    )

    plans = client.get("/api/plans", headers=auth_headers_a).json()
    plan = next((p for p in plans["data"] if p["id"] == plan_id), None)
    assert plan["title"] == "Python数据分析"
