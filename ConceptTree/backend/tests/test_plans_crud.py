import pytest
from fastapi.testclient import TestClient
import sqlite3
import os
import json
from main import app
from database import get_db

TEST_DB = "test_plans_crud.db"


@pytest.fixture(scope="function")
def client():
    """测试客户端"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # 初始化测试数据库
    import database

    database.DATABASE_PATH = TEST_DB
    database.init_database(run_seed=False)

    # 注入测试数据库连接
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


class TestPlansCRUD:
    def test_create_plan_success(self, client):
        """测试创建计划"""
        plan_data = {
            "title": "测试计划",
            "originalInput": "我想学Python",
            "nodes": [
                {
                    "id": "node_test_1",
                    "name": "Python基础",
                    "status": "unlearned",
                    "x": 0,
                    "y": 0,
                    "why": "基础",
                    "what": ["语法"],
                    "mastery": ["写出Hello World"],
                    "isTarget": True,
                    "domain": "编程",
                }
            ],
            "edges": [],
            "targetNodeId": "node_test_1",
        }
        response = client.post("/api/plans", json=plan_data)
        if response.status_code != 200:
            print(f"Error: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "测试计划"
        assert "id" in data["data"]

    def test_update_plan_title_success(self, client):
        """测试更新计划标题"""
        # 先创建一个计划
        create_resp = client.post(
            "/api/plans",
            json={
                "title": "旧标题",
                "originalInput": "test",
                "nodes": [
                    {
                        "id": "node_test_update_1",
                        "name": "node",
                        "status": "unlearned",
                        "x": 0,
                        "y": 0,
                        "isTarget": True,
                    }
                ],
                "edges": [],
                "targetNodeId": "node_test_update_1",
            },
        )
        plan_id = create_resp.json()["data"]["id"]

        # 更新标题
        response = client.put(f"/api/plans/{plan_id}", json={"title": "新标题"})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 验证更新结果
        get_resp = client.get("/api/plans")
        plans = get_resp.json()["data"]
        updated_plan = next(p for p in plans if p["id"] == plan_id)
        assert updated_plan["title"] == "新标题"
