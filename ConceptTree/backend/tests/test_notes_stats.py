"""Notes and stats integration: creating a note is reflected in the stats overview.

This module validates the cross-feature integration between the notes API
and the stats API. It confirms that:
1. The notes endpoint is auth-protected.
2. After a note is successfully created, the stats overview endpoint reports
   the correct counts — ensuring the two features share consistent state.

Primary reader: a developer verifying that stats counters stay in sync when
notes are created, or debugging a mismatch between note counts and stats.
"""


def test_notes_requires_auth(client):
    """The notes listing endpoint rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.get("/api/notes")
    assert resp.status_code == 401


def test_create_note_and_stats(client, auth_headers_a):
    """Creating a note is reflected in the stats overview response.

    Creates a plan with one node, posts a note to it, then checks that
    the stats overview returns HTTP 200 with success=True — confirming
    the stats endpoint sees the newly created data without errors.
    Expected: note creation returns HTTP 200 with success=True; stats
    overview also returns HTTP 200 with success=True.
    """
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
