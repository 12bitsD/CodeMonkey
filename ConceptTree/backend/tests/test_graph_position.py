"""Node position API validates updating the visual (x, y) coordinates of graph nodes.

When a learner drags nodes around in the knowledge-graph canvas, the frontend
sends position updates. This module validates both single-node and bulk-position
update endpoints, covering:
1. Auth protection on both endpoints.
2. Successful single-node position update with float coordinates.
3. Successful bulk position update returning the count of updated nodes.
4. Correct HTTP 404 responses for missing plans or nodes.
5. HTTP 403 rejection when a non-owner attempts to reposition nodes.
6. HTTP 400 rejection when a required coordinate field is missing.

Primary reader: a developer debugging canvas drag-and-drop persistence or
verifying the coordinate API contract.
"""


def test_update_node_position_requires_auth(client):
    """Updating a node's position without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.put(
        "/api/plans/p1/nodes/n1/position",
        json={"x": 100, "y": 200},
    )
    assert resp.status_code == 401


def test_update_node_position_success(client, auth_headers_a):
    """A node's position can be set to any float coordinates and is reflected in the response.

    Uses non-integer coordinates (150.5, -80.3) to confirm the API accepts
    and returns floating-point values without rounding.
    Expected: HTTP 200, success=True, data.nodeId matches, data.x and data.y
    match the submitted values exactly.
    """
    plan_data = {
        "title": "位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "pos_n1",
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
        "targetNodeId": "pos_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/pos_n1/position",
        json={"x": 150.5, "y": -80.3},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["nodeId"] == "pos_n1"
    assert body["data"]["x"] == 150.5
    assert body["data"]["y"] == -80.3


def test_update_node_position_plan_not_found(client, auth_headers_a):
    """Updating a node's position in a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put(
        "/api/plans/nonexistent/nodes/n1/position",
        json={"x": 100, "y": 200},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_position_node_not_found(client, auth_headers_a):
    """Updating the position of a node that is not in the plan returns HTTP 404.

    Expected: HTTP 404.
    """
    plan_data = {
        "title": "位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "pos_exists_n1",
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
        "targetNodeId": "pos_exists_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/nonexistent/position",
        json={"x": 100, "y": 200},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_position_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot reposition a node in a plan owned by user A.

    Plan ownership is enforced: position updates are restricted to the plan creator.
    Expected: HTTP 403.
    """
    plan_data = {
        "title": "位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "pos_other_n1",
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
        "targetNodeId": "pos_other_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/pos_other_n1/position",
        json={"x": 100, "y": 200},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_update_node_position_missing_x(client, auth_headers_a):
    """Omitting the required 'x' coordinate field returns HTTP 400.

    Both x and y are required; sending only y must be rejected at the
    request validation layer.
    Expected: HTTP 400.
    """
    plan_data = {
        "title": "位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "pos_x_n1",
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
        "targetNodeId": "pos_x_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/pos_x_n1/position",
        json={"y": 200},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_bulk_update_node_positions_requires_auth(client):
    """Bulk-updating node positions without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.put(
        "/api/plans/p1/nodes/positions",
        json={"positions": []},
    )
    assert resp.status_code == 401


def test_bulk_update_node_positions_success(client, auth_headers_a):
    """Multiple nodes' positions can be updated in a single request.

    Sends two position updates in one call and confirms the response reports
    that exactly 2 nodes were updated.
    Expected: HTTP 200, success=True, data.updated=2.
    """
    plan_data = {
        "title": "批量位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "bulk_n1",
                "name": "节点A",
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
                "id": "bulk_n2",
                "name": "节点B",
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
            },
        ],
        "edges": [],
        "targetNodeId": "bulk_n2",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/positions",
        json={
            "positions": [
                {"nodeId": "bulk_n1", "x": 100, "y": 200},
                {"nodeId": "bulk_n2", "x": -50, "y": 150},
            ]
        },
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["updated"] == 2


def test_bulk_update_node_positions_plan_not_found(client, auth_headers_a):
    """Bulk-updating positions for a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put(
        "/api/plans/nonexistent/nodes/positions",
        json={"positions": [{"nodeId": "n1", "x": 100, "y": 200}]},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_bulk_update_node_positions_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot bulk-update node positions for a plan owned by user A.

    Plan ownership is enforced on the bulk-position endpoint as well.
    Expected: HTTP 403.
    """
    plan_data = {
        "title": "批量位置测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "bulk_other_n1",
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
        "targetNodeId": "bulk_other_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/positions",
        json={"positions": [{"nodeId": "bulk_other_n1", "x": 100, "y": 200}]},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403
