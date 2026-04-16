from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.no_db
def test_health_endpoint_includes_security_headers():
    from main import app

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.no_db
def test_get_db_context_uses_pool_and_returns_connection(monkeypatch):
    import database

    statements = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            statements.append((sql, params))

    class FakeConnection:
        closed = 0

        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def cursor(self, cursor_factory=None):
            return FakeCursor()

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    class FakePool:
        def __init__(self, conn):
            self.conn = conn
            self.put_back = []
            self.requests = 0

        def getconn(self):
            self.requests += 1
            return self.conn

        def putconn(self, conn):
            self.put_back.append(conn)

    fake_connection = FakeConnection()
    fake_pool = FakePool(fake_connection)

    monkeypatch.setenv("DATABASE_SCHEMA", "sprint4_schema")
    monkeypatch.setattr(database, "get_connection_pool", lambda: fake_pool)

    with database.get_db_context() as session:
        session.execute("SELECT 1")

    assert fake_pool.requests == 1
    assert fake_pool.put_back == [fake_connection]
    assert fake_connection.commits == 1
    assert fake_connection.rollbacks == 1
    assert statements[0][0] == 'SET search_path TO "sprint4_schema"'
    assert statements[1][0] == "SELECT 1"


@pytest.mark.no_db
def test_dockerfile_runs_as_non_root_user():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "useradd" in dockerfile or "adduser" in dockerfile
    assert "USER appuser" in dockerfile
