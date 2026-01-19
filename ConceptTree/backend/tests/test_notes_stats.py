import pytest
from fastapi.testclient import TestClient
import sqlite3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db

TEST_DB = "./test_notes_stats.sqlite"


@pytest.fixture
def client():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            occupation TEXT,
            education TEXT,
            programming_level TEXT DEFAULT '入门',
            math_level TEXT DEFAULT '入门',
            abilities TEXT DEFAULT '[]',
            mastered_knowledge TEXT DEFAULT '[]',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            last_access_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'unlearned',
            x REAL DEFAULT 0,
            y REAL DEFAULT 0,
            why TEXT,
            what TEXT,
            mastery TEXT,
            prompt TEXT,
            resources TEXT,
            is_target INTEGER DEFAULT 0,
            domain TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            from_node_id TEXT NOT NULL,
            to_node_id TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (to_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            UNIQUE(plan_id, from_node_id, to_node_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            node_name TEXT,
            action TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    user_id = "user_default"
    conn.execute("INSERT OR IGNORE INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                 (user_id, "test@example.com", "pw"))
    conn.execute("INSERT INTO user_profiles (id, user_id, mastered_knowledge) VALUES (?, ?, ?)",
                 ("profile_1", user_id, json.dumps(["知识点A", "知识点B"])))

    plan_id = "p_1"
    conn.execute("INSERT INTO plans (id, user_id, title, status, progress, total) VALUES (?, ?, ?, ?, ?, ?)",
                 (plan_id, user_id, "Test Plan", "active", 2, 3))

    conn.execute("""
        INSERT INTO nodes (id, plan_id, name, status, domain) VALUES (?, ?, ?, ?, ?)
    """, ("n_1", plan_id, "Node 1", "learned", "深度学习"))
    conn.execute("""
        INSERT INTO nodes (id, plan_id, name, status, domain) VALUES (?, ?, ?, ?, ?)
    """, ("n_2", plan_id, "Node 2", "learned", "数学基础"))
    conn.execute("""
        INSERT INTO nodes (id, plan_id, name, status, domain) VALUES (?, ?, ?, ?, ?)
    """, ("n_3", plan_id, "Node 3", "unlearned", "深度学习"))

    conn.execute("INSERT INTO notes (id, plan_id, node_id, user_id, content) VALUES (?, ?, ?, ?, ?)",
                 ("note_1", plan_id, "n_1", user_id, "This is a test note"))

    conn.execute("""INSERT INTO learning_sessions (id, user_id, plan_id, node_id, node_name, action)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 ("ls_1", user_id, plan_id, "n_1", "Node 1", "learned"))

    conn.commit()
    conn.close()

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


class TestBulkPositionUpdate:
    def test_bulk_update_positions_success(self, client):
        response = client.put("/api/plans/p_1/nodes/positions", json={
            "positions": [
                {"nodeId": "n_1", "x": 100, "y": 200},
                {"nodeId": "n_2", "x": 300, "y": 400}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["updated"] == 2

        conn = sqlite3.connect(TEST_DB)
        conn.row_factory = sqlite3.Row
        row1 = conn.execute("SELECT x, y FROM nodes WHERE id = 'n_1'").fetchone()
        row2 = conn.execute("SELECT x, y FROM nodes WHERE id = 'n_2'").fetchone()
        assert row1["x"] == 100
        assert row1["y"] == 200
        assert row2["x"] == 300
        assert row2["y"] == 400
        conn.close()

    def test_bulk_update_positions_plan_not_found(self, client):
        response = client.put("/api/plans/p_not_exist/nodes/positions", json={
            "positions": [{"nodeId": "n_1", "x": 100, "y": 200}]
        })
        assert response.status_code == 404


class TestNotesAPI:
    def test_get_notes(self, client):
        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1
        assert len(data["data"]["notes"]) >= 1

    def test_get_notes_filter_by_plan(self, client):
        response = client.get("/api/notes?planId=p_1")
        assert response.status_code == 200
        data = response.json()
        assert all(n["planId"] == "p_1" for n in data["data"]["notes"])

    def test_get_notes_search(self, client):
        response = client.get("/api/notes?search=test")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] >= 1

    def test_create_note(self, client):
        response = client.post("/api/notes", json={
            "planId": "p_1",
            "nodeId": "n_1",
            "content": "New note content"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "New note content"
        assert "id" in data["data"]

    def test_create_note_empty_content(self, client):
        response = client.post("/api/notes", json={
            "planId": "p_1",
            "nodeId": "n_1",
            "content": ""
        })
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "CONTENT_REQUIRED"

    def test_create_note_plan_not_found(self, client):
        response = client.post("/api/notes", json={
            "planId": "p_not_exist",
            "nodeId": "n_1",
            "content": "test"
        })
        assert response.status_code == 404
        assert response.json()["detail"]["error"]["code"] == "PLAN_NOT_FOUND"

    def test_update_note(self, client):
        response = client.put("/api/notes/note_1", json={
            "content": "Updated content"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "Updated content"

    def test_update_note_not_found(self, client):
        response = client.put("/api/notes/note_not_exist", json={
            "content": "test"
        })
        assert response.status_code == 404
        assert response.json()["detail"]["error"]["code"] == "NOTE_NOT_FOUND"

    def test_delete_note(self, client):
        response = client.delete("/api/notes/note_1")
        assert response.status_code == 200
        assert response.json()["success"] is True

        conn = sqlite3.connect(TEST_DB)
        row = conn.execute("SELECT * FROM notes WHERE id = 'note_1'").fetchone()
        assert row is None
        conn.close()

    def test_delete_note_not_found(self, client):
        response = client.delete("/api/notes/note_not_exist")
        assert response.status_code == 404


class TestStatsAPI:
    def test_get_stats_overview(self, client):
        response = client.get("/api/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]
        assert "thisWeek" in data["data"]
        assert data["data"]["summary"]["activePlans"] >= 1
        assert data["data"]["summary"]["masteredKnowledge"] == 2

    def test_get_stats_distribution(self, client):
        response = client.get("/api/stats/distribution")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "distribution" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] == 2
