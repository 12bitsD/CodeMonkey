from __future__ import annotations

import re
from pathlib import Path


def _concept_tree_root() -> Path:
    return Path(__file__).resolve().parents[1].parent.parent / "docs" / "spec"


def _load_backend_spec_text() -> str:
    """
    Load API spec from Epic contract files.

    The old '后端-通用规范.md' has been replaced by Epic-specific contract.md files.
    This test now reads from the Epic spec directory structure.
    """
    spec_path = _concept_tree_root()
    # Collect all contract.md files from epic directories
    contract_contents = []
    for epic_dir in spec_path.glob("epic-*"):
        contract_file = epic_dir / "contract.md"
        if contract_file.exists():
            contract_contents.append(contract_file.read_text(encoding="utf-8"))
    return "\n\n".join(contract_contents)


def _extract_documented_api_routes(spec_text: str) -> set[tuple[str, str]]:
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
    return {route for route in routes if route[1].startswith("/api/")}


def test_backend_spec_routes_cover_openapi_api_prefix():
    spec_routes = _only_api_prefix(
        _extract_documented_api_routes(_load_backend_spec_text())
    )
    openapi_routes = _only_api_prefix(_extract_openapi_routes())

    missing_in_spec = sorted(openapi_routes - spec_routes)
    message = "OpenAPI 路由未在 spec 接口清单出现: " + str(missing_in_spec)
    assert not missing_in_spec, message


def test_openapi_contains_all_implemented_spec_routes():
    spec_routes = _only_api_prefix(
        _extract_documented_api_routes(_load_backend_spec_text())
    )
    openapi_routes = _only_api_prefix(_extract_openapi_routes())

    missing_in_openapi = sorted(spec_routes - openapi_routes)
    message = "Spec 标记为已实现(非❌)但 OpenAPI 不存在: " + str(missing_in_openapi)
    assert not missing_in_openapi, message
