from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from routers.graph import _normalize_node_target_end_date

pytestmark = pytest.mark.no_db


def test_node_target_end_date_allows_today():
    today = date.today().isoformat()

    assert _normalize_node_target_end_date(today) == today


def test_node_target_end_date_allows_future_date():
    future = (date.today() + timedelta(days=7)).isoformat()

    assert _normalize_node_target_end_date(future) == future


def test_node_target_end_date_rejects_past_date():
    past = (date.today() - timedelta(days=1)).isoformat()

    with pytest.raises(HTTPException) as exc:
        _normalize_node_target_end_date(past)

    assert exc.value.status_code == 400
    assert exc.value.detail["error"]["code"] == "TARGET_END_DATE_IN_PAST"


def test_node_target_end_date_rejects_invalid_text():
    with pytest.raises(HTTPException) as exc:
        _normalize_node_target_end_date("not-a-date")

    assert exc.value.status_code == 400
    assert exc.value.detail["error"]["code"] == "INVALID_TARGET_END_DATE"


def test_node_target_end_date_allows_clear():
    assert _normalize_node_target_end_date("") is None
    assert _normalize_node_target_end_date(None) is None
