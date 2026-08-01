import json

import pytest

from services.deep_learn.agents.note_generator import _CONFIG_PATH as NOTE_CONFIG_PATH
from services.deep_learn.memory.update_agent import _CONFIG_PATH as MEMORY_CONFIG_PATH


pytestmark = pytest.mark.no_db


@pytest.mark.parametrize("config_path", [NOTE_CONFIG_PATH, MEMORY_CONFIG_PATH])
def test_deep_learn_prompt_config_exists_and_is_valid_json(config_path):
    with open(config_path, encoding="utf-8") as config_file:
        config = json.load(config_file)

    assert config["system_prompt"]
    assert config["model_params"]
