import pytest

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
    def __init__(self, row=None):
        self.row = row
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeResult(self.row)


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

    sql, params = db.calls[0]
    assert "ON CONFLICT" in sql
    assert params == ("u1:POST /api/notes:k1", "u1", "POST /api/notes", response)

