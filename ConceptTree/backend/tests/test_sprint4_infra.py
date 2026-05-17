from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager

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
    assert response.headers["x-request-id"]


@pytest.mark.no_db
def test_health_db_reports_ok_when_database_query_succeeds(monkeypatch):
    import main
    from utils.observability import reset_observability_for_tests

    reset_observability_for_tests()

    class FakeResult:
        def fetchone(self):
            return {"?column?": 1}

    class FakeDb:
        def execute(self, sql, params=None):
            assert sql == "SELECT 1"
            return FakeResult()

    @contextmanager
    def fake_db_context():
        yield FakeDb()

    monkeypatch.setattr(main, "get_db_context", fake_db_context)

    with TestClient(main.app) as client:
        response = client.get("/health/db")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["latencyMs"] >= 0


@pytest.mark.no_db
def test_health_db_reports_degraded_without_crashing(monkeypatch):
    import main
    from psycopg2 import OperationalError
    from utils.observability import reset_observability_for_tests

    reset_observability_for_tests()

    @contextmanager
    def fake_db_context():
        raise OperationalError("database unavailable")
        yield

    monkeypatch.setattr(main, "get_db_context", fake_db_context)

    with TestClient(main.app) as client:
        response = client.get("/health/db")
        metrics = client.get("/health/metrics")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"
    assert metrics.json()["metrics"]["dbErrorCounts"]["DATABASE_UNAVAILABLE"] == 1


@pytest.mark.no_db
def test_health_metrics_include_request_counters():
    from main import app
    from utils.observability import reset_observability_for_tests

    reset_observability_for_tests()

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "test-request-id"})
        metrics = client.get("/health/metrics")

    assert response.headers["x-request-id"] == "test-request-id"
    request_metrics = metrics.json()["metrics"]["requests"]
    assert request_metrics["GET /health"]["count"] >= 1
    assert request_metrics["GET /health"]["avgLatencyMs"] >= 0


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
    assert statements[0][0] == "SET statement_timeout TO %s"
    assert statements[1][0] == "SET lock_timeout TO %s"
    assert statements[2][0] == "SET idle_in_transaction_session_timeout TO %s"
    assert statements[3][0] == 'SET search_path TO "sprint4_schema"'
    assert statements[4][0] == "SELECT 1"


@pytest.mark.no_db
def test_database_operational_errors_return_recoverable_json():
    from psycopg2 import OperationalError
    from main import app

    @app.get("/__test_db_operational_error")
    def _raise_db_error():
        raise OperationalError("SSL SYSCALL error: EOF detected")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test_db_operational_error")

    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


@pytest.mark.no_db
def test_database_data_errors_return_bad_request_json():
    from psycopg2 import DataError
    from main import app

    @app.get("/__test_db_data_error")
    def _raise_db_error():
        raise DataError("invalid input syntax for type timestamp")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test_db_data_error")

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "DATABASE_INVALID_DATA"


@pytest.mark.no_db
def test_schema_readiness_reports_missing_columns():
    import database

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeDb:
        def execute(self, sql, params=None):
            table_name = params[0]
            rows_by_table = {
                "plans": [{"column_name": "start_date"}],
                "nodes": [],
            }
            return FakeResult(rows_by_table.get(table_name, []))

    with pytest.raises(database.SchemaNotReadyError) as exc:
        database.ensure_schema_columns(
            FakeDb(),
            {
                "plans": ("start_date", "target_end_date"),
                "nodes": ("target_end_date",),
            },
        )

    assert exc.value.missing_columns == [
        "plans.target_end_date",
        "nodes.target_end_date",
    ]


@pytest.mark.no_db
def test_schema_not_ready_errors_return_recoverable_json():
    from database import SchemaNotReadyError
    from main import app

    @app.get("/__test_schema_not_ready")
    def _raise_schema_error():
        raise SchemaNotReadyError(["nodes.target_end_date"])

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test_schema_not_ready")

    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "SCHEMA_NOT_READY"
    assert response.json()["error"]["missingColumns"] == ["nodes.target_end_date"]


@pytest.mark.no_db
def test_transaction_commits_success_and_rolls_back_failure():
    import database

    class FakeDb:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    successful = FakeDb()
    with database.transaction(successful):
        pass
    assert successful.commits == 1
    assert successful.rollbacks == 0

    failing = FakeDb()
    with pytest.raises(RuntimeError):
        with database.transaction(failing):
            raise RuntimeError("boom")

    assert failing.commits == 0
    assert failing.rollbacks == 1


@pytest.mark.no_db
def test_release_connection_closes_broken_connection(monkeypatch):
    import database

    class BrokenConnection:
        closed = 0

        def rollback(self):
            raise RuntimeError("connection is broken")

    class FakePool:
        def __init__(self):
            self.calls = []

        def putconn(self, conn, close=False):
            self.calls.append((conn, close))

    fake_pool = FakePool()
    conn = BrokenConnection()
    monkeypatch.setattr(database, "get_connection_pool", lambda: fake_pool)

    database._release_connection(conn)

    assert fake_pool.calls == [(conn, True)]


@pytest.mark.no_db
def test_dockerfile_runs_as_non_root_user():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "useradd" in dockerfile or "adduser" in dockerfile
    assert "USER appuser" in dockerfile
