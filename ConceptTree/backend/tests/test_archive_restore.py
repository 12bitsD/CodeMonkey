"""Archive and restore API validates the basic plan lifecycle state transitions.

Plans can be archived (paused) and later restored (resumed). This module
covers the fundamental happy-path and auth-protection scenarios:
1. Both archive and restore endpoints require authentication.
2. A plan can be successfully archived and then successfully restored.

For edge-case scenarios (double-archive, cross-user access, skipped-node
counting), see test_archive_restore_extended.py.

Primary reader: a developer checking that the archive/restore cycle works
end-to-end, or verifying that auth guards are in place on both endpoints.
"""


def test_archive_restore_requires_auth(client):
    """Both archive and restore endpoints reject unauthenticated requests.

    Expected: both calls return HTTP 401.
    """
    resp = client.put("/api/plans/p_any/archive")
    assert resp.status_code == 401

    resp = client.put("/api/plans/p_any/restore")
    assert resp.status_code == 401


def test_archive_restore_flow(client, auth_headers_a):
    """A plan can be archived and subsequently restored without errors.

    Creates a plan, archives it (PUT /archive), then restores it (PUT /restore).
    Both operations must succeed.
    Expected: archive returns HTTP 200 with success=True; restore returns
    HTTP 200 with success=True.
    """
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
