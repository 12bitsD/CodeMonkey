from decimal import Decimal

import pytest

from services.admin import tracing


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _Db:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return _Rows(self.rows)


@pytest.mark.no_db
def test_trace_events_require_session_context(monkeypatch):
    monkeypatch.setattr(tracing, "start_trace_buffer", lambda: None)
    assert tracing.emit_trace_event(event_type="llm", event_name="chat") is False

    captured = []
    monkeypatch.setattr(tracing._QUEUE, "put_nowait", captured.append)
    with tracing.trace_scope(session_id="session-1", user_id="user-1", request_id="req-1"):
        accepted = tracing.emit_trace_event(
            event_type="llm",
            event_name="chat",
            redacted_input="x" * 800,
        )

    assert accepted is True
    assert captured[0]["session_id"] == "session-1"
    assert captured[0]["request_id"] == "req-1"
    assert len(captured[0]["redacted_input"]) == 500


@pytest.mark.no_db
def test_trace_query_returns_safe_camel_case_shape():
    db = _Db(
        [
            {
                "id": "event-1",
                "session_id": "session-1",
                "request_id": "req-1",
                "event_type": "llm",
                "event_name": "chat",
                "status": "ok",
                "duration_ms": 120.5,
                "provider": "kimi",
                "model": "kimi-k3",
                "input_tokens": 12,
                "output_tokens": 34,
                "estimated_cost_usd": Decimal("0.0123"),
                "retry_count": 0,
                "error_code": None,
                "attributes": {"agent": "teaching"},
                "redacted_input": None,
                "redacted_output": None,
                "created_at": "2026-10-14T00:00:00Z",
            }
        ]
    )

    result = tracing.list_session_trace(db, "session-1", limit=100, cursor=None)
    events = result["items"]

    assert events[0]["estimatedCostUsd"] == 0.0123
    assert events[0]["attributes"] == {"agent": "teaching"}
    assert db.calls[0][1] == ("session-1", None, None, None, 101)
    assert result["nextCursor"] is None


@pytest.mark.no_db
def test_trace_cursor_round_trip_and_invalid_cursor():
    cursor = tracing._encode_trace_cursor("2026-10-14T10:00:00+00:00", "event-1")
    assert tracing._decode_trace_cursor(cursor) == (
        "2026-10-14T10:00:00+00:00",
        "event-1",
    )

    with pytest.raises(Exception) as exc:
        tracing._decode_trace_cursor("not-valid")
    assert exc.value.status_code == 400


@pytest.mark.no_db
def test_trace_persistence_failure_is_fail_open(monkeypatch):
    class _FailingContext:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(tracing, "get_db_context", lambda: _FailingContext())

    # Trace storage is diagnostic-only and must never fail a learner request.
    tracing._persist_batch([{"event_type": "interaction"}])
