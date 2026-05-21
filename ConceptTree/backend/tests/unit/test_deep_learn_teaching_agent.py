import pytest

import services.deep_learn.agents.teaching as teaching_module
from services.deep_learn.agents.teaching import (
    TeachingAgent,
    _extract_json_string_value,
)


pytestmark = pytest.mark.no_db


def test_extract_json_string_value_decodes_partial_content():
    partial, complete = _extract_json_string_value('{"content":"第一句\\n第二', "content")
    assert partial == "第一句\n第二"
    assert complete is False

    full, complete = _extract_json_string_value('{"content":"第一句\\n第二句","questions":[]}', "content")
    assert full == "第一句\n第二句"
    assert complete is True


@pytest.mark.asyncio
async def test_teaching_agent_stream_run_emits_content_before_done(monkeypatch):
    class FakeClient:
        async def chat_stream(self, *_args, **_kwargs):
            yield '{"content":"第一'
            yield '句。第二句。","questions":["诊断题","应用题","变式题"]}'

    monkeypatch.setattr(teaching_module, "get_llm_client", lambda: FakeClient())

    events = []
    async for event in TeachingAgent().stream_run(
        node_name="节点",
        node_why="",
        current_concept="概念",
        concept_index=0,
        total_concepts=1,
        difficulty_level=3,
        weak_points=[],
        recent_turns=[],
        mode="normal",
    ):
        events.append(event)

    assert events[0] == {"type": "content", "text": "第一"}
    assert events[1] == {"type": "content", "text": "句。第二句。"}
    assert events[-1]["type"] == "done"
    assert events[-1]["output"].questions == ["诊断题", "应用题", "变式题"]
