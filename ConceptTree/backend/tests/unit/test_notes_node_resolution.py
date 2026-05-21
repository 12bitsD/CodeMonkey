import pytest
from fastapi import HTTPException

from routers.notes import _resolve_node_id

pytestmark = pytest.mark.no_db


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeDb:
    def __init__(self, existing_ids):
        self.existing_ids = set(existing_ids)
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(params)
        node_id, plan_id = params
        if node_id in self.existing_ids:
            return FakeResult({"id": node_id, "plan_id": plan_id})
        return FakeResult(None)


def test_resolve_node_id_accepts_stored_node_id():
    db = FakeDb({"plan_1_node_1"})

    assert _resolve_node_id(db, "plan_1", "plan_1_node_1") == "plan_1_node_1"


def test_resolve_node_id_accepts_original_node_id_alias():
    db = FakeDb({"plan_1_node_1"})

    assert _resolve_node_id(db, "plan_1", "node_1") == "plan_1_node_1"


def test_resolve_node_id_rejects_missing_node():
    db = FakeDb(set())

    with pytest.raises(HTTPException) as exc:
        _resolve_node_id(db, "plan_1", "missing")

    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "NODE_NOT_FOUND"

