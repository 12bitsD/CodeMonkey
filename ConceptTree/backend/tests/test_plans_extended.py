"""Plans list, update, and delete API validates extended plan management operations.

This module covers listing plans (with ownership isolation and status filters),
renaming plans, and deleting plans — complementing the basic CRUD in
test_plans_crud.py. Key scenarios:
1. A fresh user has an empty plan list.
2. Each user sees only their own plans (data isolation).
3. Filtering by status=active or status=archived works correctly after archiving.
4. A plan's title can be updated by its owner; non-owners are rejected (HTTP 403).
5. A plan can be deleted by its owner; a subsequent list confirms removal.

Primary reader: a developer debugging plan listing, filtering logic, or
permission enforcement for update and delete operations.
"""


def test_get_plans_empty(client, auth_headers_a):
    """A user with no plans receives an empty list, not an error.

    Expected: HTTP 200, success=True, data=[].
    """
    resp = client.get("/api/plans", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []


def test_get_plans_returns_user_plans_only(client, auth_headers_a, auth_headers_b):
    """Each user can only see their own plans — data isolation is enforced.

    User A creates one plan, user B creates another. When user A lists their
    plans, only user A's plan appears.
    Expected: HTTP 200, exactly 1 plan with user A's title.
    """
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "list_n1",
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
        "targetNodeId": "list_n1",
    }
    client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_data["title"] = "用户B的计划"
    plan_data["nodes"][0]["id"] = "list_n2"
    plan_data["nodes"][0]["isTarget"] = True
    plan_data["targetNodeId"] = "list_n2"
    client.post("/api/plans", json=plan_data, headers=auth_headers_b)

    resp = client.get("/api/plans", headers=auth_headers_a)
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "用户A的计划"


def test_get_plans_filter_active(client, auth_headers_a):
    """Filtering by status=active excludes archived plans from the response.

    Creates a plan, archives it, then filters for active plans — the archived
    plan must not appear.
    Expected: HTTP 200, success=True, empty data list.
    """
    plan_data = {
        "title": "进行中的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "active_n1",
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
        "targetNodeId": "active_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)

    resp = client.get("/api/plans?status=active", headers=auth_headers_a)
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 0


def test_get_plans_filter_archived(client, auth_headers_a):
    """Filtering by status=archived returns only archived plans.

    Creates and archives a plan, then verifies the archived filter returns it.
    Expected: HTTP 200, success=True, exactly 1 plan in the list.
    """
    plan_data = {
        "title": "待归档计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "arch_filter_n1",
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
        "targetNodeId": "arch_filter_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)

    resp = client.get("/api/plans?status=archived", headers=auth_headers_a)
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1


def test_update_plan_title(client, auth_headers_a):
    """A plan owner can rename their plan and the new title is returned.

    Expected: HTTP 200, success=True, data.title equals the new title string.
    """
    plan_data = {
        "title": "原标题",
        "originalInput": "input",
        "nodes": [
            {
                "id": "update_title_n1",
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
        "targetNodeId": "update_title_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}",
        json={"title": "新标题"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == "新标题"


def test_update_plan_not_found(client, auth_headers_a):
    """Renaming a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put(
        "/api/plans/nonexistent",
        json={"title": "新标题"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_plan_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot rename a plan owned by user A.

    Plan ownership is enforced: only the creator may update plan metadata.
    Expected: HTTP 403.
    """
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "update_other_n1",
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
        "targetNodeId": "update_other_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}",
        json={"title": "被B修改"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_delete_plan_success(client, auth_headers_a):
    """A plan owner can delete their plan and it no longer appears in the list.

    Creates a plan, deletes it, then verifies it is absent from the GET /plans
    response.
    Expected: DELETE returns HTTP 200 with success=True; subsequent list does
    not contain the deleted plan's id.
    """
    plan_data = {
        "title": "待删除计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "delete_plan_n1",
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
        "targetNodeId": "delete_plan_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.delete(f"/api/plans/{plan_id}", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    get_resp = client.get("/api/plans", headers=auth_headers_a)
    plans = get_resp.json()["data"]
    assert not any(p["id"] == plan_id for p in plans)


def test_delete_plan_not_found(client, auth_headers_a):
    """Deleting a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.delete("/api/plans/nonexistent", headers=auth_headers_a)
    assert resp.status_code == 404
