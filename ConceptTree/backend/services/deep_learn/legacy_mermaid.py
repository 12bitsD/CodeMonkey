"""Safe adapter for the small flowchart subset produced by older sessions."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import ValidationError

from models_memory import DiagramSpec

_HEADER = re.compile(r"^(?:graph|flowchart)\s+(LR|RL|TD|TB|BT)$", re.IGNORECASE)
_TOKEN = r"([A-Za-z][A-Za-z0-9_-]{0,31})(?:\[([^\]\n]{1,64})\]|\(([^)\n]{1,64})\)|\{([^}\n]{1,64})\})?"
_EDGE = re.compile(rf"^\s*{_TOKEN}\s*(-->|---|-\.->|<-->)\s*{_TOKEN}\s*$")


def _label(node_id: str, *labels: Optional[str]) -> str:
    return next((value.strip() for value in labels if value and value.strip()), node_id)


def convert_legacy_mermaid(code: object) -> Optional[dict]:
    if not isinstance(code, str) or len(code.encode("utf-8")) > 8 * 1024:
        return None
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    header = _HEADER.fullmatch(lines[0])
    if not header:
        return None

    node_labels: dict[str, str] = {}
    edges: list[dict] = []
    for line in lines[1:]:
        match = _EDGE.fullmatch(line)
        if not match:
            return None
        (
            source,
            source_square,
            source_round,
            source_brace,
            arrow,
            target,
            target_square,
            target_round,
            target_brace,
        ) = match.groups()
        node_labels.setdefault(source, _label(source, source_square, source_round, source_brace))
        target_label = _label(target, target_square, target_round, target_brace)
        if target not in node_labels or target_label != target:
            node_labels[target] = target_label
        relation = {
            "-->": "sequence",
            "---": "related",
            "-.->": "related",
            "<-->": "contrasts",
        }[arrow]
        edges.append({"source": source, "target": target, "relation": relation})

    nodes = [
        {
            "id": node_id,
            "title": title[:32],
            "summary": title[:96],
            "role": "core" if index == 0 else "support",
            "details": {"key_points": []},
        }
        for index, (node_id, title) in enumerate(node_labels.items())
    ]
    try:
        spec = DiagramSpec(
            version=1,
            title="旧版知识关系图",
            layout="flow" if header.group(1).upper() in ("LR", "RL") else "hierarchy",
            nodes=nodes,
            edges=edges,
        )
    except ValidationError:
        return None
    return spec.model_dump(mode="json", exclude_none=True)


def normalize_legacy_visual_turns(turns: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for turn in turns:
        if turn.get("kind") == "illustration_offer":
            content = turn.get("content")
            caption = content.get("caption", "") if isinstance(content, dict) else ""
            normalized.append({**turn, "content": {"caption": caption}})
            continue
        if turn.get("kind") != "mermaid":
            normalized.append(turn)
            continue
        spec = convert_legacy_mermaid(turn.get("content"))
        if spec:
            normalized.append({**turn, "kind": "diagram", "content": spec})
        else:
            normalized.append({
                "id": turn.get("id"),
                "role": turn.get("role", "assistant"),
                "kind": "legacy_diagram_unavailable",
                "content": None,
            })
    return normalized
