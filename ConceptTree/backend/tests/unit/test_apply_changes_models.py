"""Pydantic model unit tests for GraphChanges and ClarifyGoalResponse.

These tests validate the data models used when a learner refines their goal and
the system calculates what to keep, remove, and add to the knowledge graph.
No database or HTTP calls are made — these are pure model validation tests.

This module validates:
1. GraphChanges initialises with empty lists by default.
2. GraphChanges stores and serialises node IDs correctly.
3. ClarifyGoalResponse includes a 'changes' field when provided.
4. ClarifyGoalResponse defaults to empty GraphChanges when 'changes' is omitted.
5. Large-change responses correctly reflect the remove list length.

Primary reader: a developer adding new fields to the apply-changes models or
debugging a Pydantic validation error in the clarify-goal / apply-changes flow.
"""

import pytest
from pydantic import ValidationError
from models import GraphChanges, ClarifyGoalResponse


class TestGraphChanges:
    def test_default_empty_lists(self):
        """GraphChanges initialises keep, remove, and add to empty lists by default.

        Constructing GraphChanges with no arguments must produce empty lists
        rather than None values that would break downstream JSON serialisation.
        Expected: keep=[], remove=[], add=[].
        """
        changes = GraphChanges()
        assert changes.keep == []
        assert changes.remove == []
        assert changes.add == []

    def test_accepts_node_ids_in_keep_and_remove(self):
        """GraphChanges stores node IDs in keep/remove and concept names in add.

        Expected: keep=['n1','n2'], remove=['n3'], add=['新节点名'].
        """
        changes = GraphChanges(keep=["n1", "n2"], remove=["n3"], add=["新节点名"])
        assert changes.keep == ["n1", "n2"]
        assert changes.remove == ["n3"]
        assert changes.add == ["新节点名"]

    def test_serializes_to_dict(self):
        """GraphChanges.model_dump() produces a plain dict with all three lists.

        Expected: {'keep': ['n1'], 'remove': ['n2'], 'add': ['X']}.
        """
        changes = GraphChanges(keep=["n1"], remove=["n2"], add=["X"])
        d = changes.model_dump()
        assert d == {"keep": ["n1"], "remove": ["n2"], "add": ["X"]}


class TestClarifyGoalResponseWithChanges:
    def test_has_changes_field(self):
        """ClarifyGoalResponse stores a nested GraphChanges when 'changes' is provided.

        Verifies that the nested model is parsed correctly and the individual
        lists are accessible on the result.
        Expected: changes.keep=['n1'], changes.remove=['n2'], changes.add=['新概念'].
        """
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
        """ClarifyGoalResponse creates an empty GraphChanges when 'changes' is omitted.

        The 'changes' field should not be required — when absent, the model
        must default to empty lists rather than raising a validation error.
        Expected: changes.keep=[], changes.remove=[], changes.add=[].
        """
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
        """A large-change response correctly stores a non-empty remove list.

        Tests a scenario where isLargeChange=True and two nodes are marked
        for removal. Verifies the model stores both IDs.
        Expected: isLargeChange=True, len(changes.remove)==2.
        """
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
