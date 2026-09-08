import pytest

from services.deep_learn.agents.note_generator import _summarize_turns


pytestmark = pytest.mark.no_db


def test_note_summary_excludes_all_visual_payloads():
    summary = _summarize_turns([
        {"role": "assistant", "kind": "text", "content": "核心讲解"},
        {"role": "assistant", "kind": "diagram", "content": {"title": "秘密大图"}},
        {"role": "assistant", "kind": "illustration_offer", "content": {"prompt": "expensive prompt"}},
        {"role": "assistant", "kind": "dalle_image", "content": "/static/image.png"},
    ])

    assert "核心讲解" in summary
    assert "秘密大图" not in summary
    assert "expensive prompt" not in summary
    assert "/static/image.png" not in summary
