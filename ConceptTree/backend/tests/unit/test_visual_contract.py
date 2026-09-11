import pytest
from pydantic import ValidationError

from models_memory import DiagramSpec, VisualDecision


pytestmark = pytest.mark.no_db


def _diagram(**overrides):
    data = {
        "version": 1,
        "title": "导数的几何意义",
        "layout": "flow",
        "nodes": [
            {
                "id": "slope",
                "title": "割线斜率",
                "summary": "先观察两个点之间的平均变化率",
                "role": "support",
                "details": {"key_points": ["对应平均变化率"]},
            },
            {
                "id": "derivative",
                "title": "导数",
                "summary": "让两个点无限接近得到瞬时变化率",
                "role": "core",
                "details": {
                    "key_points": ["等于切线斜率"],
                    "example": "位移函数的导数是瞬时速度",
                    "misconception": "不是把两个很小的量直接相除",
                },
            },
        ],
        "edges": [
            {
                "source": "slope",
                "target": "derivative",
                "relation": "prerequisite",
                "label": "取极限",
            },
        ],
    }
    data.update(overrides)
    return data


def test_diagram_spec_accepts_a_small_valid_teaching_graph():
    spec = DiagramSpec(**_diagram())

    assert spec.nodes[1].details.example == "位移函数的导数是瞬时速度"
    assert spec.edges[0].target == "derivative"


@pytest.mark.parametrize(
    "nodes, edges",
    [
        (
            [
                {"id": "same", "title": "A", "summary": "A", "details": {}},
                {"id": "same", "title": "B", "summary": "B", "details": {}},
            ],
            [{"source": "same", "target": "same", "relation": "related"}],
        ),
        (
            _diagram()["nodes"],
            [{"source": "missing", "target": "derivative", "relation": "causes"}],
        ),
    ],
)
def test_diagram_spec_rejects_ambiguous_or_dangling_edges(nodes, edges):
    with pytest.raises(ValidationError):
        DiagramSpec(**_diagram(nodes=nodes, edges=edges))


def test_diagram_spec_rejects_oversized_graphs_and_invalid_ids():
    too_many_nodes = [
        {"id": f"node_{index}", "title": str(index), "summary": "摘要", "details": {}}
        for index in range(9)
    ]
    with pytest.raises(ValidationError):
        DiagramSpec(**_diagram(nodes=too_many_nodes))

    invalid = _diagram()
    invalid["nodes"][0]["id"] = "1 invalid"
    with pytest.raises(ValidationError):
        DiagramSpec(**invalid)


def test_visual_decision_requires_payload_matching_its_type():
    diagram = DiagramSpec(**_diagram())
    assert VisualDecision(
        visual_type="diagram",
        diagram=diagram,
        reason="关系结构有助于理解",
    ).diagram == diagram

    with pytest.raises(ValidationError):
        VisualDecision(visual_type="diagram", reason="缺少图")

    with pytest.raises(ValidationError):
        VisualDecision(
            visual_type="illustration",
            diagram=diagram,
            illustration_prompt="show a tangent",
            reason="状态冲突",
        )
