from pathlib import Path

import pytest


pytestmark = pytest.mark.no_db

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BACKEND_ROOT / "schema.sql"
MIGRATION_PATH = BACKEND_ROOT / "sql" / "2026-05-20_deep_learn_sessions_schema.sql"

REQUIRED_COLUMNS = [
    "test_questions",
    "test_current_index",
    "test_results",
    "ended_at",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_deep_learn_sessions_schema_contains_runtime_state_columns():
    sql = _read(SCHEMA_PATH)
    assert "CREATE TABLE IF NOT EXISTS deep_learn_sessions" in sql
    for column in REQUIRED_COLUMNS:
        assert column in sql


def test_deep_learn_runtime_migration_backfills_missing_columns():
    sql = _read(MIGRATION_PATH)
    assert "CREATE TABLE IF NOT EXISTS deep_learn_sessions" in sql
    for column in REQUIRED_COLUMNS:
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql
    assert "CREATE TABLE IF NOT EXISTS idempotency_keys" in sql
