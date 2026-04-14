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
