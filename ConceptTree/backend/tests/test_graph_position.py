def test_update_node_position_requires_auth(client):
    resp = client.put(
        "/api/plans/p1/nodes/n1/position",
        json={"x": 100, "y": 200},
    )
    assert resp.status_code == 401


def test_update_node_position_success(client, auth_headers_a):
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
    resp = client.put(
        "/api/plans/nonexistent/nodes/n1/position",
        json={"x": 100, "y": 200},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_position_node_not_found(client, auth_headers_a):
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
    resp = client.put(
        "/api/plans/p1/nodes/positions",
        json={"positions": []},
    )
    assert resp.status_code == 401


def test_bulk_update_node_positions_success(client, auth_headers_a):
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
    resp = client.put(
        "/api/plans/nonexistent/nodes/positions",
        json={"positions": [{"nodeId": "n1", "x": 100, "y": 200}]},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_bulk_update_node_positions_forbidden_other_user(client, auth_headers_a, auth_headers_b):
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
