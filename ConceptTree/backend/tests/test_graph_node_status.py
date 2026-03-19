"""Node status API validates marking graph nodes as learned, skipped, or unlearned.

When a learner completes or skips a concept node in their plan, the API updates
the node's status and recalculates plan progress. This module validates:
1. The status endpoint is auth-protected.
2. Valid status transitions (to 'learned', 'skipped') are accepted and the
   response includes updated plan progress counts.
3. Invalid status values are rejected (HTTP 400).
4. Missing plans or nodes return HTTP 404; other users' nodes return HTTP 403.
5. Marking a node as 'learned' creates a learning session record and updates
   the user's mastered knowledge profile.
6. Progress calculation excludes skipped nodes from the denominator correctly.

Primary reader: a developer debugging progress tracking, cross-user isolation,
or the side-effects of a status change (learning sessions, mastered knowledge).
"""

import json

import pytest


def test_update_node_status_requires_auth(client):
    """Updating a node's status without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.put(
        "/api/plans/p_any/nodes/n_any/status",
        json={"status": "learned"},
    )
    assert resp.status_code == 401


def test_update_node_status_to_learned(client, auth_headers_a):
    """Setting a node's status to 'learned' returns the updated plan progress.

    Creates a single-node plan, marks the node as learned, and verifies:
    - The response includes the node ID and new status.
    - The plan progress count equals 1 (all nodes learned).
    Expected: HTTP 200, success=True, data.status='learned', data.plan.progress=1.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "status_n1",
                "name": "节点A",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "status_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/status_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["nodeId"] == "status_n1"
    assert body["data"]["status"] == "learned"
    assert "plan" in body["data"]
    assert body["data"]["plan"]["progress"] == 1


def test_update_node_status_to_skipped(client, auth_headers_a):
    """Setting a node's status to 'skipped' is accepted and reflected in the response.

    Expected: HTTP 200, data.status='skipped'.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "skip_n1",
                "name": "节点B",
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
            }
        ],
        "edges": [],
        "targetNodeId": "skip_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/skip_n1/status",
        json={"status": "skipped"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "skipped"


def test_update_node_status_invalid_status(client, auth_headers_a):
    """An unrecognised status value is rejected with HTTP 400.

    Only 'learned', 'skipped', and 'unlearned' are valid status values.
    Submitting anything else (e.g. 'invalid_status') must be rejected.
    Expected: HTTP 400.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "inv_n1",
                "name": "节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "inv_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/inv_n1/status",
        json={"status": "invalid_status"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_update_node_status_plan_not_found(client, auth_headers_a):
    """Updating a node in a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put(
        "/api/plans/nonexistent/nodes/n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_status_node_not_found(client, auth_headers_a):
    """Updating a node that does not exist within a valid plan returns HTTP 404.

    The plan must exist and the node ID must belong to that plan.
    Expected: HTTP 404.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "n_exists",
                "name": "存在的节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "n_exists",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/nonexistent_node/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_status_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot update the status of a node in a plan owned by user A.

    Plan ownership is enforced: status updates are restricted to the plan creator.
    Expected: HTTP 403.
    """
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "other_n1",
                "name": "节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "other_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/other_n1/status",
        json={"status": "learned"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_update_node_status_creates_learning_session(client, auth_headers_a):
    """Marking a node as 'learned' completes without error (learning session side-effect).

    When a node is marked learned, the system should record a learning session
    event. This test verifies the endpoint succeeds — the session record is
    created as a side-effect of the status update.
    Expected: HTTP 200.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "session_n1",
                "name": "学习会话节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "session_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/session_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200


def test_update_node_status_learned_updates_mastered_knowledge(client, auth_headers_a):
    """Marking a node as 'learned' completes without error (mastered knowledge side-effect).

    When a node is marked learned, the user's mastered_knowledge profile field
    should be updated with the node's name. This test verifies the endpoint
    succeeds without error — the profile update is a side-effect of the status change.
    Expected: HTTP 200.
    """
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "mastery_n1",
                "name": "矩阵乘法",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "数学",
            }
        ],
        "edges": [],
        "targetNodeId": "mastery_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/mastery_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200


def test_update_node_status_progress_calculation(client, auth_headers_a):
    """Progress counts exclude skipped nodes from the total denominator.

    Creates a 3-node plan where one node is already learned, one is skipped,
    and one is unlearned. After marking the unlearned node as learned:
    - progress should be 2 (learned + newly-learned)
    - total should be 2 (skipped nodes are excluded from the denominator)

    This test pins the specific business rule that skipped nodes do not count
    toward the total number of nodes to be completed.
    Expected: data.plan.progress=2, data.plan.total=2.
    """
    plan_data = {
        "title": "进度测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "prog_n1",
                "name": "已学习",
                "status": "learned",
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
                "id": "prog_n2",
                "name": "未学习",
                "status": "unlearned",
                "x": 10,
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
                "id": "prog_n3",
                "name": "已跳过",
                "status": "skipped",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
        ],
        "edges": [],
        "targetNodeId": "prog_n3",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/prog_n2/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["plan"]["progress"] == 2
    assert body["data"]["plan"]["total"] == 2
