"""AI服务API测试 - 简化版本"""

import os
import sys
import sqlite3
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from database import get_db

TEST_DB = "./test_ai.db"


@pytest.fixture(scope="function")
def client():
    """测试客户端"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    import database

    database.DATABASE_PATH = TEST_DB
    database.init_database()

    def override_get_db():
        conn = sqlite3.connect(TEST_DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestParseGoal:
    """测试解析学习目标"""

    def test_parse_goal_success(self, client):
        """测试成功解析学习目标"""
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "我想学反向传播，我有Python基础但数学不好"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        result = data["data"]
        assert "interpretation" in result
        assert "backgroundSummary" in result
        assert "suggestedNodeCount" in result
        assert "shouldSplit" in result

    def test_parse_goal_simple_input(self, client):
        """测试简单输入（可能需要拆分）"""
        response = client.post("/api/ai/parse-goal", json={"input": "深度学习"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        result = data["data"]
        assert "shouldSplit" in result
        if result["shouldSplit"]:
            assert "splitSuggestions" in result
            assert len(result["splitSuggestions"]) > 0


class TestGenerateGraph:
    """测试生成知识图谱"""

    def test_generate_graph_success(self, client):
        """测试成功生成知识图谱"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学反向传播",
                "interpretation": "学习神经网络的反向传播算法",
            },
        )

        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        result = data["data"]
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) > 0

    def test_generate_graph_node_structure(self, client):
        """测试生成的节点结构"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学反向传播",
                "interpretation": "学习神经网络的反向传播算法",
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        node = result["nodes"][0]
        assert "id" in node
        assert "name" in node
        assert "status" in node
        assert "x" in node
        assert "y" in node
