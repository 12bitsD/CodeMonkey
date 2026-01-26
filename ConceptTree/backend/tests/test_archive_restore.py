def test_archive_restore_requires_auth(client):
    resp = client.put("/api/plans/p_any/archive")
    assert resp.status_code == 401

    resp = client.put("/api/plans/p_any/restore")
    assert resp.status_code == 401


def test_archive_restore_flow(client, auth_headers_a):
    plan_data = {
        "title": "可归档计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "arch_n1",
                "name": "Node",
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
        "targetNodeId": "arch_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    archived = client.put(
        f"/api/plans/{plan_id}/archive",
        headers=auth_headers_a,
    )
    assert archived.status_code == 200
    assert archived.json()["success"] is True

    restored = client.put(
        f"/api/plans/{plan_id}/restore",
        headers=auth_headers_a,
    )
    assert restored.status_code == 200
    assert restored.json()["success"] is True
