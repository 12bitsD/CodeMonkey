import pytest
from services.learning_history import get_learning_history


class TestGetLearningHistory:
    @pytest.mark.asyncio
    async def test_returns_empty_history_for_new_user(self, db):
        history = await get_learning_history(
            user_id="new_user", plan_id="plan_1", db=db
        )

        assert history["last_node"] is None
        assert history["last_session"] is None
        assert history["learned_nodes"] == []
        assert history["skipped_nodes"] == []

    @pytest.mark.asyncio
    async def test_returns_last_learned_node(self, db, auth_headers_a, client):
        plan_data = {
            "title": "测试计划",
            "originalInput": "input",
            "nodes": [
                {
                    "id": "n1",
                    "name": "矩阵乘法",
                    "status": "learned",
                    "x": 0,
                    "y": 0,
                    "why": "",
                    "what": [],
                    "mastery": [],
                    "prompt": "",
                    "resources": [],
                    "isTarget": False,
                }
            ],
            "edges": [],
            "targetNodeId": "n1",
        }

        create_resp = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
        plan_id = create_resp.json()["data"]["id"]

        await db.execute(
            """INSERT INTO learning_sessions 
                (id, user_id, plan_id, node_id, node_name, action)
                VALUES ('s1', 'u_a', %s, 'n1', '矩阵乘法', 'learned')""",
            (plan_id,),
        )
        db.commit()

        history = await get_learning_history(user_id="u_a", plan_id=plan_id, db=db)

        assert history["last_node"] == "矩阵乘法"
        assert history["learned_nodes"] == ["n1"]

    @pytest.mark.asyncio
    async def test_distinguishes_learned_and_skipped(self, db):
        cur = db.cursor()
        cur.execute(
            """INSERT INTO learning_sessions 
                (id, user_id, plan_id, node_id, node_name, action)
                VALUES 
                ('s1', 'user_1', 'plan_1', 'n1', '节点1', 'learned'),
                ('s2', 'user_1', 'plan_1', 'n2', '节点2', 'skipped')"""
        )
        db.commit()

        history = await get_learning_history(user_id="user_1", plan_id="plan_1", db=db)

        assert "n1" in history["learned_nodes"]
        assert "n2" in history["skipped_nodes"]
        assert "n2" not in history["learned_nodes"]

    @pytest.mark.asyncio
    async def test_returns_unique_nodes_only(self, db):
        cur = db.cursor()
        cur.execute(
            """INSERT INTO learning_sessions 
                (id, user_id, plan_id, node_id, node_name, action)
                VALUES 
                ('s1', 'user_1', 'plan_1', 'n1', '节点1', 'learned'),
                ('s2', 'user_1', 'plan_1', 'n1', '节点1', 'learned')"""
        )
        db.commit()

        history = await get_learning_history(user_id="user_1", plan_id="plan_1", db=db)

        assert history["learned_nodes"] == ["n1"]

    @pytest.mark.asyncio
    async def test_isolated_by_user_and_plan(self, db):
        cur = db.cursor()
        cur.execute(
            """INSERT INTO learning_sessions 
                (id, user_id, plan_id, node_id, node_name, action)
                VALUES ('s1', 'user_1', 'plan_1', 'n1', '节点1', 'learned')"""
        )
        cur.execute(
            """INSERT INTO learning_sessions 
                (id, user_id, plan_id, node_id, node_name, action)
                VALUES ('s2', 'user_2', 'plan_2', 'n2', '节点2', 'learned')"""
        )
        db.commit()

        history = await get_learning_history(user_id="user_1", plan_id="plan_1", db=db)

        assert history["learned_nodes"] == ["n1"]
        assert "n2" not in history["learned_nodes"]
