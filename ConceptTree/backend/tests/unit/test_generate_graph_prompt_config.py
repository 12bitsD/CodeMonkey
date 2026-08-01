import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_db


def _load_generate_graph_config():
    path = Path(__file__).resolve().parents[2] / "services/llm/configs/generate_graph.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_graph_what_prompt_uses_dynamic_concept_count():
    config = _load_generate_graph_config()
    node_example = config["output_format"]["nodes"][0]
    rules_text = " ".join(config.get("rules", []))

    assert len(node_example["what"]) != 3
    assert "not fixed to 3" in " ".join(node_example["what"]).lower()
    assert "Do NOT output exactly 3 items by default" in rules_text
    assert "Deep Learning uses every nodes[].what item as one separate concept lesson" in rules_text
    assert "5-8 items" in rules_text
