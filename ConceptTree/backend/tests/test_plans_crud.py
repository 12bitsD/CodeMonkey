def test_create_plan_requires_auth(client):
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
