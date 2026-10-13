from datetime import datetime, timezone

import pytest

from services.admin.analytics import _decode_cursor, _encode_cursor, get_overview, mask_email


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Db:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return _Result(self.row)


@pytest.mark.no_db
def test_mask_email_keeps_domain_without_exposing_local_part():
    assert mask_email("victor@example.com") == "v***@example.com"
    assert mask_email("invalid") == "***"


@pytest.mark.no_db
def test_cursor_round_trip_and_invalid_cursor():
    cursor = _encode_cursor("2026-10-14T10:00:00+00:00", "user-1")
    assert _decode_cursor(cursor) == ("2026-10-14T10:00:00+00:00", "user-1")

    with pytest.raises(Exception) as exc:
        _decode_cursor("not-valid")
    assert exc.value.status_code == 400


@pytest.mark.no_db
def test_overview_calculates_completion_rate_and_numeric_cost():
    db = _Db(
        {
            "total_users": 12,
            "new_users": 3,
            "plans_created": 4,
            "active_plans": 5,
            "learning_events": 8,
            "deep_sessions": 4,
            "completed_sessions": 3,
            "notes_created": 2,
            "trace_errors": 1,
            "total_tokens": 1200,
            "estimated_cost_usd": "1.250000",
            "active_users": 6,
        }
    )
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 8, tzinfo=timezone.utc)

    result = get_overview(db, start, end)

    assert result["completion_rate"] == 0.75
    assert result["estimated_cost_usd"] == 1.25
    assert len(db.calls[0][1]) == 22
