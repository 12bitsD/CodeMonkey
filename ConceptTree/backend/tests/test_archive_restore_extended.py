"""Archive and restore edge-case tests: idempotency, ownership, and progress counting.

This module extends test_archive_restore.py with scenarios that verify
correct behaviour in unusual but realistic situations:
1. Double-archiving an already-archived plan returns HTTP 400 (idempotency guard).
2. Restoring an already-active plan returns HTTP 400 (idempotency guard).
3. Archiving or restoring a non-existent plan returns HTTP 404.
4. Another user cannot archive or restore a plan they don't own (HTTP 403).
5. When archiving or restoring, the progress 'total' field excludes skipped
   nodes from the denominator (business rule: skipped ≠ incomplete).

Primary reader: a developer debugging idempotency errors, cross-user
isolation on archive/restore, or the skipped-node counting logic.
"""


def test_archive_plan_already_archived(client, auth_headers_a):
    """Archiving an already-archived plan returns HTTP 400.

    A plan that is already in 'archived' status cannot be archived again.
    Expected: first archive returns HTTP 200; second archive returns HTTP 400.
    """
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
    """Restoring an already-active plan returns HTTP 400.

    A plan that is in 'active' status (never archived) cannot be restored.
    Expected: HTTP 400.
    """
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
    """Archiving a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put("/api/plans/nonexistent/archive", headers=auth_headers_a)
    assert resp.status_code == 404


def test_restore_plan_not_found(client, auth_headers_a):
    """Restoring a non-existent plan returns HTTP 404.

    Expected: HTTP 404.
    """
    resp = client.put("/api/plans/nonexistent/restore", headers=auth_headers_a)
    assert resp.status_code == 404


def test_archive_plan_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    """User B cannot archive a plan owned by user A.

    Plan ownership is enforced: archiving is restricted to the plan creator.
    Expected: HTTP 403.
    """
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
    """User B cannot restore an archived plan owned by user A.

    Plan ownership is enforced on the restore endpoint as well.
    Expected: HTTP 403.
    """
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


def test_archive_plan_excludes_skipped_from_total(client, auth_headers_a):
    """The archive response's 'total' field excludes skipped nodes.

    Creates a 3-node plan (1 learned, 1 skipped, 1 unlearned) and archives it.
    The response total should be 2, not 3 — confirming that skipped nodes are
    not counted as 'to be completed' in the progress denominator.
    Expected: HTTP 200, data.total=2 (learned + unlearned, skipped excluded).
    """
    plan_data = {
        "title": "跳过节点口径测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "skip_n1",
                "name": "已学节点",
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
                "id": "skip_n2",
                "name": "跳过节点",
                "status": "skipped",
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
            {
                "id": "skip_n3",
                "name": "未学节点",
                "status": "unlearned",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
        ],
        "edges": [{"from_node": "skip_n1", "to_node": "skip_n2"}],
        "targetNodeId": "skip_n3",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 2


def test_restore_plan_excludes_skipped_from_total(client, auth_headers_a):
    """The restore response's 'total' and 'progress' fields exclude skipped nodes.

    Creates a 2-node plan (1 learned, 1 skipped), archives then restores it.
    The restore response should show total=1 (only the learned node counts) and
    progress=1 (the learned node is already done).
    Expected: HTTP 200, data.total=1, data.progress=1.
    """
    plan_data = {
        "title": "恢复跳过节点口径测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "rest_skip_n1",
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
                "id": "rest_skip_n2",
                "name": "节点B",
                "status": "skipped",
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
        ],
        "edges": [],
        "targetNodeId": "rest_skip_n2",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_a)

    resp = client.put(f"/api/plans/{plan_id}/restore", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["progress"] == 1
