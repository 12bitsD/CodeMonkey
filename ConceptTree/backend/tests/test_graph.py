def test_update_node_status_idempotency_key_prevents_duplicate_sessions(
    client, auth_headers_a, db
):
    plan_data = {
        "title": "idempotent graph status",
        "originalInput": "input",
        "nodes": [
            {
                "id": "idempotent-status-node",
                "name": "Status Node",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
            }
        ],
        "edges": [],
        "targetNodeId": "idempotent-status-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_idempotent-status-node"
    headers = {**auth_headers_a, "Idempotency-Key": "node-status-double-click"}

    first = client.put(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}/status",
        json={"status": "learned"},
        headers=headers,
    )
    second = client.put(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}/status",
        json={"status": "learned"},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"] == first.json()["data"]

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE plan_id = %s AND node_id = %s",
            (plan_id, stored_node_id),
        )
        assert cur.fetchone()[0] == 1


def test_get_graph_requires_auth(client):
    resp = client.get("/api/plans/p_any/graph")
    assert resp.status_code == 401


def test_get_graph_success_and_edges_shape(client, auth_headers_a):
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


def test_get_graph_returns_content_cache(client, auth_headers_a, db):
    plan_data = {
        "title": "cache graph",
        "originalInput": "input",
        "nodes": [
            {
                "id": "cache-node",
                "name": "A",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": ["topic"],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "coding",
            }
        ],
        "edges": [],
        "targetNodeId": "cache-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_cache-node"

    with db.cursor() as cur:
        cur.execute(
            "UPDATE nodes SET content_cache = %s WHERE id = %s",
            ('{"0": "cached explanation"}', stored_node_id),
        )
    db.commit()

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)
    assert graph.status_code == 200
    node = graph.json()["data"]["nodes"][0]
    assert node["contentCache"] == {"0": "cached explanation"}


def test_get_graph_returns_resource_search_cache(client, auth_headers_a, db):
    plan_data = {
        "title": "resource cache graph",
        "originalInput": "input",
        "nodes": [
            {
                "id": "resource-node",
                "name": "Backpropagation",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": ["topic"],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "coding",
            }
        ],
        "edges": [],
        "targetNodeId": "resource-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_resource-node"

    with db.cursor() as cur:
        cur.execute(
            "UPDATE nodes SET resource_search_cache = %s WHERE id = %s",
            (
                '{"items":[{"name":"官方教程","url":"https://example.com","reason":"系统讲解","source":"web_search"}],"query":"backpropagation tutorial"}',
                stored_node_id,
            ),
        )
    db.commit()

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)
    assert graph.status_code == 200
    node = graph.json()["data"]["nodes"][0]
    assert node["resourceSearchCache"]["query"] == "backpropagation tutorial"
    assert node["resourceSearchCache"]["items"][0]["source"] == "web_search"


def test_update_node_target_end_date_persists_in_graph(client, auth_headers_a):
    from datetime import date, timedelta

    future_date = (date.today() + timedelta(days=10)).isoformat()
    plan_data = {
        "title": "node deadline graph",
        "originalInput": "input",
        "nodes": [
            {
                "id": "deadline-node",
                "name": "Deadline Node",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
            }
        ],
        "edges": [],
        "targetNodeId": "deadline-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_deadline-node"

    updated = client.put(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}",
        json={"targetEndDate": future_date},
        headers=auth_headers_a,
    )
    assert updated.status_code == 200
    assert str(updated.json()["data"]["targetEndDate"]).startswith(future_date)

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)
    assert graph.status_code == 200
    node = graph.json()["data"]["nodes"][0]
    assert str(node["targetEndDate"]).startswith(future_date)
