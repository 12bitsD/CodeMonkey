def _create_plan(client, auth_headers_a):
    payload = {
        "title": "计划管理测试",
        "originalInput": "我想系统学习 Transformer",
        "nodes": [
            {
                "id": "pm_node_1",
                "name": "注意力机制",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "核心概念",
                "what": ["缩放点积注意力"],
                "mastery": ["能解释 QKV"],
                "prompt": "",
                "resources": [],
                "isTarget": True,
            }
        ],
        "edges": [],
        "targetNodeId": "pm_node_1",
    }
    response = client.post("/api/plans", json=payload, headers=auth_headers_a)
    assert response.status_code == 200
    return response.json()["data"]


def test_create_plan_returns_management_defaults(client, auth_headers_a):
    created = _create_plan(client, auth_headers_a)

    assert created["status"] == "active"
    assert created["studyFrequency"] == "flexible"
    assert created["studyDaysPerWeek"] == 3
    assert created["reminderEnabled"] is False
    assert created["archivedReason"] is None
    assert created["startDate"] is not None


def test_create_plan_accepts_ai_generated_resources(client, auth_headers_a):
    payload = {
        "title": "AI generated graph with resources",
        "originalInput": "learn graph generation",
        "nodes": [
            {
                "id": "ai_node_1",
                "name": "Graph Basics",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "foundation",
                "what": ["nodes", "edges"],
                "mastery": ["draw a graph"],
                "prompt": "Explain graph basics",
                "resources": [
                    {
                        "name": "Graph guide",
                        "url": "https://example.com/graph",
                        "reason": "AI generated resource",
                    }
                ],
                "isTarget": True,
            }
        ],
        "edges": [],
        "targetNodeId": "ai_node_1",
    }

    response = client.post("/api/plans", json=payload, headers=auth_headers_a)

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_update_plan_management_fields(client, auth_headers_a):
    created = _create_plan(client, auth_headers_a)
    plan_id = created["id"]

    response = client.put(
        f"/api/plans/{plan_id}",
        json={
            "startDate": "2026-04-18",
            "targetEndDate": "2026-05-18",
            "studyFrequency": "custom",
            "studyDaysPerWeek": 4,
            "reminderEnabled": True,
            "reminderTime": "20:30",
            "reminderTimezone": "Asia/Shanghai",
        },
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert str(data["startDate"]).startswith("2026-04-18")
    assert str(data["targetEndDate"]).startswith("2026-05-18")
    assert data["studyFrequency"] == "custom"
    assert data["studyDaysPerWeek"] == 4
    assert data["reminderEnabled"] is True
    assert data["reminderTime"] == "20:30"
    assert data["reminderTimezone"] == "Asia/Shanghai"


def test_pause_archive_restore_resume_plan(client, auth_headers_a):
    created = _create_plan(client, auth_headers_a)
    plan_id = created["id"]

    paused = client.put(f"/api/plans/{plan_id}/pause", headers=auth_headers_a)
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"

    resumed = client.put(f"/api/plans/{plan_id}/resume", headers=auth_headers_a)
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "active"

    archived = client.put(
        f"/api/plans/{plan_id}/archive",
        json={"reason": "manual"},
        headers=auth_headers_a,
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"
    assert archived.json()["data"]["archivedReason"] == "manual"

    restored = client.put(f"/api/plans/{plan_id}/restore", headers=auth_headers_a)
    assert restored.status_code == 200
    assert restored.json()["data"]["status"] == "active"
    assert restored.json()["data"]["archivedReason"] is None
