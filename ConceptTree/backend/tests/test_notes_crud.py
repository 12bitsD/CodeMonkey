"""Notes CRUD API validates create, read, update, and delete operations on learning notes.

Notes are attached to a specific node inside a learning plan, allowing
users to record insights while studying a concept.

This module validates three key scenarios:
1. All note endpoints are auth-protected — unauthenticated requests return HTTP 401.
2. Notes can be created, listed (with optional filters), updated, and deleted by
   their owner; cross-user access is forbidden (HTTP 403).
3. Invalid inputs (non-existent plan/node, empty content) are rejected with the
   correct error codes before any data is written.

Primary reader: a developer debugging a note-related failure or extending the
notes feature with a new field or filter.
"""


def test_get_notes_requires_auth(client):
    """Listing notes without a token returns HTTP 401.

    The notes list endpoint must be protected against unauthenticated access.
    Expected: HTTP 401.
    """
    resp = client.get("/api/notes")
    assert resp.status_code == 401


def test_get_notes_empty(client, auth_headers_a):
    """A new user with no notes receives an empty list, not an error.

    Expected: HTTP 200, success=True, notes=[], total=0.
    """
    resp = client.get("/api/notes", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["notes"] == []
    assert body["data"]["total"] == 0


def test_get_notes_with_notes(client, auth_headers_a):
    """Notes created by the user appear in the listing response.

    Creates a plan with one node, adds a note to that node, then verifies
    that the note is returned with its content intact.
    Expected: HTTP 200, one note with the expected content string.
    """
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
    """The ?planId= filter returns only notes belonging to the specified plan.

    Creates one plan with two nodes, adds a note to each, then filters by
    planId and expects both notes to be returned (they share the same plan).
    Expected: HTTP 200, exactly 2 notes.
    """
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
    """The ?search= filter returns only notes whose content matches the query.

    Creates two notes with different content, searches for a keyword that
    appears in exactly one of them, and confirms only that note is returned.
    Expected: HTTP 200, exactly 1 note with the matching content.
    """
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
    """Creating a note without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.post(
        "/api/notes",
        json={"planId": "p1", "nodeId": "n1", "content": "笔记"},
    )
    assert resp.status_code == 401


def test_create_note_plan_not_found(client, auth_headers_a):
    """Creating a note for a non-existent plan returns HTTP 404.

    The API must validate that the referenced plan exists before creating
    any data.
    Expected: HTTP 404.
    """
    resp = client.post(
        "/api/notes",
        json={"planId": "nonexistent", "nodeId": "n1", "content": "笔记"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_create_note_node_not_found(client, auth_headers_a):
    """Creating a note for a non-existent node within a valid plan returns HTTP 404.

    Even if the plan exists, the node must also be a member of that plan.
    Expected: HTTP 404.
    """
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
    """Creating a note with empty content is rejected with HTTP 400.

    A blank note provides no value and should be rejected at the API layer
    before any database write occurs.
    Expected: HTTP 400.
    """
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
    """User B cannot create a note in a plan owned by user A.

    Plan ownership is enforced: only the plan's creator may add notes to it.
    Expected: HTTP 403.
    """
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
    """Updating a note without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.put("/api/notes/note_123", json={"content": "更新"})
    assert resp.status_code == 401


def test_update_note_not_found(client, auth_headers_a):
    """Updating a note that does not exist returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put(
        "/api/notes/nonexistent_note",
        json={"content": "更新内容"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_note_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot update a note created by user A.

    Note ownership is enforced: only the note's creator may update its content.
    Expected: HTTP 403.
    """
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
    """Updating a note with whitespace-only content is rejected with HTTP 400.

    A note cannot be replaced with blank or whitespace content; the API
    must validate the updated value the same way it validates creation.
    Expected: HTTP 400.
    """
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
    """A user can successfully update their own note and the new content is returned.

    Creates a note with original content, updates it, and verifies the
    response body contains the new content string.
    Expected: HTTP 200, success=True, data.content == updated string.
    """
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
    """Deleting a note without a token returns HTTP 401.

    Expected: HTTP 401.
    """
    resp = client.delete("/api/notes/note_123")
    assert resp.status_code == 401


def test_delete_note_not_found(client, auth_headers_a):
    """Deleting a note that does not exist returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.delete("/api/notes/nonexistent_note", headers=auth_headers_a)
    assert resp.status_code == 404


def test_delete_note_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot delete a note created by user A.

    Note ownership is enforced: only the note's creator may delete it.
    Expected: HTTP 403.
    """
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
    """A user can delete their own note and it no longer appears in the listing.

    Creates a note, deletes it, then confirms it is absent from the GET /notes
    response.
    Expected: DELETE returns HTTP 200 with success=True; subsequent GET does
    not include the deleted note's id.
    """
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
