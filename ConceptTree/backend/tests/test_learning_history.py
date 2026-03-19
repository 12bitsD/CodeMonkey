"""Learning history service unit tests: validates get_learning_history data retrieval.

The learning history service reads the learning_sessions table to summarise what
a user has learned or skipped in a given plan. It is used by the recommend-next
AI feature to provide personalised context to the LLM.

This module validates five key scenarios directly against the database (using
the ``db`` fixture) without going through the HTTP layer:
1. A new user with no sessions gets a fully empty history structure.
2. A learned session creates a record visible as the last node and in learned_nodes.
3. Learned and skipped sessions are kept in separate lists.
4. If the same node is recorded multiple times, it appears only once (deduplication).
5. Sessions for other users or other plans are excluded from the result (isolation).

Primary reader: a developer extending the learning history logic or debugging
why the recommend-next LLM prompt is missing expected context.
"""

import pytest
from services.learning_history import get_learning_history


class TestGetLearningHistory:
    def test_returns_empty_history_for_new_user(self, db):
        """A user with no learning sessions gets a fully empty history.

        All fields must be initialised to empty/None values rather than raising
        an error or returning partial data.
        Expected: last_node=None, last_session=None, learned_nodes=[],
        skipped_nodes=[].
        """
        history = get_learning_history(user_id="u_a", plan_id="nonexistent", db=db)

        assert history["last_node"] is None
        assert history["last_session"] is None
        assert history["learned_nodes"] == []
        assert history["skipped_nodes"] == []

    def test_returns_last_learned_node(self, db):
        """A 'learned' session is reflected in last_node and learned_nodes.

        Inserts one learning session (action='learned') and checks that the
        history correctly identifies '矩阵乘法' as the last node and 'n1' as
        a member of learned_nodes.
        Expected: last_node='矩阵乘法', 'n1' in learned_nodes.
        """
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s1", "u_a", "p1", "n1", "矩阵乘法", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["last_node"] == "矩阵乘法"
        assert "n1" in history["learned_nodes"]

    def test_distinguishes_learned_and_skipped(self, db):
        """Learned and skipped sessions populate separate lists.

        Inserts one 'learned' session for n1 and one 'skipped' session for n2.
        Each node must appear in the correct list and not cross-contaminate.
        Expected: 'n1' in learned_nodes, 'n2' in skipped_nodes,
        'n2' not in learned_nodes.
        """
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s2", "u_a", "p1", "n2", "节点2", "skipped"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert "n1" in history["learned_nodes"]
        assert "n2" in history["skipped_nodes"]
        assert "n2" not in history["learned_nodes"]

    def test_deduplicates_repeated_actions(self, db):
        """A node recorded multiple times in sessions appears only once in the result.

        Inserting two 'learned' sessions for the same node must not produce
        duplicate entries in learned_nodes.
        Expected: learned_nodes.count('n1') == 1.
        """
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s2", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["learned_nodes"].count("n1") == 1

    def test_isolated_by_user_and_plan(self, db):
        """Sessions for other users or other plans do not appear in the result.

        Inserts a session for user u_a/plan p1 and another for user u_b/plan p2.
        Querying for u_a/p1 must return only n1, never n2.
        Expected: learned_nodes==['n1'], 'n2' not in learned_nodes.
        """
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s1", "u_a", "p1", "n1", "节点1", "learned"],
        )
        db.execute(
            "INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ["s2", "u_b", "p2", "n2", "节点2", "learned"],
        )
        db.commit()

        history = get_learning_history(user_id="u_a", plan_id="p1", db=db)

        assert history["learned_nodes"] == ["n1"]
        assert "n2" not in history["learned_nodes"]
