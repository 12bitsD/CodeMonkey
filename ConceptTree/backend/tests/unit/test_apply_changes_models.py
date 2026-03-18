import pytest
from pydantic import ValidationError
from models import GraphChanges, ClarifyGoalResponse


class TestGraphChanges:
    def test_default_empty_lists(self):
        changes = GraphChanges()
        assert changes.keep == []
        assert changes.remove == []
        assert changes.add == []

    def test_accepts_node_ids_in_keep_and_remove(self):
        changes = GraphChanges(keep=["n1", "n2"], remove=["n3"], add=["新节点名"])
        assert changes.keep == ["n1", "n2"]
        assert changes.remove == ["n3"]
        assert changes.add == ["新节点名"]

    def test_serializes_to_dict(self):
        changes = GraphChanges(keep=["n1"], remove=["n2"], add=["X"])
        d = changes.model_dump()
        assert d == {"keep": ["n1"], "remove": ["n2"], "add": ["X"]}


class TestClarifyGoalResponseWithChanges:
    def test_has_changes_field(self):
        data = {
            "interpretation": "新目标",
            "isLargeChange": False,
            "suggestion": "modify",
            "reason": "小幅调整",
            "changes": {
                "keep": ["n1"],
                "remove": ["n2"],
                "add": ["新概念"],
            },
        }
        resp = ClarifyGoalResponse(**data)
        assert resp.changes.keep == ["n1"]
        assert resp.changes.remove == ["n2"]
        assert resp.changes.add == ["新概念"]

    def test_changes_defaults_to_empty_when_omitted(self):
        data = {
            "interpretation": "新目标",
            "isLargeChange": True,
            "suggestion": "create_new",
            "reason": "完全不同",
        }
        resp = ClarifyGoalResponse(**data)
        assert resp.changes.keep == []
        assert resp.changes.remove == []
        assert resp.changes.add == []

    def test_large_change_with_summary_counts(self):
        data = {
            "interpretation": "全新方向",
            "isLargeChange": True,
            "suggestion": "create_new",
            "reason": "主题完全不同",
            "changes": {"keep": ["n1"], "remove": ["n2", "n3"], "add": []},
        }
        resp = ClarifyGoalResponse(**data)
        assert resp.isLargeChange is True
        assert len(resp.changes.remove) == 2
