"""Plans CRUD API validates creating learning plans and enforcing ownership.

A learning plan is the central entity in ConceptTree — it groups a set of
concept nodes (graph) that a learner wants to master. This module validates:
1. The plan creation endpoint is auth-protected.
2. Creating a plan with nodes and edges succeeds and returns the plan title.
3. A user cannot delete another user's plan (ownership enforced, HTTP 403).

Primary reader: a developer debugging plan creation failures or verifying
the ownership-enforcement logic for destructive operations.
"""


def test_create_plan_requires_auth(client):
    """Creating a plan without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "我想学Python",
        "nodes": [
            {
                "id": "node_test_1",
                "name": "Python基础",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "基础",
                "what": ["语法"],
                "mastery": ["写出Hello World"],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "node_test_1",
    }
    resp = client.post("/api/plans", json=plan_data)
    assert resp.status_code == 401


def test_create_plan_with_edges_success(client, auth_headers_a):
    """Creating a plan with two nodes and one directed edge succeeds.

    Verifies that the full plan payload (nodes + edges) is accepted and
    that the response reflects the submitted title.
    Expected: HTTP 200, success=True, data.title matches the submitted title.
    """
    plan_data = {
        "title": "带边计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "n_a_1",
                "name": "A",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "why",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            },
            {
                "id": "n_a_2",
                "name": "B",
                "status": "unlearned",
                "x": 10,
                "y": 10,
                "why": "why",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
        ],
        "edges": [{"from_node": "n_a_1", "to_node": "n_a_2"}],
        "targetNodeId": "n_a_2",
    }
    resp = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == "带边计划"


def test_cross_user_delete_forbidden(client, auth_headers_a, auth_headers_b):
    """User B cannot delete a plan that belongs to user A.

    Plan ownership is strictly enforced: the delete endpoint must return
    HTTP 403 when the requester is not the plan creator.
    Expected: plan creation by user A returns HTTP 200; deletion attempt
    by user B returns HTTP 403.
    """
    plan_data = {
        "title": "用户A计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "n_cross_1",
                "name": "X",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "why",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "n_cross_1",
    }
    resp = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    assert resp.status_code == 200
    plan_id = resp.json()["data"]["id"]

    resp_b = client.delete(f"/api/plans/{plan_id}", headers=auth_headers_b)
    assert resp_b.status_code == 403
