import pytest
from psycopg2.errors import UndefinedTable

from utils.idempotency import (
    build_idempotency_id,
    get_idempotent_response,
    normalize_idempotency_key,
    store_idempotent_response,
)

pytestmark = pytest.mark.no_db


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class FakeDb:
    def __init__(self, row=None, fail_on=None):
        self.row = row
        self.calls = []
        self.fail_on = fail_on
        self.rollbacks = 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if self.fail_on and self.fail_on in sql:
            raise UndefinedTable("missing idempotency table")
        return FakeResult(self.row)

    def rollback(self):
        self.rollbacks += 1


def test_normalize_idempotency_key_rejects_empty_values():
    assert normalize_idempotency_key(None) is None
    assert normalize_idempotency_key("   ") is None


def test_build_idempotency_id_scopes_by_user_and_endpoint():
    assert build_idempotency_id("u1", "POST /api/notes", "k1") == "u1:POST /api/notes:k1"


def test_get_idempotent_response_returns_cached_json():
    cached = {"success": True, "data": {"id": "note_1"}}
    db = FakeDb({"response": cached})

    assert get_idempotent_response(db, "u1", "POST /api/notes", "k1") == cached


def test_store_idempotent_response_uses_insert_on_conflict():
    db = FakeDb()
    response = {"success": True, "data": {"id": "note_1"}}

    store_idempotent_response(db, "u1", "POST /api/notes", "k1", response)

    sql, params = next(call for call in db.calls if "INSERT INTO idempotency_keys" in call[0])
    assert "ON CONFLICT" in sql
    assert params == ("u1:POST /api/notes:k1", "u1", "POST /api/notes", response)


def test_missing_idempotency_table_does_not_block_get_or_store():
    get_db = FakeDb(fail_on="SELECT response")
    assert get_idempotent_response(get_db, "u1", "POST /api/notes", "k1") is None
    assert get_db.rollbacks == 1

    store_db = FakeDb(fail_on="INSERT INTO idempotency_keys")
    store_idempotent_response(
        store_db,
        "u1",
        "POST /api/notes",
        "k1",
        {"success": True},
    )
    sql_calls = [call[0] for call in store_db.calls]
    assert any("ROLLBACK TO SAVEPOINT idempotency_store" in sql for sql in sql_calls)
    assert any("RELEASE SAVEPOINT idempotency_store" in sql for sql in sql_calls)
