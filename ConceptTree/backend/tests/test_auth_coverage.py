"""Auth Coverage Tests - Verify 401 for unauthenticated and 403 for cross-user access.

Covers plans, graph, notes, and AI endpoints.
"""

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

_PLAN_BODY = {
    "title": "Auth Test Plan",
    "originalInput": "test",
    "targetNodeId": "n1",
    "nodes": [
        {
            "id": "n1",
            "name": "节点1",
            "status": "unlearned",
            "x": 0,
            "y": 0,
            "isTarget": True,
        }
    ],
    "edges": [],
}


def _create_plan(client, headers):
    resp = client.post("/api/plans", json=_PLAN_BODY, headers=headers)
    assert resp.status_code == 200, resp.json()
    return resp.json()["data"]["id"]


# ── 401: unauthenticated ───────────────────────────────────────────────────────


class TestUnauthenticatedReturns401:
    """All protected endpoints must return 401 with no token."""

    def test_plans_list(self, client):
        assert client.get("/api/plans").status_code == 401

    def test_plans_create(self, client):
        assert client.post("/api/plans", json=_PLAN_BODY).status_code == 401

    def test_plans_update(self, client):
        assert client.put("/api/plans/p_xxx", json={"title": "x"}).status_code == 401

    def test_plans_delete(self, client):
        assert client.delete("/api/plans/p_xxx").status_code == 401

    def test_plans_archive(self, client):
        assert client.put("/api/plans/p_xxx/archive").status_code == 401

    def test_plans_restore(self, client):
        assert client.put("/api/plans/p_xxx/restore").status_code == 401

    def test_graph_get(self, client):
        assert client.get("/api/plans/p_xxx/graph").status_code == 401

    def test_graph_node_status(self, client):
        assert (
            client.put(
                "/api/plans/p_xxx/nodes/n1/status", json={"status": "learned"}
            ).status_code
            == 401
        )

    def test_graph_node_position(self, client):
        assert (
            client.put(
                "/api/plans/p_xxx/nodes/n1/position", json={"x": 0, "y": 0}
            ).status_code
            == 401
        )

    def test_notes_list(self, client):
        assert client.get("/api/notes").status_code == 401

    def test_notes_create(self, client):
        assert (
            client.post(
                "/api/notes", json={"planId": "p", "nodeId": "n", "content": "c"}
            ).status_code
            == 401
        )

    def test_user_profile_get(self, client):
        assert client.get("/api/user/profile").status_code == 401

    def test_user_profile_update(self, client):
        assert client.put("/api/user/profile", json={}).status_code == 401

    def test_ai_parse_goal(self, client):
        assert (
            client.post("/api/ai/parse-goal", json={"input": "test"}).status_code == 401
        )

    def test_ai_generate_graph(self, client):
        assert (
            client.post(
                "/api/ai/generate-graph",
                json={"input": "test", "interpretation": "test"},
            ).status_code
            == 401
        )

    def test_ai_clarify_goal(self, client):
        assert (
            client.post(
                "/api/ai/clarify-goal",
                json={"originalGoal": "a", "newGoal": "b"},
            ).status_code
            == 401
        )

    def test_ai_recommend_next(self, client):
        assert (
            client.post(
                "/api/ai/recommend-next", json={"planId": "p_xxx"}
            ).status_code
            == 401
        )

    def test_stats_overview(self, client):
        assert client.get("/api/stats/overview").status_code == 401

    def test_stats_distribution(self, client):
        assert client.get("/api/stats/distribution").status_code == 401

    def test_auth_logout(self, client):
        assert client.post("/api/auth/logout").status_code == 401


# ── 403: cross-user isolation ─────────────────────────────────────────────────


class TestCrossUserReturns403:
    """User B must not access or modify User A's resources."""

    def test_plans_update_by_other_user(self, client, auth_headers_a, auth_headers_b):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.put(
            f"/api/plans/{plan_id}", json={"title": "hijack"}, headers=auth_headers_b
        )
        assert resp.status_code == 403

    def test_plans_delete_by_other_user(self, client, auth_headers_a, auth_headers_b):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.delete(f"/api/plans/{plan_id}", headers=auth_headers_b)
        assert resp.status_code == 403

    def test_plans_archive_by_other_user(self, client, auth_headers_a, auth_headers_b):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.put(f"/api/plans/{plan_id}/archive", headers=auth_headers_b)
        assert resp.status_code == 403

    def test_graph_get_by_other_user(self, client, auth_headers_a, auth_headers_b):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_b)
        assert resp.status_code == 403

    def test_graph_node_status_by_other_user(
        self, client, auth_headers_a, auth_headers_b
    ):
        plan_id = _create_plan(client, auth_headers_a)
        node_id = f"{plan_id}_n1"
        resp = client.put(
            f"/api/plans/{plan_id}/nodes/{node_id}/status",
            json={"status": "learned"},
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    def test_graph_node_position_by_other_user(
        self, client, auth_headers_a, auth_headers_b
    ):
        plan_id = _create_plan(client, auth_headers_a)
        node_id = f"{plan_id}_n1"
        resp = client.put(
            f"/api/plans/{plan_id}/nodes/{node_id}/position",
            json={"x": 100, "y": 100},
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    def test_notes_create_on_other_users_plan(
        self, client, auth_headers_a, auth_headers_b
    ):
        plan_id = _create_plan(client, auth_headers_a)
        node_id = f"{plan_id}_n1"
        resp = client.post(
            "/api/notes",
            json={"planId": plan_id, "nodeId": node_id, "content": "stolen"},
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    def test_ai_clarify_goal_with_other_users_plan(
        self, client, auth_headers_a, auth_headers_b
    ):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.post(
            "/api/ai/clarify-goal",
            json={
                "originalGoal": "学习Python基础",
                "newGoal": "学习Python数据分析",
                "planId": plan_id,
            },
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    def test_ai_recommend_next_with_other_users_plan(
        self, client, auth_headers_a, auth_headers_b
    ):
        plan_id = _create_plan(client, auth_headers_a)
        resp = client.post(
            "/api/ai/recommend-next",
            json={"planId": plan_id},
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    def test_plans_list_isolation(self, client, auth_headers_a, auth_headers_b):
        """User B must not see User A's plans in the list."""
        _create_plan(client, auth_headers_a)
        resp = client.get("/api/plans", headers=auth_headers_b)
        assert resp.status_code == 200
        assert resp.json()["data"] == []
