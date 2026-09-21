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
HARDEN_ALL_TABLES_PATH = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "2026-09-21_harden_all_public_tables_rls.sql"
)
ALL_APP_TABLES = CORE_TABLES + [
    "deep_learn_sessions",
    "idempotency_keys",
    "completion_notes",
    "user_learning_profile",
    "learning_session_records",
    "teaching_patterns",
]


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
    public_revokes = " ".join(
        re.findall(
            r"REVOKE ALL PRIVILEGES ON TABLE\s+([^;]+)\s+FROM PUBLIC;",
            sql,
            flags=re.IGNORECASE,
        )
    )
    for table in CORE_TABLES:
        assert re.search(
            rf"\b{table}\b", public_revokes
        ), f"{path.name} does not revoke PUBLIC from {table}"
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


@pytest.mark.no_db
def test_all_public_app_tables_are_hardened_by_latest_migration():
    assert HARDEN_ALL_TABLES_PATH.exists(), "full RLS hardening migration is missing"
    sql = _read(HARDEN_ALL_TABLES_PATH)

    for table in ALL_APP_TABLES:
        qualified = f"public.{table}"
        assert f"ALTER TABLE IF EXISTS {qualified} ENABLE ROW LEVEL SECURITY;" in sql
        assert f"ALTER TABLE IF EXISTS {qualified} FORCE ROW LEVEL SECURITY;" in sql
        assert f"REVOKE ALL PRIVILEGES ON TABLE {qualified} FROM PUBLIC;" in sql

    assert "to_regrole('anon')" in sql
    assert "to_regrole('authenticated')" in sql
    assert "FROM anon" in sql
    assert "FROM authenticated" in sql
