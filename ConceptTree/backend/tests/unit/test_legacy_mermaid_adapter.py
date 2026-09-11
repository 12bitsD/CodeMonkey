import pytest

from services.deep_learn.legacy_mermaid import (
    convert_legacy_mermaid,
    normalize_legacy_visual_turns,
)


pytestmark = pytest.mark.no_db


def test_converts_the_supported_legacy_lr_subset_to_a_diagram_spec():
    spec = convert_legacy_mermaid(
        "graph LR\n  concept[概念] --> mechanism[机制]\n  mechanism --> result[结果]"
    )

    assert spec is not None
    assert spec["layout"] == "flow"
    assert [node["title"] for node in spec["nodes"]] == ["概念", "机制", "结果"]
    assert spec["edges"][1] == {
        "source": "mechanism",
        "target": "result",
        "relation": "sequence",
    }


def test_rejects_unsupported_or_potentially_active_mermaid_syntax():
    assert convert_legacy_mermaid("sequenceDiagram\nA->>B: hello") is None
    assert convert_legacy_mermaid("graph LR\nclick A call dangerous()") is None
    assert convert_legacy_mermaid("graph LR\nA-->B\nB-->C\nstyle A fill:red") is None


def test_normalizes_legacy_turns_without_losing_unrenderable_history():
    normalized = normalize_legacy_visual_turns([
        {"role": "assistant", "kind": "mermaid", "content": "graph TD\nA[根]-->B[叶]"},
        {"role": "assistant", "kind": "mermaid", "content": "sequenceDiagram\nA->>B: hi"},
    ])

    assert normalized[0]["kind"] == "diagram"
    assert normalized[0]["content"]["layout"] == "hierarchy"
    assert normalized[1]["kind"] == "legacy_diagram_unavailable"
    assert "sequenceDiagram" not in str(normalized[1])


def test_hides_server_side_illustration_prompts_from_resumed_clients():
    normalized = normalize_legacy_visual_turns([{
        "id": "offer-1",
        "role": "assistant",
        "kind": "illustration_offer",
        "content": {"caption": "演示空间关系", "prompt": "private generation prompt"},
    }])

    assert normalized[0]["content"] == {"caption": "演示空间关系"}
