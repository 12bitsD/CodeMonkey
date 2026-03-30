def test_notes_requires_auth(client):
    resp = client.get("/api/notes")
    assert resp.status_code == 401


def test_create_note_and_stats(client, auth_headers_a):
    plan_data = {
        "title": "计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "note_n1",
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
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "note_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "note_n1", "content": "hello"},
        headers=auth_headers_a,
    )
    assert note.status_code == 200
    assert note.json()["success"] is True

    stats = client.get("/api/stats/overview", headers=auth_headers_a)
    assert stats.status_code == 200
    assert stats.json()["success"] is True
