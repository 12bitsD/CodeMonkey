from __future__ import annotations

from pathlib import Path
import re

import pytest


CORE_TABLES = [
    "users",
    "user_profiles",
    "plans",
    "nodes",
    "edges",
    "learning_sessions",
    "notes",
]

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.sql"
MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "2026-04-16_enable_rls.sql"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.no_db
def test_rls_migration_exists():
    assert MIGRATION_PATH.exists(), "RLS hardening migration is missing"


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_all_core_tables_enable_rls(path: Path):
    sql = _read(path)
    for table in CORE_TABLES:
        assert (
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql
        ), f"{path.name} is missing ENABLE RLS for {table}"


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_all_core_tables_force_rls(path: Path):
    sql = _read(path)
    for table in CORE_TABLES:
        assert (
            f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in sql
        ), f"{path.name} is missing FORCE RLS for {table}"


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_public_and_supabase_roles_are_revoked(path: Path):
    sql = _read(path)
    assert "REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes FROM PUBLIC;" in sql
    assert "to_regrole('anon')" in sql
    assert "to_regrole('authenticated')" in sql
    assert "FROM anon" in sql
    assert "FROM authenticated" in sql


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_no_dangerous_public_grants(path: Path):
    sql = _read(path)
    dangerous = re.findall(
        r"GRANT\s+ALL(?:\s+PRIVILEGES)?\s+ON\s+TABLE.*\b(PUBLIC|anon|authenticated)\b",
        sql,
        flags=re.IGNORECASE,
    )
    assert dangerous == [], f"{path.name} contains dangerous public grants: {dangerous}"


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_rls_is_never_disabled(path: Path):
    sql = _read(path).upper()
    assert "DISABLE ROW LEVEL SECURITY" not in sql
