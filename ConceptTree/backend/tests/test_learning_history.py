import pytest
from services.learning_history import get_learning_history


class TestGetLearningHistory:
    def test_returns_empty_history_for_new_user(self, db):
        history = get_learning_history(user_id="u_a", plan_id="nonexistent", db=db)

        assert history["last_node"] is None
        assert history["last_session"] is None
        assert history["learned_nodes"] == []
        assert history["skipped_nodes"] == []

    def test_returns_last_learned_node(self, db):
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s1", "u_a", "p1", "n1", "矩阵乘法", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["last_node"] == "矩阵乘法"
        assert "n1" in history["learned_nodes"]

    def test_distinguishes_learned_and_skipped(self, db):
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s2", "u_a", "p1", "n2", "节点2", "skipped"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert "n1" in history["learned_nodes"]
        assert "n2" in history["skipped_nodes"]
        assert "n2" not in history["learned_nodes"]

    def test_deduplicates_repeated_actions(self, db):
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s2", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["learned_nodes"].count("n1") == 1

    def test_isolated_by_user_and_plan(self, db):
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["s2", "u_b", "p2", "n2", "节点2", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["learned_nodes"] == ["n1"]
        assert "n2" not in history["learned_nodes"]
