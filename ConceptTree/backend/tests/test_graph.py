import pytest
from fastapi.testclient import TestClient
import sqlite3
import json
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db

TEST_DB = "./test_graph_fixes.sqlite"


@pytest.fixture
def client():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # Initialize DB with schema and seed data
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Use the init_database logic but adapted for test
    # We copy the schema creation manually to ensure test environment is correct
    # or we could import init_database if it accepted a db path/connection

    # For this test, I'll rely on the app's startup event or manual init
    # But since I'm overriding get_db, I need to init the test db myself.

    # Create tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.execute(
        """
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
    """
    )
    conn.execute(
        """
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
    """
    )
    conn.execute(
        """
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
    """
    )
    conn.execute(
        """
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
    """
    )
    conn.execute(
        """
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
    """
    )

    # Seed data
    user_id = "user_default"
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, password_hash) VALUES (?, ?, ?)",
        (user_id, "test@example.com", "pw"),
    )

    # Ensure user profile exists (as it might be created on registration in real app)
    conn.execute(
        "INSERT INTO user_profiles (id, user_id, mastered_knowledge) VALUES (?, ?, ?)",
        ("profile_1", user_id, json.dumps([])),
    )

    plan_id = "p_1"
    conn.execute(
        "INSERT INTO plans (id, user_id, title) VALUES (?, ?, ?)",
        (plan_id, user_id, "Test Plan"),
    )

    node_id = "n_1"
    conn.execute(
        """
        INSERT INTO nodes (id, plan_id, name, status, what, mastery, resources) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            node_id,
            plan_id,
            "Test Node",
            "unlearned",
            json.dumps(["Concept A", "Concept B"]),
            json.dumps(["Mastery 1"]),
            json.dumps([{"name": "Res 1", "url": "http://example.com"}]),
        ),
    )

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


def test_get_graph_returns_parsed_json(client):
    response = client.get("/api/plans/p_1/graph")
    assert response.status_code == 200
    data = response.json()["data"]
    node = data["nodes"][0]

    # Check if JSON fields are parsed lists, not empty or strings
    assert isinstance(node["what"], list)
    assert len(node["what"]) == 2
    assert "Concept A" in node["what"]

    assert isinstance(node["mastery"], list)
    assert len(node["mastery"]) == 1

    assert isinstance(node["resources"], list)
    assert len(node["resources"]) == 1


def test_update_node_status_persists_and_updates_profile(client):
    # 1. Update status to learned
    response = client.put("/api/plans/p_1/nodes/n_1/status", json={"status": "learned"})
    assert response.status_code == 200

    # 2. Verify persistence (simulating new request/connection)
    # The client fixture uses a fresh connection for each request via dependency override?
    # Actually dependency override is set once. But get_db yields a new connection each time.
    # So if commit is missing, the next request (or direct db check) won't see changes.

    # Check directly in DB
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT status FROM nodes WHERE id = 'n_1'").fetchone()
    assert row["status"] == "learned", "Node status update was not committed!"

    # 3. Verify learning session created
    session = conn.execute(
        "SELECT * FROM learning_sessions WHERE node_id = 'n_1'"
    ).fetchone()
    assert session is not None, "Learning session not recorded!"
    assert session["action"] == "learned"
    assert session["node_name"] == "Test Node"

    # 4. Verify user profile updated
    profile = conn.execute(
        "SELECT mastered_knowledge FROM user_profiles WHERE user_id = 'user_default'"
    ).fetchone()
    mastered = json.loads(profile["mastered_knowledge"])
    assert "Test Node" in mastered, "User profile not updated!"

    conn.close()


def test_update_node_position_persists(client):
    response = client.put(
        "/api/plans/p_1/nodes/n_1/position", json={"x": 100, "y": 200}
    )
    assert response.status_code == 200

    conn = sqlite3.connect(TEST_DB)
    row = conn.execute("SELECT x, y FROM nodes WHERE id = 'n_1'").fetchone()
    assert row[0] == 100
    assert row[1] == 200, "Node position update was not committed!"
    conn.close()
