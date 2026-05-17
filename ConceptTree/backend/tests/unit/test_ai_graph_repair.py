from models import GenerateGraphResponse, GraphEdge, GraphNode
from services.ai_service import _repair_generated_graph


def test_repair_generated_graph_uses_flagged_target_when_target_id_is_invalid():
    graph = GenerateGraphResponse(
        interpretation="repair target",
        targetNodeId="missing",
        nodes=[
            GraphNode(
                id="n1",
                name="基础",
                why="why",
                what=["what"],
                mastery=["mastery"],
                prompt="prompt",
                isTarget=False,
            ),
            GraphNode(
                id="n2",
                name="目标",
                why="why",
                what=["what"],
                mastery=["mastery"],
                prompt="prompt",
                isTarget=True,
            ),
        ],
        edges=[],
    )

    repaired = _repair_generated_graph(graph)

    assert repaired.targetNodeId == "n2"
    assert [node.isTarget for node in repaired.nodes] == [False, True]


def test_repair_generated_graph_filters_invalid_edges():
    graph = GenerateGraphResponse(
        interpretation="repair edges",
        targetNodeId="n2",
        nodes=[
            GraphNode(
                id="n1",
                name="基础",
                why="why",
                what=["what"],
                mastery=["mastery"],
                prompt="prompt",
            ),
            GraphNode(
                id="n2",
                name="目标",
                why="why",
                what=["what"],
                mastery=["mastery"],
                prompt="prompt",
            ),
        ],
        edges=[
            GraphEdge(from_node="n1", to_node="n2"),
            GraphEdge(from_node="n404", to_node="n2"),
        ],
    )

    repaired = _repair_generated_graph(graph)

    assert len(repaired.edges) == 1
    assert repaired.edges[0].from_node == "n1"
