import pytest

from models_deep_learn import SessionState
from models_deep_learn import AssessmentOverallOutput, AssessmentPerQuestionOutput, TeachingOutput
import services.deep_learn.service as service_module
from services.deep_learn.service import (
    DeepLearnService,
    _split_text_for_streaming,
    _sse,
)


pytestmark = pytest.mark.no_db


def _session(state="INITIALIZING"):
    return SessionState(
        id="session-1",
        user_id="user-1",
        node_id="node-1",
        plan_id="plan-1",
        state=state,
        current_concept_index=0,
        difficulty_level=3,
        wrong_count_current=0,
        concepts_status={},
        weak_points=[],
        recent_turns=[],
        what_list=["概念一"],
        test_questions=[],
        test_current_index=0,
        test_results=[],
        status="in_progress",
    )


async def _collect(generator):
    return [event async for event in generator]


@pytest.mark.asyncio
async def test_localize_node_meta_translates_historical_chinese_content_for_english(monkeypatch):
    calls = []

    class FakeLlm:
        async def chat_json(self, system, user, **kwargs):
            calls.append((system, user, kwargs))
            return {
                "node_name": "Numerical gradient checking",
                "node_why": "Verify analytical gradients before training.",
                "what_list": [
                    "Finite-difference derivative approximation",
                    "Centered versus one-sided differences",
                ],
            }

    monkeypatch.setattr(service_module, "get_llm_client", lambda: FakeLlm())
    service = DeepLearnService()
    source = {
        "node_name": "梯度数值检验",
        "node_why": "验证解析梯度",
        "what_list": ["有限差分近似导数", "中心差分与单边差分"],
    }

    localized = await service.localize_node_meta(source, "en-US")
    cached = await service.localize_node_meta(source, "en-US")

    assert localized["node_name"] == "Numerical gradient checking"
    assert localized["what_list"] == [
        "Finite-difference derivative approximation",
        "Centered versus one-sided differences",
    ]
    assert cached == localized
    assert len(calls) == 1


def test_split_text_for_streaming_returns_multiple_chunks():
    chunks = _split_text_for_streaming("第一句很短。第二句也会独立推送。第三句继续用于验证。", chunk_size=12)

    assert len(chunks) > 1
    assert "".join(chunks) == "第一句很短。第二句也会独立推送。第三句继续用于验证。"


@pytest.mark.asyncio
async def test_initialize_stream_always_ends_with_done():
    service = DeepLearnService()

    async def fake_run_teach(_session, _node_meta, mode, background_tasks=None):
        yield _sse("chunk", text="hello")

    service._run_teach = fake_run_teach

    events = await _collect(service.stream_initialize(_session(), {"node_name": "n"}))

    assert events[0] == _sse("chunk", text="hello")
    assert events[-1] == _sse("done")


@pytest.mark.asyncio
async def test_initialize_invalid_state_still_ends_with_done():
    service = DeepLearnService()

    events = await _collect(service.stream_initialize(_session("QUESTIONING"), {}))

    assert any('"type": "error"' in event for event in events)
    assert events[-1] == _sse("done")


@pytest.mark.asyncio
async def test_run_teach_streams_content_in_multiple_chunks(monkeypatch):
    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    service = DeepLearnService()

    async def fake_stream_run(**_kwargs):
        yield {"type": "content", "text": "第一段内容"}
        yield {"type": "content", "text": "继续流式输出"}
        yield {
            "type": "done",
            "output": TeachingOutput(content="第一段内容继续流式输出", questions=[]),
        }

    monkeypatch.setattr(service_module, "get_db_context", lambda: FakeDbContext())
    monkeypatch.setattr(service_module, "update_session", lambda *_args, **_kwargs: None)
    service.teaching_agent.stream_run = fake_stream_run

    events = await _collect(
        service._run_teach(
            _session(),
            {"node_name": "节点", "node_why": "", "what_list": ["概念"]},
            mode="normal",
        ),
    )

    chunk_events = [event for event in events if '"type": "chunk"' in event]
    assert any('"type": "assistant_start"' in event for event in events)
    assert len(chunk_events) > 1


@pytest.mark.asyncio
async def test_run_teach_persists_questions_for_session_resume(monkeypatch):
    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    updated = {}
    service = DeepLearnService()

    async def fake_stream_run(**_kwargs):
        yield {"type": "content", "text": "核心讲解"}
        yield {
            "type": "done",
            "output": TeachingOutput(content="核心讲解", questions=["诊断题", "应用题", "变式题"]),
        }

    def fake_update(_db, _session_id, **fields):
        updated.update(fields)

    monkeypatch.setattr(service_module, "get_db_context", lambda: FakeDbContext())
    monkeypatch.setattr(service_module, "update_session", fake_update)
    service.teaching_agent.stream_run = fake_stream_run

    session = _session()
    events = await _collect(
        service._run_teach(
            session,
            {"node_name": "节点", "node_why": "", "what_list": ["概念"]},
            mode="normal",
        ),
    )

    assert any('"type": "questions"' in event for event in events)
    assert updated["recent_turns"][-1] == {
        "role": "assistant",
        "kind": "questions",
        "content": ["诊断题", "应用题", "变式题"],
    }


@pytest.mark.asyncio
async def test_failed_concept_emits_failed_status(monkeypatch):
    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    updated = {}
    service = DeepLearnService()

    async def fake_assessment_run(**_kwargs):
        return AssessmentPerQuestionOutput(
            is_correct=False,
            quality_score=0.2,
            explanation="还没通过",
            feedback="需要复习",
            update_weak_points=["薄弱点"],
            wrong_count=1,
        )

    def fake_update(_db, _session_id, **fields):
        updated.update(fields)

    monkeypatch.setattr(service_module, "get_db_context", lambda: FakeDbContext())
    monkeypatch.setattr(service_module, "update_session", fake_update)
    service.assessment_per_q.run = fake_assessment_run

    session = _session("QUESTIONING")
    session.concepts_status = {"0": "current"}
    events = await _collect(
        service._run_assessment(
            session,
            {"node_name": "节点", "node_why": "", "what_list": ["概念"]},
            "错误回答",
            False,
        ),
    )

    assert updated["concepts_status"] == {"0": "failed"}
    assert any('"type": "concept_update"' in event and '"status": "failed"' in event for event in events)


@pytest.mark.asyncio
async def test_last_concept_correct_enters_test_confirmation_without_completion_gate(monkeypatch):
    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    updates = []
    service = DeepLearnService()

    async def fake_assessment_run(**_kwargs):
        return AssessmentPerQuestionOutput(
            is_correct=True,
            quality_score=0.95,
            explanation="correct",
            feedback="ready",
            update_weak_points=[],
            difficulty_delta=0,
            wrong_count=0,
        )

    async def fake_readiness_run(**_kwargs):
        return AssessmentOverallOutput(
            passed=True,
            confidence=0.9,
            ready_for_test=True,
            reason="all concepts are covered",
            strong_areas=["concepts"],
            weak_areas=[],
            suggest_review_concepts=[],
        )

    def fake_update(_db, _session_id, **fields):
        updates.append(fields)

    monkeypatch.setattr(service_module, "get_db_context", lambda: FakeDbContext())
    monkeypatch.setattr(service_module, "update_session", fake_update)
    service.assessment_per_q.run = fake_assessment_run
    service.assessment_overall.run_readiness = fake_readiness_run

    session = _session("QUESTIONING")
    session.what_list = ["concept one", "concept two"]
    session.current_concept_index = 1
    session.concepts_status = {"0": "done", "1": "current"}

    events = await _collect(
        service._run_assessment(
            session,
            {"node_name": "node", "node_why": "", "what_list": session.what_list},
            "correct answer",
            False,
        ),
    )

    assert any('"type": "concept_update"' in event and '"index": 1' in event and '"status": "done"' in event for event in events)
    assert any('"type": "state_change"' in event and '"to": "AI_ASSESSING_READINESS"' in event for event in events)
    assert any('"type": "state_change"' in event and '"to": "CONFIRMING_TEST"' in event for event in events)
    assert any('"type": "test_confirm_prompt"' in event and '"confirm_test"' in event for event in events)
    assert not any('"type": "show_commands"' in event for event in events)
    assert any(update.get("state") == "CONFIRMING_TEST" for update in updates)
