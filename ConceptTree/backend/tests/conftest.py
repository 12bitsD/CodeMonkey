from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from psycopg2.extras import Json

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("DATABASE_URL is required for integration tests")
    return database_url


def _read_schema_sql() -> str:
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    return schema_path.read_text(encoding="utf-8")


def _split_statements(sql: str) -> list[str]:
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


@pytest.fixture(scope="session")
def test_schema() -> str:
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
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_database(request, test_schema: str):
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
    from utils.auth import create_access_token

    token = create_access_token({"sub": "u_a"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_b():
    from utils.auth import create_access_token

    token = create_access_token({"sub": "u_b"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def db(test_schema: str):
    database_url = _require_database_url()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{test_schema}"')
        yield conn
    finally:
        conn.close()
