def test_archive_plan_already_archived(client, auth_headers_a):
    plan_data = {
        "title": "双重归档测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "arch_dup_n1",
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
        "targetNodeId": "arch_dup_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)

    resp = client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)
    assert resp.status_code == 400


def test_restore_plan_already_active(client, auth_headers_a):
    plan_data = {
        "title": "双重恢复测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "rest_dup_n1",
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
        "targetNodeId": "rest_dup_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(f"/api/plans/{plan_id}/restore", headers=auth_headers_a)
    assert resp.status_code == 400


def test_archive_plan_not_found(client, auth_headers_a):
    resp = client.put("/api/plans/nonexistent/archive", headers=auth_headers_a)
    assert resp.status_code == 404


def test_restore_plan_not_found(client, auth_headers_a):
    resp = client.put("/api/plans/nonexistent/restore", headers=auth_headers_a)
    assert resp.status_code == 404


def test_archive_plan_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "arch_forbid_n1",
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
        "targetNodeId": "arch_forbid_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_b)
    assert resp.status_code == 403


def test_restore_plan_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "rest_forbid_n1",
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
        "targetNodeId": "rest_forbid_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)

    resp = client.put(f"/api/plans/{plan_id}/restore", headers=auth_headers_b)
    assert resp.status_code == 403
