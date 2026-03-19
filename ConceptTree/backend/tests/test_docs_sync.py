"""Documentation sync test: the backend spec and OpenAPI schema must agree on all API routes.

This module acts as a living contract between the written specification
(``backend/spec/后端-通用规范.md``) and the FastAPI application's actual route
definitions (exposed via OpenAPI). Two invariants are enforced:

1. Every route that the OpenAPI schema exposes under /api/ must also appear
   in the spec's '接口完整清单' (Interface Complete List) table.
2. Every route in that table that is not marked as unimplemented (❌) must
   also exist in the OpenAPI schema.

If either invariant fails, the test message includes the list of diverging
routes so the developer can see exactly what is missing.

Primary reader: a developer adding or renaming an endpoint, ensuring that
the spec document stays in sync with the actual implementation.
"""

from __future__ import annotations

import re
from pathlib import Path


def _concept_tree_root() -> Path:
    """Return the root path of the backend directory (parent of this file's directory)."""
    return Path(__file__).resolve().parents[1]


def _load_backend_spec_text() -> str:
    """Return the full text of the backend general specification markdown file."""
    spec_path = _concept_tree_root() / "spec" / "后端-通用规范.md"
    return spec_path.read_text(encoding="utf-8")


def _extract_documented_api_routes(spec_text: str) -> set[tuple[str, str]]:
    """Parse the '接口完整清单' table from the spec and return (METHOD, path) pairs.

    Rows marked with ❌ in the status column (meaning 'not yet implemented') are
    excluded — only routes that are supposed to be live are returned. Routes with
    methods outside GET/POST/PUT/DELETE are also excluded.
    """
    routes: set[tuple[str, str]] = set()
    in_api_tables = False

    for raw_line in spec_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## 接口完整清单"):
            in_api_tables = True
            continue
        if in_api_tables and line.startswith("## "):
            break
        if not in_api_tables:
            continue
        if not line.startswith("|"):
            continue
        if "方法" in line and "路由" in line and "状态" in line:
            continue
        if line.startswith("| ----"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 6:
            continue
        method = cells[0].upper()
        route_cell = cells[1]
        status = cells[5]

        if method not in {"GET", "POST", "PUT", "DELETE"}:
            continue
        if status == "❌":
            continue

        match = re.search(r"`([^`]+)`", route_cell)
        if not match:
            continue
        path = match.group(1).strip()
        routes.add((method, path))

    return routes


def _extract_openapi_routes() -> set[tuple[str, str]]:
    """Return all (METHOD, path) pairs from the FastAPI application's OpenAPI schema."""
    from main import app

    openapi = app.openapi()
    paths = openapi.get("paths", {})
    routes: set[tuple[str, str]] = set()
    for path, operations in paths.items():
        for method in operations.keys():
            upper = method.upper()
            if upper in {"GET", "POST", "PUT", "DELETE"}:
                routes.add((upper, path))
    return routes


def _only_api_prefix(routes: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """Filter route pairs to only those whose path starts with /api/."""
    return {route for route in routes if route[1].startswith("/api/")}


def test_backend_spec_routes_cover_openapi_api_prefix():
    """Every /api/ route in OpenAPI must also appear in the backend spec table.

    If a developer adds a new endpoint but forgets to document it, this test
    fails and lists the undocumented routes.
    Expected: no routes in OpenAPI that are missing from the spec.
    """
    spec_routes = _only_api_prefix(
        _extract_documented_api_routes(_load_backend_spec_text())
    )
    openapi_routes = _only_api_prefix(_extract_openapi_routes())

    missing_in_spec = sorted(openapi_routes - spec_routes)
    message = "OpenAPI 路由未在 spec 接口清单出现: " + str(missing_in_spec)
    assert not missing_in_spec, message


def test_openapi_contains_all_implemented_spec_routes():
    """Every implemented /api/ route in the spec must also exist in OpenAPI.

    If a developer removes an endpoint or changes its path, but forgets to
    update the spec, this test fails and lists the orphaned spec entries.
    Expected: no non-❌ spec routes that are absent from OpenAPI.
    """
    spec_routes = _only_api_prefix(
        _extract_documented_api_routes(_load_backend_spec_text())
    )
    openapi_routes = _only_api_prefix(_extract_openapi_routes())

    missing_in_openapi = sorted(spec_routes - openapi_routes)
    message = "Spec 标记为已实现(非❌)但 OpenAPI 不存在: " + str(
        missing_in_openapi
    )
    assert not missing_in_openapi, message
