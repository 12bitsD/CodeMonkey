def test_stats_overview_requires_auth(client):
    resp = client.get("/api/stats/overview")
    assert resp.status_code == 401


def test_stats_overview_new_user(client, auth_headers_a):
    resp = client.get("/api/stats/overview", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "summary" in body["data"]
    assert "thisWeek" in body["data"]
    assert body["data"]["summary"]["completedPlans"] == 0
    assert body["data"]["summary"]["activePlans"] == 0
    assert body["data"]["summary"]["masteredKnowledge"] == 0
    assert body["data"]["summary"]["totalNotes"] == 0


def test_stats_overview_with_data(client, auth_headers_a):
    plan_data = {
        "title": "统计测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "stats_n1",
                "name": "节点A",
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
                "id": "stats_n2",
                "name": "节点B",
                "status": "learned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "数学",
            },
        ],
        "edges": [{"from_node": "stats_n1", "to_node": "stats_n2"}],
        "targetNodeId": "stats_n2",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "stats_n1", "content": "笔记内容"},
        headers=auth_headers_a,
    )

    resp = client.get("/api/stats/overview", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["summary"]["activePlans"] == 1
    assert body["data"]["summary"]["totalNotes"] == 1


def test_stats_distribution_requires_auth(client):
    resp = client.get("/api/stats/distribution")
    assert resp.status_code == 401


def test_stats_distribution_empty(client, auth_headers_a):
    resp = client.get("/api/stats/distribution", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["distribution"] == []
    assert body["data"]["total"] == 0


def test_stats_distribution_with_learned_nodes(client, auth_headers_a):
    plan_data = {
        "title": "分布测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "dist_n1",
                "name": "节点A",
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
                "id": "dist_n2",
                "name": "节点B",
                "status": "learned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
            {
                "id": "dist_n3",
                "name": "节点C",
                "status": "learned",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "数学",
            },
        ],
        "edges": [],
        "targetNodeId": "dist_n2",
    }
    client.post("/api/plans", json=plan_data, headers=auth_headers_a)

    resp = client.get("/api/stats/distribution", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["total"] == 3

    dist = body["data"]["distribution"]
    assert len(dist) == 2

    prog_domain = next((d for d in dist if d["domain"] == "编程"), None)
    assert prog_domain is not None
    assert prog_domain["count"] == 2

    math_domain = next((d for d in dist if d["domain"] == "数学"), None)
    assert math_domain is not None
    assert math_domain["count"] == 1
