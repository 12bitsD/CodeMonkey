"""
Sprint 2 Feature Tests
======================
Covers:
  F1  - learning_purpose 存储与传递
  F3  - phase / phase_order / depth_level 字段存储与返回
  F5  - generate-graph SSE 流式端点格式与 learning_purpose 传递
  CFG - generate_graph.json 配置正确性（无 DB）
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import psycopg2
import psycopg2.extras
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sql_utils import split_sql_statements

# ─── helpers ─────────────────────────────────────────────────────────────────

_NODE_PAYLOAD_BASE = dict(
    status="unlearned",
    x=0.0,
    y=0.0,
    why="用于理解目标",
    what=["内容1"],
    mastery=["掌握标准1"],
    prompt="学习提示",
    resources=[],
)


def _node(
    node_id: str,
    name: str,
    *,
    is_target: bool = False,
    phase: str = "核心",
    phase_order: int = 2,
    depth_level: int = 3,
    domain: str = "编程",
) -> dict:
    return {
        "id": node_id,
        "name": name,
        "isTarget": is_target,
        "phase": phase,
        "phase_order": phase_order,
        "depth_level": depth_level,
        "domain": domain,
        **_NODE_PAYLOAD_BASE,
    }


def _plan_payload(
    *,
    learning_purpose: str = "apply",
    nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
) -> dict:
    nodes = nodes or [
        _node("n1", "基础知识", phase="地基", phase_order=1, depth_level=3),
        _node("n2", "核心概念", is_target=True, phase="核心", phase_order=2, depth_level=3),
    ]
    edges = edges or [{"from_node": "n1", "to_node": "n2"}]
    return {
        "title": "测试计划",
        "originalInput": "我想学深度学习",
        "nodes": nodes,
        "edges": edges,
        "targetNodeId": "n2",
        "learning_purpose": learning_purpose,
    }


# ─── Section 1: Model structure (no DB) ──────────────────────────────────────


@pytest.mark.no_db
class TestModelStructure:
    """NodeBase / GraphNode / PlanCreateRequest 新增字段校验"""

    def test_node_base_has_phase_fields(self):
        from models import NodeBase, NodeStatus

        node = NodeBase(
            id="n1",
            name="测试",
            status=NodeStatus.unlearned,
            x=0.0,
            y=0.0,
            phase="核心",
            phase_order=2,
            depth_level=3,
        )
        assert node.phase == "核心"
        assert node.phase_order == 2
        assert node.depth_level == 3

    def test_node_base_phase_defaults(self):
        from models import NodeBase, NodeStatus

        node = NodeBase(id="n1", name="测试", status=NodeStatus.unlearned, x=0.0, y=0.0)
        assert node.phase is None
        assert node.phase_order == 0
        assert node.depth_level == 2

    def test_graph_node_has_phase_fields(self):
        from models import GraphNode

        gn = GraphNode(
            id="n1",
            name="测试",
            why="why",
            what=["a"],
            mastery=["b"],
            prompt="p",
            phase="地基",
            phase_order=1,
            depth_level=4,
        )
        assert gn.phase == "地基"
        assert gn.phase_order == 1
        assert gn.depth_level == 4

    def test_plan_create_request_has_learning_purpose(self):
        from models import NodeData, NodeStatus, PlanCreateRequest, Resource

        req = PlanCreateRequest(
            title="t",
            originalInput="i",
            nodes=[
                NodeData(
                    id="n1",
                    name="A",
                    status=NodeStatus.unlearned,
                    x=0.0,
                    y=0.0,
                    isTarget=True,
                )
            ],
            edges=[],
            targetNodeId="n1",
            learning_purpose="master",
        )
        assert req.learning_purpose == "master"

    def test_plan_create_request_default_learning_purpose(self):
        from models import NodeData, NodeStatus, PlanCreateRequest

        req = PlanCreateRequest(
            title="t",
            originalInput="i",
            nodes=[
                NodeData(
                    id="n1",
                    name="A",
                    status=NodeStatus.unlearned,
                    x=0.0,
                    y=0.0,
                    isTarget=True,
                )
            ],
            edges=[],
            targetNodeId="n1",
        )
        assert req.learning_purpose == "apply"


# ─── Section 2: Plans router — F1 + F3 storage ───────────────────────────────
# Uses an isolated FastAPI mini-app with a direct psycopg2 connection,
# bypassing main.py / auth.py / limiter.py to avoid the starlette GBK issue.


def _require_db_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DATABASE_URL not set — skipping DB integration tests")
    return url


def _make_plans_app(schema: str, user_id: str = "u_s2"):
    """Minimal FastAPI app with only the plans + graph routers, real DB."""
    import routers.plans as plans_router
    import routers.graph as graph_router
    from database import DbSession, get_db
    from utils.auth import get_current_user_id

    def _override_user():
        return user_id

    def _override_db():
        conn = psycopg2.connect(_require_db_url())
        try:
            with conn.cursor() as cur:
                cur.execute(f'SET search_path TO "{schema}"')
            conn.commit()
            yield DbSession(conn)
        finally:
            conn.close()

    app = FastAPI()
    app.include_router(plans_router.router)
    app.include_router(graph_router.router)
    app.dependency_overrides[get_current_user_id] = _override_user
    app.dependency_overrides[get_db] = _override_db
    return app


@pytest.fixture(scope="class")
def s2_db_schema():
    """Ephemeral schema for Section 2/3 DB tests — no main.py involved."""
    url = _require_db_url()
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    schema = f"ct_s2_{uuid.uuid4().hex[:8]}"

    conn = psycopg2.connect(url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                cur.execute(f'SET search_path TO "{schema}"')
                for stmt in split_sql_statements(schema_sql):
                    cur.execute(stmt)
                # seed a test user
                cur.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    ("u_s2", "s2@test.com", "hash_s2"),
                )
        yield schema
    finally:
        drop_conn = psycopg2.connect(url)
        try:
            with drop_conn:
                with drop_conn.cursor() as cur:
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        finally:
            drop_conn.close()
        conn.close()


@pytest.fixture()
def s2_client(s2_db_schema):
    app = _make_plans_app(s2_db_schema)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def s2_conn(s2_db_schema):
    url = _require_db_url()
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{s2_db_schema}"')
        yield conn
    finally:
        conn.close()


class TestPlanCreationSprintTwo:
    """验证 learning_purpose 和节点阶段字段写入数据库（独立 mini-app，无 starlette 编码冲突）"""

    def _create_plan(self, s2_client, purpose="apply"):
        payload = _plan_payload(learning_purpose=purpose)
        resp = s2_client.post("/api/plans", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]["id"]

    def test_create_plan_stores_learning_purpose_apply(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client, purpose="apply")
        with s2_conn.cursor() as cur:
            cur.execute("SELECT learning_purpose FROM plans WHERE id = %s", (plan_id,))
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "apply"

    def test_create_plan_stores_learning_purpose_explore(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client, purpose="explore")
        with s2_conn.cursor() as cur:
            cur.execute("SELECT learning_purpose FROM plans WHERE id = %s", (plan_id,))
            row = cur.fetchone()
        assert row[0] == "explore"

    def test_create_plan_stores_learning_purpose_master(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client, purpose="master")
        with s2_conn.cursor() as cur:
            cur.execute("SELECT learning_purpose FROM plans WHERE id = %s", (plan_id,))
            row = cur.fetchone()
        assert row[0] == "master"

    def test_create_plan_stores_node_phase(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client)
        with s2_conn.cursor() as cur:
            cur.execute(
                "SELECT name, phase FROM nodes WHERE plan_id = %s ORDER BY name",
                (plan_id,),
            )
            rows = {r[0]: r[1] for r in cur.fetchall()}
        assert rows["基础知识"] == "地基"
        assert rows["核心概念"] == "核心"

    def test_create_plan_stores_node_phase_order(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client)
        with s2_conn.cursor() as cur:
            cur.execute(
                "SELECT name, phase_order FROM nodes WHERE plan_id = %s ORDER BY name",
                (plan_id,),
            )
            rows = {r[0]: r[1] for r in cur.fetchall()}
        assert rows["基础知识"] == 1
        assert rows["核心概念"] == 2

    def test_create_plan_stores_node_depth_level(self, s2_client, s2_conn):
        plan_id = self._create_plan(s2_client)
        with s2_conn.cursor() as cur:
            cur.execute(
                "SELECT depth_level FROM nodes WHERE plan_id = %s",
                (plan_id,),
            )
            levels = [r[0] for r in cur.fetchall()]
        assert all(lvl == 3 for lvl in levels)

    def test_create_plan_missing_learning_purpose_defaults_apply(self, s2_client, s2_conn):
        """后端缺省值为 apply"""
        payload = _plan_payload()
        payload.pop("learning_purpose")
        resp = s2_client.post("/api/plans", json=payload)
        assert resp.status_code == 200
        plan_id = resp.json()["data"]["id"]
        with s2_conn.cursor() as cur:
            cur.execute("SELECT learning_purpose FROM plans WHERE id = %s", (plan_id,))
            row = cur.fetchone()
        assert row[0] == "apply"


# ─── Section 3: Graph router — F3 return ─────────────────────────────────────


class TestGraphApiSprintTwo:
    """GET /plans/{plan_id}/graph 返回节点阶段字段"""

    def _setup_plan(self, s2_client):
        payload = _plan_payload()
        resp = s2_client.post("/api/plans", json=payload)
        assert resp.status_code == 200
        return resp.json()["data"]["id"]

    def test_graph_returns_phase_on_nodes(self, s2_client):
        plan_id = self._setup_plan(s2_client)
        resp = s2_client.get(f"/api/plans/{plan_id}/graph")
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        phases = {n["name"]: n.get("phase") for n in nodes}
        assert phases.get("基础知识") == "地基"
        assert phases.get("核心概念") == "核心"

    def test_graph_returns_phase_order_on_nodes(self, s2_client):
        plan_id = self._setup_plan(s2_client)
        resp = s2_client.get(f"/api/plans/{plan_id}/graph")
        nodes = resp.json()["data"]["nodes"]
        orders = {n["name"]: n.get("phase_order") for n in nodes}
        assert orders["基础知识"] == 1
        assert orders["核心概念"] == 2

    def test_graph_returns_depth_level_on_nodes(self, s2_client):
        plan_id = self._setup_plan(s2_client)
        resp = s2_client.get(f"/api/plans/{plan_id}/graph")
        nodes = resp.json()["data"]["nodes"]
        for node in nodes:
            assert "depth_level" in node
            assert isinstance(node["depth_level"], int)

    def test_graph_nodes_without_phase_fallback_to_defaults(self, s2_client):
        """节点没有 phase 字段时返回 null / 0 / 2"""
        payload = _plan_payload()
        payload["nodes"][0].pop("phase", None)
        payload["nodes"][0].pop("phase_order", None)
        payload["nodes"][0].pop("depth_level", None)
        resp = s2_client.post("/api/plans", json=payload)
        plan_id = resp.json()["data"]["id"]

        resp = s2_client.get(f"/api/plans/{plan_id}/graph")
        nodes = resp.json()["data"]["nodes"]
        plain_node = next(n for n in nodes if n["name"] == "基础知识")
        assert plain_node["phase_order"] == 0
        assert plain_node["depth_level"] == 2


# ─── Section 4: AI router — F5 SSE streaming ─────────────────────────────────


@pytest.mark.no_db
class TestSSEEndpointSprintTwo:
    """generate-graph 端点 SSE 格式与 learning_purpose 传递"""

    def _build_fake_graph_result(self, learning_purpose: str = "apply"):
        from models import GenerateGraphAIResult, GenerateGraphResponse, GraphNode

        node = GraphNode(
            id="n1",
            name="核心概念",
            why="核心原因",
            what=["知识点A"],
            mastery=["掌握标准"],
            prompt="提示词",
            isTarget=True,
            phase="核心",
            phase_order=2,
            depth_level=3,
        )
        return GenerateGraphAIResult(
            success=True,
            data=GenerateGraphResponse(
                interpretation="测试解释",
                nodes=[node],
                edges=[],
                targetNodeId="n1",
            ),
        )

    def _make_app(self, monkeypatch, captured: dict):
        import routers.ai as ai_router

        fake_result = self._build_fake_graph_result()

        class FakeAIService:
            async def generate_graph(
                self, interpretation, original_input, user_background=None, learning_purpose="apply"
            ):
                captured["learning_purpose"] = learning_purpose
                captured["interpretation"] = interpretation
                return fake_result

        app = FastAPI()
        app.include_router(ai_router.router)
        app.dependency_overrides[ai_router.get_current_user_id] = lambda: "u_test"
        app.dependency_overrides[ai_router.get_db] = lambda: None
        monkeypatch.setattr(ai_router, "get_ai_service", lambda: FakeAIService())
        return app

    def _parse_sse(self, text: str) -> list[dict]:
        events = []
        for line in text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    def test_sse_response_media_type(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_sse_contains_meta_event(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        types = [e["type"] for e in events]
        assert "meta" in types

    def test_sse_contains_node_event(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        node_events = [e for e in events if e["type"] == "node"]
        assert len(node_events) == 1
        assert node_events[0]["node"]["name"] == "核心概念"

    def test_sse_contains_edges_event(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        assert any(e["type"] == "edges" for e in events)

    def test_sse_contains_done_event(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        assert events[-1]["type"] == "done"

    def test_sse_event_order_meta_before_nodes(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        types = [e["type"] for e in events]
        assert types.index("meta") < types.index("node")

    def test_sse_meta_contains_total_nodes(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        meta = next(e for e in events if e["type"] == "meta")
        assert meta["totalNodes"] == 1
        assert meta["targetNodeId"] == "n1"

    def test_sse_passes_learning_purpose_apply(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播", "learning_purpose": "apply"},
            )
        assert captured.get("learning_purpose") == "apply"

    def test_sse_passes_learning_purpose_explore(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播", "learning_purpose": "explore"},
            )
        assert captured.get("learning_purpose") == "explore"

    def test_sse_passes_learning_purpose_master(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播", "learning_purpose": "master"},
            )
        assert captured.get("learning_purpose") == "master"

    def test_sse_node_event_contains_phase_fields(self, monkeypatch):
        captured = {}
        app = self._make_app(monkeypatch, captured)
        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        node_event = next(e for e in events if e["type"] == "node")
        node = node_event["node"]
        assert node.get("phase") == "核心"
        assert node.get("phase_order") == 2
        assert node.get("depth_level") == 3

    def test_sse_error_event_on_ai_failure(self, monkeypatch):
        import routers.ai as ai_router
        from models import ApiError, GenerateGraphAIResult

        class FailingService:
            async def generate_graph(self, **kwargs):
                return GenerateGraphAIResult(
                    success=False,
                    error=ApiError(code="AI_SERVICE_ERROR", message="模拟错误"),
                )

        app = FastAPI()
        app.include_router(ai_router.router)
        app.dependency_overrides[ai_router.get_current_user_id] = lambda: "u_test"
        app.dependency_overrides[ai_router.get_db] = lambda: None
        monkeypatch.setattr(ai_router, "get_ai_service", lambda: FailingService())

        with TestClient(app) as client:
            resp = client.post(
                "/api/ai/generate-graph",
                json={"input": "反向传播", "interpretation": "反向传播"},
            )
        events = self._parse_sse(resp.text)
        assert events[0]["type"] == "error"
        assert events[0]["error"]["code"] == "AI_SERVICE_ERROR"


# ─── Section 5: Config file correctness (no DB) ──────────────────────────────


@pytest.mark.no_db
class TestGenerateGraphConfig:
    """generate_graph.json 配置完整性"""

    CONFIG_PATH = (
        Path(__file__).resolve().parents[1]
        / "services" / "llm" / "configs" / "generate_graph.json"
    )

    @pytest.fixture(autouse=True)
    def load_config(self):
        self.config = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))

    def test_config_has_learning_purpose_placeholder(self):
        assert "{{learning_purpose}}" in self.config["system_prompt"]

    def test_config_node_format_has_phase(self):
        nodes = self.config["output_format"]["nodes"]
        assert len(nodes) > 0
        assert "phase" in nodes[0]

    def test_config_node_format_has_phase_order(self):
        nodes = self.config["output_format"]["nodes"]
        assert "phase_order" in nodes[0]

    def test_config_node_format_has_depth_level(self):
        nodes = self.config["output_format"]["nodes"]
        assert "depth_level" in nodes[0]

    def test_config_rules_mention_all_three_purposes(self):
        rules_text = " ".join(self.config.get("rules", []))
        assert "explore" in rules_text
        assert "apply" in rules_text
        assert "master" in rules_text

    def test_config_rules_mention_phase_assignment(self):
        rules_text = " ".join(self.config.get("rules", []))
        assert "phase" in rules_text.lower()

    def test_config_model_params_present(self):
        params = self.config.get("model_params", {})
        assert "temperature" in params
        assert "max_tokens" in params

    def test_config_node_count_rules_by_purpose(self):
        """规则中节点数范围: explore=5-7, apply=7-10, master=10-15"""
        rules_text = " ".join(self.config.get("rules", []))
        assert "5-7" in rules_text
        assert "7-10" in rules_text
        assert "10-15" in rules_text
