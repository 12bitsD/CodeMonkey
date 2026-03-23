"""API Contract Tests - Validate frontend-backend API contract

This test module validates that the backend API responses match what the frontend expects.
These tests ensure consistency between frontend api.js and backend routers.

Run with: pytest tests/test_api_contract.py -v
"""

import pytest


class TestAuthContract:
    """Test /api/auth/* endpoints match frontend expectations"""

    def test_register_request_format(self, client):
        """Frontend sends: {email, password}"""
        resp = client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "user" in body["data"]
        assert "token" in body["data"]
        assert body["data"]["user"]["email"] == "test@example.com"

    def test_login_request_format(self, client):
        """Frontend sends: {email, password}
        Backend returns: {success, data: {user, token, expiresIn}}
        """
        client.post(
            "/api/auth/register",
            json={"email": "login@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "user" in data
        assert "token" in data
        assert "expiresIn" in data
        assert data["expiresIn"] == 604800

    def test_logout_requires_auth(self, client):
        """Frontend calls logout with Bearer token"""
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401


class TestUserProfileContract:
    """Test /api/user/* endpoints match frontend expectations"""

    def test_get_profile_response_format(self, client, auth_headers_a):
        """Frontend expects: {success, data: {occupation, education, programmingLevel, mathLevel, abilities, masteredKnowledge}}"""
        resp = client.get("/api/user/profile", headers=auth_headers_a)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "occupation" in data
        assert "education" in data
        assert "programmingLevel" in data
        assert "mathLevel" in data
        assert "abilities" in data
        assert "masteredKnowledge" in data

    def test_update_profile_request_format(self, client, auth_headers_a):
        """Frontend sends: {occupation, education, programmingLevel, mathLevel, abilities}"""
        resp = client.put(
            "/api/user/profile",
            headers=auth_headers_a,
            json={
                "occupation": "Engineer",
                "education": "Bachelor",
                "programmingLevel": "intermediate",
                "mathLevel": "advanced",
                "abilities": ["Python", "JavaScript"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["occupation"] == "Engineer"
        assert data["programmingLevel"] == "intermediate"


class TestPlansContract:
    """Test /api/plans/* endpoints match frontend expectations"""

    def test_list_plans_response_format(self, client, auth_headers_a):
        """Frontend expects: [{id, title, progress, total, status, lastAccess, createdAt}]"""
        resp = client.get("/api/plans", headers=auth_headers_a)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        if body["data"]:
            plan = body["data"][0]
            assert "id" in plan
            assert "title" in plan
            assert "progress" in plan
            assert "total" in plan
            assert "status" in plan
            assert "lastAccess" in plan
            assert "createdAt" in plan

    def test_create_plan_request_format(self, client, auth_headers_a):
        """Frontend sends: {title, originalInput, targetNodeId, nodes, edges}"""
        plan_data = {
            "title": "Test Plan",
            "originalInput": "I want to learn Python",
            "targetNodeId": "n1",
            "nodes": [
                {
                    "id": "n1",
                    "name": "Python Basics",
                    "status": "unlearned",
                    "x": 100,
                    "y": 100,
                    "isTarget": True,
                }
            ],
            "edges": [],
        }
        resp = client.post("/api/plans", headers=auth_headers_a, json=plan_data)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "id" in data
        assert data["title"] == "Test Plan"

    def test_update_plan_request_format(self, client, auth_headers_a):
        """Frontend sends: {title} (only title field)"""
        create_resp = client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Original Title",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
            },
        )
        plan_id = create_resp.json()["data"]["id"]

        resp = client.put(
            f"/api/plans/{plan_id}",
            headers=auth_headers_a,
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["title"] == "Updated Title"


class TestGraphContract:
    """Test /api/plans/{id}/graph and related endpoints match frontend expectations"""

    def test_get_graph_response_format(self, client, auth_headers_a):
        """Frontend expects: {planId, title, nodes, edges}
        Nodes have: {id, name, status, x, y, why, what, mastery, prompt, resources, isTarget}
        Edges have: {from_node, to_node} (frontend converts to {from, to})
        """
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Graph Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
            },
        )
        resp = client.get("/api/plans/p_1/graph", headers=auth_headers_a)
        if resp.status_code == 404:
            resp = client.get("/api/plans/", headers=auth_headers_a)
            plan_id = resp.json()["data"][0]["id"]
            resp = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "planId" in data
        assert "title" in data
        assert "nodes" in data
        assert "edges" in data

        if data["nodes"]:
            node = data["nodes"][0]
            assert "id" in node
            assert "name" in node
            assert "status" in node
            assert "isTarget" in node

        if data["edges"]:
            edge = data["edges"][0]
            assert "from_node" in edge
            assert "to_node" in edge

    def test_update_node_status_request_format(self, client, auth_headers_a):
        """Frontend sends: {status}"""
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Status Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
            },
        )
        resp = client.get("/api/plans/", headers=auth_headers_a)
        plan_id = resp.json()["data"][0]["id"]

        resp = client.put(
            f"/api/plans/{plan_id}/nodes/n1/status",
            headers=auth_headers_a,
            json={"status": "learned"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["nodeId"] == "n1"
        assert data["status"] == "learned"

    def test_update_node_position_request_format(self, client, auth_headers_a):
        """Frontend sends: {x, y}"""
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Position Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
            },
        )
        resp = client.get("/api/plans/", headers=auth_headers_a)
        plan_id = resp.json()["data"][0]["id"]

        resp = client.put(
            f"/api/plans/{plan_id}/nodes/n1/position",
            headers=auth_headers_a,
            json={"x": 250, "y": 150},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["nodeId"] == "n1"
        assert data["x"] == 250
        assert data["y"] == 150


class TestNotesContract:
    """Test /api/notes/* endpoints match frontend expectations"""

    def test_list_notes_response_format(self, client, auth_headers_a):
        """Frontend expects: {notes: [...], total: int}
        Each note: {id, planId, planTitle, nodeId, nodeName, content, date, createdAt}
        """
        resp = client.get("/api/notes", headers=auth_headers_a)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "notes" in body["data"]
        assert "total" in body["data"]
        assert isinstance(body["data"]["notes"], list)

    def test_create_note_request_format(self, client, auth_headers_a):
        """Frontend sends: {planId, nodeId, content}"""
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Note Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
            },
        )
        resp = client.get("/api/plans/", headers=auth_headers_a)
        plan_id = resp.json()["data"][0]["id"]

        resp = client.post(
            "/api/notes",
            headers=auth_headers_a,
            json={"planId": plan_id, "nodeId": "n1", "content": "Test note content"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "id" in data
        assert data["content"] == "Test note content"


class TestAIContract:
    """Test /api/ai/* endpoints match frontend expectations"""

    def test_parse_goal_request_format(self, client, auth_headers_a):
        """Frontend sends: {input, userBackground: {occupation, education, programmingLevel, mathLevel, abilities, masteredKnowledge}}"""
        resp = client.post(
            "/api/ai/parse-goal",
            headers=auth_headers_a,
            json={
                "input": "I want to learn deep learning with Python experience",
                "userBackground": {
                    "occupation": "Engineer",
                    "education": "Bachelor",
                    "programmingLevel": "intermediate",
                    "mathLevel": "beginner",
                    "abilities": ["Python"],
                    "masteredKnowledge": ["variables"],
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "interpretation" in data
        assert "backgroundSummary" in data
        assert "suggestedNodeCount" in data
        assert "shouldSplit" in data

    def test_generate_graph_request_format(self, client, auth_headers_a):
        """Frontend sends: {input, interpretation, userBackground}"""
        resp = client.post(
            "/api/ai/generate-graph",
            headers=auth_headers_a,
            json={
                "input": "I want to learn deep learning",
                "interpretation": "理解深度学习的基本概念和反向传播算法",
                "userBackground": {
                    "occupation": "Engineer",
                    "education": "Bachelor",
                    "programmingLevel": "intermediate",
                    "mathLevel": "beginner",
                    "abilities": ["Python"],
                    "masteredKnowledge": ["variables"],
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "interpretation" in data
        assert "nodes" in data
        assert "edges" in data
        assert "targetNodeId" in data

    def test_clarify_goal_request_format(self, client, auth_headers_a):
        """Frontend sends: {originalGoal, newGoal, planId?}"""
        resp = client.post(
            "/api/ai/clarify-goal",
            headers=auth_headers_a,
            json={
                "originalGoal": "I want to learn deep learning",
                "newGoal": "I want to learn deep learning for computer vision",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "interpretation" in data
        assert "isLargeChange" in data
        assert "suggestion" in data
        assert "reason" in data

    def test_recommend_next_request_format(self, client, auth_headers_a):
        """Frontend sends: {planId}
        Frontend expects: {recommended_node_id, reason} (snake_case from alias)
        """
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Recommend Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": False,
                    },
                    {
                        "id": "n2",
                        "name": "N2",
                        "status": "unlearned",
                        "x": 100,
                        "y": 0,
                        "isTarget": True,
                    },
                ],
                "edges": [{"from_node": "n1", "to_node": "n2"}],
            },
        )
        resp = client.get("/api/plans/", headers=auth_headers_a)
        plan_id = resp.json()["data"][0]["id"]

        resp = client.post(
            "/api/ai/recommend-next",
            headers=auth_headers_a,
            json={"planId": plan_id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "recommended_node_id" in data
        assert "reason" in data


class TestStatsContract:
    """Test /api/stats/* endpoints match frontend expectations"""

    def test_overview_response_format(self, client, auth_headers_a):
        """Frontend expects: {summary: {completedPlans, activePlans, masteredKnowledge, totalNotes}, thisWeek: {completedNodes, newNotes}}"""
        resp = client.get("/api/stats/overview", headers=auth_headers_a)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "summary" in data
        assert "thisWeek" in data
        summary = data["summary"]
        assert "completedPlans" in summary
        assert "activePlans" in summary
        assert "masteredKnowledge" in summary
        assert "totalNotes" in summary
        this_week = data["thisWeek"]
        assert "completedNodes" in this_week
        assert "newNotes" in this_week

    def test_distribution_response_format(self, client, auth_headers_a):
        """Frontend expects: {distribution: [{domain, count, percentage}], total: int}"""
        resp = client.get("/api/stats/distribution", headers=auth_headers_a)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "distribution" in data
        assert "total" in data
        assert isinstance(data["distribution"], list)
        if data["distribution"]:
            item = data["distribution"][0]
            assert "domain" in item
            assert "count" in item
            assert "percentage" in item


class TestEdgeFieldContract:
    """Test Edge field naming consistency"""

    def test_edge_from_backend_uses_snake_case(self, client, auth_headers_a):
        """Backend returns edges with from_node/to_node (snake_case)
        Frontend converts to from/to (camelCase) via mapEdgesFromBackend
        """
        client.post(
            "/api/plans",
            headers=auth_headers_a,
            json={
                "title": "Edge Test",
                "originalInput": "input",
                "targetNodeId": "n1",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "N1",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": False,
                    },
                    {
                        "id": "n2",
                        "name": "N2",
                        "status": "unlearned",
                        "x": 100,
                        "y": 0,
                        "isTarget": True,
                    },
                ],
                "edges": [{"from_node": "n1", "to_node": "n2"}],
            },
        )
        resp = client.get("/api/plans/", headers=auth_headers_a)
        plan_id = resp.json()["data"][0]["id"]
        resp = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)

        edges = resp.json()["data"]["edges"]
        assert len(edges) == 1
        edge = edges[0]
        assert "from_node" in edge
        assert "to_node" in edge
        assert edge["from_node"] == "n1"
        assert edge["to_node"] == "n2"


class TestUserBackgroundFieldContract:
    """Test userBackground field naming consistency"""

    def test_parse_goal_accepts_all_background_fields(self, client, auth_headers_a):
        """Frontend sends all 6 fields in userBackground
        Backend should accept: occupation, education, programmingLevel, mathLevel, abilities, masteredKnowledge
        """
        resp = client.post(
            "/api/ai/parse-goal",
            headers=auth_headers_a,
            json={
                "input": "I want to learn deep learning with 5 years Python experience",
                "userBackground": {
                    "occupation": "Software Engineer",
                    "education": "Master's",
                    "programmingLevel": "advanced",
                    "mathLevel": "intermediate",
                    "abilities": ["Python", "TensorFlow", "PyTorch"],
                    "masteredKnowledge": ["Linear Algebra", "Statistics"],
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_generate_graph_accepts_all_background_fields(self, client, auth_headers_a):
        """Frontend sends all 6 fields in userBackground for generate-graph too"""
        resp = client.post(
            "/api/ai/generate-graph",
            headers=auth_headers_a,
            json={
                "input": "I want to learn deep learning",
                "interpretation": "理解深度学习概念",
                "userBackground": {
                    "occupation": "Software Engineer",
                    "education": "Master's",
                    "programmingLevel": "advanced",
                    "mathLevel": "intermediate",
                    "abilities": ["Python", "TensorFlow"],
                    "masteredKnowledge": ["Linear Algebra"],
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
