import json
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[1] / "services" / "llm" / "configs"


def _load_config(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def test_explain_topic_config_uses_runtime_model():
    config = _load_config("explain_topic.json")
    assert "model" not in config.get("model_params", {})


def test_chat_config_uses_runtime_model():
    config = _load_config("chat.json")
    assert "model" not in config.get("model_params", {})
