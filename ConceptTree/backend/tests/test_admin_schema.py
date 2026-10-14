from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_ROOT / "schema.sql"
MIGRATION_PATH = BACKEND_ROOT / "sql" / "2026-10-14_admin_control_room.sql"
ADMIN_TABLES = ("user_roles", "session_trace_events", "admin_audit_logs")


@pytest.mark.no_db
def test_admin_migration_is_present_and_idempotent():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    for table in ADMIN_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql


@pytest.mark.no_db
@pytest.mark.parametrize("path", [SCHEMA_PATH, MIGRATION_PATH])
def test_admin_tables_are_hardened(path: Path):
    sql = path.read_text(encoding="utf-8")
    for table in ADMIN_TABLES:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in sql
        assert table in sql
    assert "FROM PUBLIC" in sql
    assert "FROM anon" in sql
    assert "FROM authenticated" in sql


@pytest.mark.no_db
def test_admin_schema_never_grants_public_access():
    sql = MIGRATION_PATH.read_text(encoding="utf-8").upper()
    assert "GRANT ALL" not in sql
    assert "DISABLE ROW LEVEL SECURITY" not in sql
