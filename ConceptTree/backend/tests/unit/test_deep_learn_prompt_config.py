import json
from pathlib import Path


def test_teaching_prompt_uses_required_learning_constraints():
    path = Path(__file__).resolve().parents[2] / "services/llm/configs/deep_learn_teaching.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    prompt = config["system_prompt"]

    assert "疑问接力" in prompt
    assert "每次只攻一个核心概念" in prompt
    assert "三层水位校准" in prompt
    assert "工艺 + 效果双轨验收" in prompt
    assert "变式题" in prompt
    assert "仅返回合法 JSON" in prompt
