import os
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from main import app

TEST_DB = "./test_database.sqlite"


@pytest.fixture(scope="function")
def test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE plans (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_access_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE nodes (
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        );
        CREATE TABLE edges (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            from_node_id TEXT NOT NULL,
            to_node_id TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (to_node_id) REFERENCES nodes(id) ON DELETE CASCADE
        );
        INSERT OR IGNORE INTO users (id, email, password_hash, name) VALUES 
            ('user_default', 'test@example.com', 'hash', 'Test User');
        INSERT INTO plans (id, user_id, title, status) VALUES 
            ('p_active', 'user_default', 'Active Plan', 'active');
        INSERT INTO plans (id, user_id, title, status) VALUES 
            ('p_archived', 'user_default', 'Archived Plan', 'archived');
        INSERT INTO plans (id, user_id, title, status) VALUES 
            ('p_with_graph', 'user_default', 'Plan with Graph', 'active');
        INSERT INTO nodes (id, plan_id, name, status) VALUES 
            ('n1', 'p_with_graph', 'Node 1', 'unlearned');
        INSERT INTO nodes (id, plan_id, name, status) VALUES 
            ('n2', 'p_with_graph', 'Node 2', 'learned');
        INSERT INTO edges (id, plan_id, from_node_id, to_node_id) VALUES 
            ('e1', 'p_with_graph', 'n1', 'n2');
    """
    )
    conn.commit()
    conn.close()
    yield TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        conn = sqlite3.connect(test_db)
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


class TestArchiveRestoreAPI:

    def test_archive_plan_success(self, client):
        response = client.put("/api/plans/p_active/archive")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "p_active"
        assert data["data"]["status"] == "archived"

    def test_archive_plan_not_found(self, client):
        response = client.put("/api/plans/p_not_exist/archive")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "PLAN_NOT_FOUND"

    def test_archive_already_archived_plan(self, client):
        response = client.put("/api/plans/p_archived/archive")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "PLAN_ALREADY_ARCHIVED"

    def test_restore_plan_success(self, client):
        response = client.put("/api/plans/p_archived/restore")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "p_archived"
        assert data["data"]["status"] == "active"

    def test_restore_plan_not_found(self, client):
        response = client.put("/api/plans/p_not_exist/restore")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "PLAN_NOT_FOUND"

    def test_restore_already_active_plan(self, client):
        response = client.put("/api/plans/p_active/restore")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "PLAN_ALREADY_ACTIVE"

    def test_get_archived_plans(self, client):
        response = client.get("/api/plans?status=archived")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        archived_ids = [p["id"] for p in data["data"]]
        assert "p_archived" in archived_ids
        assert "p_active" not in archived_ids

    def test_delete_plan_success(self, client, test_db):
        response = client.delete("/api/plans/p_with_graph")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "计划已删除"

        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ?", ("p_with_graph",))
        assert cursor.fetchone() is None
        cursor.execute("SELECT * FROM nodes WHERE plan_id = ?", ("p_with_graph",))
        assert cursor.fetchall() == []
        cursor.execute("SELECT * FROM edges WHERE plan_id = ?", ("p_with_graph",))
        assert cursor.fetchall() == []
        conn.close()

    def test_delete_plan_not_found(self, client):
        response = client.delete("/api/plans/p_not_exist")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "PLAN_NOT_FOUND"
