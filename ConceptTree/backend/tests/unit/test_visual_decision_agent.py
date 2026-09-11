import pytest

import services.deep_learn.agents.visual_decision as visual_module
from services.deep_learn.agents.visual_decision import VisualDecisionAgent


pytestmark = pytest.mark.no_db


@pytest.mark.asyncio
async def test_visual_decision_agent_returns_a_valid_diagram_in_the_requested_language(monkeypatch):
    calls = []

    class FakeClient:
        async def chat_json(self, system, user, **kwargs):
            calls.append((system, user, kwargs))
            return {
                "visual_type": "diagram",
                "diagram": {
                    "version": 1,
                    "title": "导数关系图",
                    "layout": "flow",
                    "nodes": [
                        {"id": "secant", "title": "割线", "summary": "平均变化", "details": {}},
                        {"id": "tangent", "title": "切线", "summary": "瞬时变化", "role": "core", "details": {}},
                    ],
                    "edges": [
                        {"source": "secant", "target": "tangent", "relation": "prerequisite", "label": "取极限"},
                    ],
                },
                "illustration_prompt": None,
                "caption": None,
                "reason": "关系结构适合图示",
            }

    monkeypatch.setattr(visual_module, "get_llm_client", lambda: FakeClient())

    decision = await VisualDecisionAgent().decide(
        teaching_content="让割线两点无限接近，就得到切线。",
        concept="导数",
        node_name="微积分",
        language="zh-CN",
    )

    assert decision.visual_type == "diagram"
    assert decision.diagram.title == "导数关系图"
    assert "zh-CN" in calls[0][1]


@pytest.mark.asyncio
async def test_visual_decision_agent_fails_closed_on_an_invalid_graph(monkeypatch):
    class FakeClient:
        async def chat_json(self, *_args, **_kwargs):
            return {
                "visual_type": "diagram",
                "diagram": {
                    "version": 1,
                    "title": "坏图",
                    "layout": "flow",
                    "nodes": [
                        {"id": "only", "title": "唯一节点", "summary": "不够", "details": {}},
                    ],
                    "edges": [],
                },
                "reason": "invalid",
            }

    monkeypatch.setattr(visual_module, "get_llm_client", lambda: FakeClient())

    decision = await VisualDecisionAgent().decide(
        teaching_content="内容",
        concept="概念",
        node_name="节点",
        language="zh-CN",
    )

    assert decision.visual_type == "none"
    assert decision.diagram is None
