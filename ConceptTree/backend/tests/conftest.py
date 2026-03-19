"""Shared fixtures for all integration tests in the ConceptTree backend.

Every integration test that needs a real database relies on this file.
It provisions a throwaway PostgreSQL schema, seeds two test users (u_a
and u_b), exposes a FastAPI TestClient, and wipes all rows between tests
so each test starts from a known-clean state.

Key fixtures and what they do:
- ``test_schema``   — creates a uniquely-named Postgres schema and tears it
                      down at the end of the session (session-scoped).
- ``client``        — a FastAPI TestClient wired to the running application.
- ``reset_database``— truncates all tables and re-seeds the two baseline users
                      before every test (unless the test is marked ``no_db``).
- ``auth_headers_a``/ ``auth_headers_b`` — JWT Bearer headers for user u_a
                      and u_b respectively, ready to pass as ``headers=``.
- ``db``            — a raw psycopg2 connection scoped to the test schema,
                      useful for tests that need to inspect or insert rows directly.

Requirements:
- The environment variable ``DATABASE_URL`` must be set; any test that
  requires it will be *skipped* (not failed) if it is absent.
- The schema.sql file at ``backend/schema.sql`` must exist and be valid SQL.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2.extras import Json


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _require_database_url() -> str:
    """Return DATABASE_URL or skip the current test if it is not set.

    Skipping (not failing) keeps CI green when the database is not
    available, while still surfacing failures when it is.
    """
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("DATABASE_URL is required for integration tests")
    return database_url


def _read_schema_sql() -> str:
    """Return the full contents of backend/schema.sql as a string."""
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    return schema_path.read_text(encoding="utf-8")


def _split_statements(sql: str) -> list[str]:
    """Split a SQL script on semicolons, discarding empty fragments.

    Postgres requires statements to be executed one at a time through
    psycopg2, so the raw schema file must be split before execution.
    """
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


@pytest.fixture(scope="session")
def test_schema() -> str:
    """Provision a temporary Postgres schema for the entire test session.

    A randomly-named schema (e.g. ``ct_test_3f8a1c2b``) is created,
    all tables from schema.sql are applied inside it, and the schema is
    set in the environment so the app under test uses it automatically.
    The schema is dropped unconditionally when the session ends.
    """
    database_url = _require_database_url()
    schema = f"ct_test_{uuid.uuid4().hex[:8]}"
    schema_sql = _read_schema_sql()
    statements = _split_statements(schema_sql)

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                cur.execute(f'SET search_path TO "{schema}"')
                for stmt in statements:
                    cur.execute(stmt)
        os.environ["DATABASE_SCHEMA"] = schema
        yield schema
    finally:
        drop_conn = psycopg2.connect(database_url)
        try:
            with drop_conn:
                with drop_conn.cursor() as cur:
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        finally:
            drop_conn.close()
        conn.close()


@pytest.fixture(scope="session")
def client(test_schema: str):
    """Return a FastAPI TestClient connected to the application.

    The client is created once per session and reused across all tests,
    avoiding repeated startup overhead. It depends on ``test_schema`` so
    the database is ready before the first request.
    """
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_database(request, test_schema: str):
    """Wipe and re-seed the database before every test that uses a database.

    After truncating all tables (resetting auto-increment sequences), two
    users are inserted:

    - ``u_a`` / ``a@example.com`` — the primary test user
    - ``u_b`` / ``b@example.com`` — the secondary user for cross-user
      isolation tests

    Both users get empty user-profile rows so profile-related endpoints
    work without additional setup.

    Tests decorated with ``@pytest.mark.no_db`` skip this fixture entirely,
    which is appropriate for pure unit tests that mock the database layer.
    """
    if request.node.get_closest_marker("no_db"):
        yield
        return
    database_url = _require_database_url()
    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                search_path_sql = f'SET search_path TO "{test_schema}"'
                cur.execute(search_path_sql)
                cur.execute(
                    (
                        "TRUNCATE TABLE notes, learning_sessions, edges, "
                        "nodes, plans, user_profiles, users "
                        "RESTART IDENTITY CASCADE"
                    )
                )

                cur.execute(
                    (
                        "INSERT INTO users (id, email, password_hash) "
                        "VALUES (%s, %s, %s)"
                    ),
                    ("u_a", "a@example.com", "hash_a"),
                )
                cur.execute(
                    (
                        "INSERT INTO users (id, email, password_hash) "
                        "VALUES (%s, %s, %s)"
                    ),
                    ("u_b", "b@example.com", "hash_b"),
                )
                cur.execute(
                    (
                        "INSERT INTO user_profiles "
                        "(id, user_id, abilities, mastered_knowledge) "
                        "VALUES (%s, %s, %s, %s)"
                    ),
                    ("profile_a", "u_a", Json([]), Json([])),
                )
                cur.execute(
                    (
                        "INSERT INTO user_profiles "
                        "(id, user_id, abilities, mastered_knowledge) "
                        "VALUES (%s, %s, %s, %s)"
                    ),
                    ("profile_b", "u_b", Json([]), Json([])),
                )
        yield
    finally:
        conn.close()


@pytest.fixture()
def auth_headers_a():
    """Return a JWT Authorization header for the primary test user (u_a).

    Use ``headers=auth_headers_a`` in any TestClient call that requires
    authentication as user A.
    """
    from utils.auth import create_access_token

    token = create_access_token({"sub": "u_a"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_b():
    """Return a JWT Authorization header for the secondary test user (u_b).

    Use this fixture when testing cross-user isolation — for example,
    verifying that user B cannot delete or modify resources owned by user A.
    """
    from utils.auth import create_access_token

    token = create_access_token({"sub": "u_b"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def db(test_schema: str):
    """Return an open psycopg2 connection scoped to the test schema.

    Use this fixture in tests that need to read or write database rows
    directly rather than going through the HTTP API. The connection is
    automatically closed after the test.
    """
    database_url = _require_database_url()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{test_schema}"')
        yield conn
    finally:
        conn.close()
