from unittest.mock import patch, AsyncMock, MagicMock


def make_plan(client, auth_headers):
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
    resp = client.post("/api/plans/p1/apply-changes", json={})
    assert resp.status_code == 401


def test_apply_changes_plan_not_found(client, auth_headers_a):
    resp = client.post(
        "/api/plans/nonexistent/apply-changes",
        json={"keep": [], "remove": [], "add": [], "newTitle": "新目标"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_apply_changes_forbidden_for_other_user(client, auth_headers_a, auth_headers_b):
    plan_id = make_plan(client, auth_headers_a)
    resp = client.post(
        f"/api/plans/{plan_id}/apply-changes",
        json={"keep": ["n1"], "remove": ["n3"], "add": [], "newTitle": "新目标"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_apply_changes_removes_nodes(client, auth_headers_a):
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
    plan = next((p for p in plans["data"]["plans"] if p["id"] == plan_id), None)
    assert plan["title"] == "Python数据分析"
