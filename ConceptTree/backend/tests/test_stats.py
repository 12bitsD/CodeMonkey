"""Stats API validates the overview and domain distribution endpoints.

The stats endpoints give learners a summary of their progress: how many plans
are active, how many nodes they've mastered, how many notes they've written,
and what subjects (domains) they've covered.

This module validates:
1. Both stats endpoints require authentication.
2. A new user with no data gets zeroed-out overview fields.
3. Creating plans and notes is reflected in the overview counts.
4. The distribution endpoint groups learned nodes by domain and returns the
   correct per-domain counts.
5. The overview response shape matches the fields expected by the frontend.

Primary reader: a developer debugging incorrect stat counts, adding a new
stat field, or verifying the frontend contract for the overview response.
"""


def test_stats_overview_requires_auth(client):
    """The stats overview endpoint rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.get("/api/stats/overview")
    assert resp.status_code == 401


def test_stats_overview_new_user(client, auth_headers_a):
    """A new user with no activity gets all-zero stats in a valid response.

    Verifies the overview fields are present and initialised to 0 rather
    than raising an error or returning None.
    Expected: HTTP 200, success=True, completedPlans=0, activePlans=0,
    masteredNodes=0, totalNotes=0, thisWeek present.
    """
    resp = client.get("/api/stats/overview", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "thisWeek" in body["data"]
    assert body["data"]["completedPlans"] == 0
    assert body["data"]["activePlans"] == 0
    assert body["data"]["masteredNodes"] == 0
    assert body["data"]["totalNotes"] == 0


def test_stats_overview_with_data(client, auth_headers_a):
    """After creating a plan and a note, overview counts are updated correctly.

    Creates a 2-node plan and one note. Verifies that activePlans=1 and
    totalNotes=1 in the overview response.
    Expected: HTTP 200, activePlans=1, totalNotes=1.
    """
    plan_data = {
        "title": "统计测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "stats_n1",
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
                "id": "stats_n2",
                "name": "节点B",
                "status": "learned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "数学",
            },
        ],
        "edges": [{"from_node": "stats_n1", "to_node": "stats_n2"}],
        "targetNodeId": "stats_n2",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    client.post(
        "/api/notes",
        json={"planId": plan_id, "nodeId": "stats_n1", "content": "笔记内容"},
        headers=auth_headers_a,
    )

    resp = client.get("/api/stats/overview", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["activePlans"] == 1
    assert body["data"]["totalNotes"] == 1


def test_stats_distribution_requires_auth(client):
    """The stats distribution endpoint rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.get("/api/stats/distribution")
    assert resp.status_code == 401


def test_stats_distribution_empty(client, auth_headers_a):
    """A new user with no learned nodes gets an empty distribution.

    Expected: HTTP 200, success=True, distribution=[], total=0.
    """
    resp = client.get("/api/stats/distribution", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["distribution"] == []
    assert body["data"]["total"] == 0


def test_stats_distribution_with_learned_nodes(client, auth_headers_a):
    """Learned nodes are grouped by domain in the distribution response.

    Creates a 3-node plan with 2 '编程' nodes and 1 '数学' node (all learned),
    then verifies that the distribution shows 2 entries — one per domain —
    with the correct per-domain counts and a total of 3.
    Expected: total=3, distribution has 2 entries, '编程' count=2, '数学' count=1.
    """
    plan_data = {
        "title": "分布测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "dist_n1",
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
                "id": "dist_n2",
                "name": "节点B",
                "status": "learned",
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
            {
                "id": "dist_n3",
                "name": "节点C",
                "status": "learned",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "数学",
            },
        ],
        "edges": [],
        "targetNodeId": "dist_n2",
    }
    client.post("/api/plans", json=plan_data, headers=auth_headers_a)

    resp = client.get("/api/stats/distribution", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["total"] == 3

    dist = body["data"]["distribution"]
    assert len(dist) == 2

    prog_domain = next((d for d in dist if d["domain"] == "编程"), None)
    assert prog_domain is not None
    assert prog_domain["count"] == 2

    math_domain = next((d for d in dist if d["domain"] == "数学"), None)
    assert math_domain is not None
    assert math_domain["count"] == 1


def test_stats_overview_response_structure_matches_frontend(client, auth_headers_a):
    """The overview response contains all fields required by the frontend.

    This test pins the exact field names expected by the frontend to prevent
    a silent contract break if a field is renamed on the backend.
    Expected: completedPlans, activePlans, masteredNodes, totalNotes, thisWeek,
    thisWeek.completedNodes, thisWeek.newNotes are all present in the response.
    """
    resp = client.get("/api/stats/overview", headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "completedPlans" in body["data"]
    assert "activePlans" in body["data"]
    assert "masteredNodes" in body["data"]
    assert "totalNotes" in body["data"]
    assert "thisWeek" in body["data"]
    assert "completedNodes" in body["data"]["thisWeek"]
    assert "newNotes" in body["data"]["thisWeek"]
