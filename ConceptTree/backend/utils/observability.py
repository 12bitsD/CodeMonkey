from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock
from typing import Any

_LOCK = Lock()
_DB_ERROR_COUNTS: Counter[str] = Counter()
_REQUEST_METRICS: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "count": 0,
        "errorCount": 0,
        "totalLatencyMs": 0.0,
        "maxLatencyMs": 0.0,
    }
)


def record_db_error(code: str) -> None:
    with _LOCK:
        _DB_ERROR_COUNTS[code] += 1


def record_request(
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
) -> None:
    key = f"{method.upper()} {route}"
    with _LOCK:
        item = _REQUEST_METRICS[key]
        item["count"] += 1
        if status_code >= 500:
            item["errorCount"] += 1
        item["totalLatencyMs"] += duration_ms
        item["maxLatencyMs"] = max(item["maxLatencyMs"], duration_ms)


def get_metrics_snapshot() -> dict[str, Any]:
    with _LOCK:
        request_metrics = {}
        for key, item in _REQUEST_METRICS.items():
            count = item["count"]
            avg_latency_ms = item["totalLatencyMs"] / count if count else 0.0
            request_metrics[key] = {
                "count": count,
                "errorCount": item["errorCount"],
                "avgLatencyMs": round(avg_latency_ms, 2),
                "maxLatencyMs": round(item["maxLatencyMs"], 2),
            }
        return {
            "dbErrorCounts": dict(_DB_ERROR_COUNTS),
            "requests": request_metrics,
        }


def reset_observability_for_tests() -> None:
    with _LOCK:
        _DB_ERROR_COUNTS.clear()
        _REQUEST_METRICS.clear()
