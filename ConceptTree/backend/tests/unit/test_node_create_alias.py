from models import NodeCreate


def test_node_create_accepts_camel_case_is_target_alias():
    node = NodeCreate(
        name="目标节点",
        isTarget=True,
    )

    assert node.is_target is True
