def test_get_notes_requires_auth(client):
    resp = client.get("/api/notes")
    assert resp.status_code == 401


def test_get_notes_empty(client, auth_headers_a):
    resp = client.get("/api/notes", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["notes"] == []
    assert body["data"]["total"] == 0


def test_get_notes_with_notes(client, auth_headers_a):
    plan_data = {
        "title": "笔记测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "note_node_1",
                "name": "节点A",
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
        "targetNodeId": "note_node_1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "note_node_1", "content": "测试笔记"},
        headers=auth_headers_a,
    )

    resp = client.get("/api/notes", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["notes"]) == 1
    assert body["data"]["notes"][0]["content"] == "测试笔记"


def test_get_notes_filter_by_plan_id(client, auth_headers_a):
    plan_data = {
        "title": "笔记测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "filter_node_1",
                "name": "节点A",
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
            {
                "id": "filter_node_2",
                "name": "节点B",
                "status": "unlearned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            },
        ],
        "edges": [],
        "targetNodeId": "filter_node_1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "filter_node_1", "content": "笔记A"},
        headers=auth_headers_a,
    )
    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "filter_node_2", "content": "笔记B"},
        headers=auth_headers_a,
    )

    resp = client.get(f"/api/notes?planId={plan_id}", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["notes"]) == 2


def test_get_notes_filter_by_search(client, auth_headers_a):
    plan_data = {
        "title": "搜索测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "search_node_1",
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
        "targetNodeId": "search_node_1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "search_node_1", "content": "矩阵乘法的笔记"},
        headers=auth_headers_a,
    )
    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "search_node_1", "content": "链式法则的笔记"},
        headers=auth_headers_a,
    )

    resp = client.get("/api/notes?search=矩阵", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["notes"]) == 1
    assert body["data"]["notes"][0]["content"] == "矩阵乘法的笔记"


def test_create_note_requires_auth(client):
    resp = client.post(
        "/api/notes",
        json={"planId": "p1", "nodeId": "n1", "content": "笔记"},
    )
    assert resp.status_code == 401


def test_create_note_plan_not_found(client, auth_headers_a):
    resp = client.post(
        "/api/notes",
        json={"planId": "nonexistent", "nodeId": "n1", "content": "笔记"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_create_note_node_not_found(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "note_exists_node",
                "name": "存在的节点",
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
        "targetNodeId": "note_exists_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "nonexistent_node", "content": "笔记"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_create_note_content_empty(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "empty_content_node",
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
        "targetNodeId": "empty_content_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "empty_content_node", "content": ""},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_create_note_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "other_user_node",
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
        "targetNodeId": "other_user_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "other_user_node", "content": "笔记"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_update_note_requires_auth(client):
    resp = client.put("/api/notes/note_123", json={"content": "更新"})
    assert resp.status_code == 401


def test_update_note_not_found(client, auth_headers_a):
    resp = client.put(
        "/api/notes/nonexistent_note",
        json={"content": "更新内容"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_note_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "update_node",
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
        "targetNodeId": "update_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note_resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "update_node", "content": "原内容"},
        headers=auth_headers_a,
    )
    note_id = note_resp.json()["data"]["id"]

    resp = client.put(
        f"/api/notes/{note_id}",
        json={"content": "被B用户更新"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_update_note_content_empty(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "empty_update_node",
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
        "targetNodeId": "empty_update_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note_resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "empty_update_node", "content": "原内容"},
        headers=auth_headers_a,
    )
    note_id = note_resp.json()["data"]["id"]

    resp = client.put(
        f"/api/notes/{note_id}",
        json={"content": "   "},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_update_note_success(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "success_update_node",
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
        "targetNodeId": "success_update_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note_resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "success_update_node", "content": "原内容"},
        headers=auth_headers_a,
    )
    note_id = note_resp.json()["data"]["id"]

    resp = client.put(
        f"/api/notes/{note_id}",
        json={"content": "更新后的内容"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["content"] == "更新后的内容"


def test_delete_note_requires_auth(client):
    resp = client.delete("/api/notes/note_123")
    assert resp.status_code == 401


def test_delete_note_not_found(client, auth_headers_a):
    resp = client.delete("/api/notes/nonexistent_note", headers=auth_headers_a)
    assert resp.status_code == 404


def test_delete_note_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "delete_node",
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
        "targetNodeId": "delete_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note_resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "delete_node", "content": "笔记"},
        headers=auth_headers_a,
    )
    note_id = note_resp.json()["data"]["id"]

    resp = client.delete(f"/api/notes/{note_id}", headers=auth_headers_b)
    assert resp.status_code == 403


def test_delete_note_success(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "del_success_node",
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
        "targetNodeId": "del_success_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    note_resp = client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "del_success_node", "content": "要删除的笔记"},
        headers=auth_headers_a,
    )
    note_id = note_resp.json()["data"]["id"]

    resp = client.delete(f"/api/notes/{note_id}", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    get_resp = client.get("/api/notes", headers=auth_headers_a)
    notes = get_resp.json()["data"]["notes"]
    assert not any(n["id"] == note_id for n in notes)


def test_create_note_idempotency_key_replays_same_response(client, auth_headers_a, db):
    plan_data = {
        "title": "idempotent notes",
        "originalInput": "input",
        "nodes": [
            {
                "id": "idempotent_note_node",
                "name": "Note Node",
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
        "targetNodeId": "idempotent_note_node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    payload = {
        "planId": plan_id,
        "nodeId": "idempotent_note_node",
        "content": "same click should save once",
    }
    headers = {**auth_headers_a, "Idempotency-Key": "note-save-double-click"}

    first = client.post("/api/notes", json=payload, headers=headers)
    second = client.post("/api/notes", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM notes WHERE plan_id = %s AND content = %s",
            (plan_id, payload["content"]),
        )
        assert cur.fetchone()[0] == 1
