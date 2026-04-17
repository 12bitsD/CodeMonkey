from contextlib import contextmanager

from psycopg2 import OperationalError

import routers.graph as graph_router


def test_search_node_resources_persists_cache(client, auth_headers_a, monkeypatch):
    plan_data = {
        "title": "Neural Networks",
        "originalInput": "input",
        "nodes": [
            {
                "id": "resource-node",
                "name": "反向传播",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [
                    {
                        "name": "反向传播算法详解",
                        "url": "https://existing.example.com",
                        "reason": "原始推荐资源",
                    }
                ],
                "isTarget": True,
                "domain": "coding",
            }
        ],
        "edges": [],
        "targetNodeId": "resource-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_resource-node"

    class FakeSearchService:
        async def search(self, query, max_results=None):
            assert "反向传播" in query
            return [
                {
                    "title": "Backpropagation tutorial",
                    "url": "https://example.com/backprop",
                    "snippet": "系统讲解反向传播的数学原理",
                    "source": "example.com",
                },
                {
                    "title": "Backpropagation tutorial duplicate",
                    "url": "https://existing.example.com",
                    "snippet": "应当被去重",
                    "source": "existing.example.com",
                },
            ]

    class FakeAIService:
        async def summarize_resource_results(self, node_name, query, results):
            assert node_name == "反向传播"
            return {
                "https://example.com/backprop": "系统讲解反向传播的核心推导过程",
            }

    monkeypatch.setattr(
        graph_router,
        "get_search_service",
        lambda: FakeSearchService(),
    )
    monkeypatch.setattr(
        graph_router,
        "get_ai_service",
        lambda: FakeAIService(),
    )

    resp = client.post(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}/search-resources",
        json={},
        headers=auth_headers_a,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["resourcesAdded"] == 1
    assert body["data"]["resourceSearchCache"]["items"][0]["source"] == "web_search"
    assert (
        body["data"]["resourceSearchCache"]["items"][0]["reason"]
        == "系统讲解反向传播的核心推导过程"
    )

    graph = client.get(f"/api/plans/{plan_id}/graph", headers=auth_headers_a)
    assert graph.status_code == 200
    node = graph.json()["data"]["nodes"][0]
    assert node["resourceSearchCache"]["items"][0]["url"] == "https://example.com/backprop"


def test_search_node_resources_requires_owner(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "Forbidden",
        "originalInput": "input",
        "nodes": [
            {
                "id": "resource-node",
                "name": "梯度下降",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "coding",
            }
        ],
        "edges": [],
        "targetNodeId": "resource-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_resource-node"

    resp = client.post(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}/search-resources",
        json={},
        headers=auth_headers_b,
    )

    assert resp.status_code == 403


def test_search_node_resources_retries_when_cache_write_connection_drops(
    client,
    auth_headers_a,
    monkeypatch,
):
    plan_data = {
        "title": "Neural Networks",
        "originalInput": "input",
        "nodes": [
            {
                "id": "resource-node",
                "name": "反向传播",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "coding",
            }
        ],
        "edges": [],
        "targetNodeId": "resource-node",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]
    stored_node_id = f"{plan_id}_resource-node"

    class FakeSearchService:
        async def search(self, query, max_results=None):
            return [
                {
                    "title": "Backpropagation tutorial",
                    "url": "https://example.com/backprop",
                    "snippet": "系统讲解反向传播的核心推导过程",
                    "source": "example.com",
                }
            ]

    class FakeAIService:
        async def summarize_resource_results(self, node_name, query, results):
            return {
                "https://example.com/backprop": "系统讲解反向传播的核心推导过程",
            }

    attempts = {"count": 0}

    class FakeWriteDb:
        def execute(self, sql, params=None):
            if "SELECT id, user_id, title FROM plans" in sql:
                return type(
                    "Cursor",
                    (),
                    {
                        "fetchone": lambda self: {
                            "id": plan_id,
                            "user_id": "u_a",
                            "title": "Neural Networks",
                        }
                    },
                )()

            if "SELECT id, name, resources, resource_search_cache" in sql:
                return type(
                    "Cursor",
                    (),
                    {
                        "fetchone": lambda self: {
                            "id": stored_node_id,
                            "name": "反向传播",
                            "resources": [],
                            "resource_search_cache": {"items": []},
                        }
                    },
                )()

            if "SELECT resources, resource_search_cache" in sql:
                return type(
                    "Cursor",
                    (),
                    {
                        "fetchone": lambda self: {
                            "resources": [],
                            "resource_search_cache": {"items": []},
                        }
                    },
                )()

            if "UPDATE nodes SET resource_search_cache" in sql:
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise OperationalError("SSL SYSCALL error: EOF detected")
                return type("Cursor", (), {"rowcount": 1})()

            return type("Cursor", (), {"fetchone": lambda self: None, "rowcount": 0})()

        def commit(self):
            return None

    @contextmanager
    def fake_get_db_context():
        yield FakeWriteDb()

    monkeypatch.setattr(graph_router, "get_search_service", lambda: FakeSearchService())
    monkeypatch.setattr(graph_router, "get_ai_service", lambda: FakeAIService())
    monkeypatch.setattr(graph_router, "get_db_context", fake_get_db_context)
    monkeypatch.setattr(
        graph_router,
        "_ensure_resource_search_cache_column",
        lambda db: None,
    )

    resp = client.post(
        f"/api/plans/{plan_id}/nodes/{stored_node_id}/search-resources",
        json={},
        headers=auth_headers_a,
    )

    assert resp.status_code == 200
    assert attempts["count"] == 2
    assert resp.json()["data"]["resourcesAdded"] == 1
