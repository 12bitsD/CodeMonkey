import pytest

import services.deep_learn.service as service_module
from models_deep_learn import SessionState
from services.deep_learn.service import DeepLearnService


pytestmark = pytest.mark.no_db


def _session(turns, **overrides):
    values = dict(
        id="session-1",
        user_id="user-1",
        node_id="node-1",
        plan_id="plan-1",
        state="QUESTIONING",
        current_concept_index=0,
        difficulty_level=3,
        wrong_count_current=0,
        concepts_status={"0": "current"},
        weak_points=[],
        recent_turns=turns,
        what_list=["空间梯度"],
        test_questions=[],
        test_current_index=0,
        test_results=[],
        status="in_progress",
    )
    values.update(overrides)
    return SessionState(**values)


@pytest.mark.asyncio
async def test_generate_illustration_requires_a_persisted_offer_and_appends_the_result(monkeypatch):
    appended = []

    class FakeLlm:
        async def generate_image(self, *, prompt):
            assert prompt == "3D mountain surface with directional slopes"
            return b"png-bytes"

    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    async def fake_upload(user_id, session_id, image_bytes):
        assert (user_id, session_id, image_bytes) == ("user-1", "session-1", b"png-bytes")
        return "/static/deep_learn_images/user-1/session-1/result.png"

    monkeypatch.setattr(service_module, "get_llm_client", lambda: FakeLlm())
    monkeypatch.setattr(service_module.image_storage, "upload_image", fake_upload)
    monkeypatch.setattr(service_module, "get_db_context", lambda: FakeDbContext())
    monkeypatch.setattr(
        service_module,
        "append_recent_turn",
        lambda _db, _sid, _uid, turn, **_kwargs: appended.append(turn),
    )

    session = _session([{
        "id": "offer-1",
        "role": "assistant",
        "kind": "illustration_offer",
        "content": {
            "caption": "生成三维坡面演示图",
            "prompt": "3D mountain surface with directional slopes",
        },
        "reason": "需要观察空间关系",
    }])

    result = await DeepLearnService().generate_illustration(session, "offer-1")

    assert result["url"].endswith("result.png")
    assert result["source_offer_id"] == "offer-1"
    assert appended[0]["kind"] == "dalle_image"


@pytest.mark.asyncio
async def test_generate_illustration_rejects_unknown_offers_and_session_limit(monkeypatch):
    class FailIfCalled:
        async def generate_image(self, **_kwargs):
            raise AssertionError("image model must not be called")

    monkeypatch.setattr(service_module, "get_llm_client", lambda: FailIfCalled())
    service = DeepLearnService()

    with pytest.raises(ValueError, match="offer"):
        await service.generate_illustration(_session([]), "missing")

    limited = _session([
        {
            "id": "offer-2",
            "role": "assistant",
            "kind": "illustration_offer",
            "content": {"caption": "演示", "prompt": "valid prompt"},
        },
        {
            "id": "image-1",
            "role": "assistant",
            "kind": "dalle_image",
            "content": "/static/old.png",
            "source_offer_id": "other-offer",
        },
    ])
    with pytest.raises(ValueError, match="limit"):
        await service.generate_illustration(limited, "offer-2")

    pruned_history = _session(
        [{
            "id": "offer-3",
            "role": "assistant",
            "kind": "illustration_offer",
            "content": {"caption": "演示", "prompt": "valid prompt"},
        }],
        conversation_summary="[illustration_generated]",
    )
    with pytest.raises(ValueError, match="limit"):
        await service.generate_illustration(pruned_history, "offer-3")
