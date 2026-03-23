from models import Edge


def test_edge_accepts_frontend_from_to_fields():
    edge = Edge.model_validate({"from": "n1", "to": "n2"})
    assert edge.from_ == "n1"
    assert edge.to_ == "n2"


def test_edge_serializes_as_frontend_from_to_fields():
    edge = Edge(from_="n1", to_="n2")
    assert edge.model_dump(by_alias=True) == {"from": "n1", "to": "n2"}
