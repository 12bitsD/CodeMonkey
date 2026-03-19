"""Loads prompt configs from JSON files and assembles ready-to-use LLM prompts.

Each AI operation in ConceptTree has a corresponding JSON config file in this
directory (e.g. ``parse_goal.json``).  This module reads the config and builds
the final ``system_prompt`` and ``user_prompt`` strings that are sent to the
LLM, so no prompt text is hard-coded in the service layer.

Primary reader: backend developer adding a new AI operation or debugging why
a prompt does not look as expected.

Key things to understand:
  1. **Config discovery** — config files live in the same directory as this
     ``__init__.py``; they are resolved at call time, not at import time.
  2. **Placeholder rendering** — ``{{key}}`` tokens in ``system_prompt`` are
     replaced by matching ``kwargs`` before the prompt is used.
  3. **User prompt assembly** — the user prompt is built in five ordered
     sections: ``Input``, dynamic kwargs (not consumed by system_prompt),
     ``Output Format``, ``Rules``, and ``Examples``.
"""

import json
from pathlib import Path
from typing import Dict, Tuple, Any


class ConfigLoadError(Exception):
    """Raised when a prompt config file cannot be loaded or parsed.

    Thrown by :func:`load_ai_config` in two cases:

    - The requested config file does not exist on disk.
    - The file exists but contains malformed JSON.
    """

    pass


def load_ai_config(
    config_name: str, user_input: str, **kwargs
) -> Tuple[Dict[str, Any], str, str]:
    """Load a named prompt config and return ready-to-use prompts.

    Reads ``<config_name>.json`` from this directory, renders any
    ``{{key}}`` placeholders in the ``system_prompt`` using ``kwargs``,
    and assembles the ``user_prompt`` from five ordered sections.

    **User prompt structure** (sections are appended in this order):

    1. ``## Input`` — always includes ``user_input`` and any ``kwargs`` that
       were *not* consumed as ``{{key}}`` placeholders in ``system_prompt``.
    2. ``## Output Format`` — if the config has an ``output_format`` key,
       the expected JSON schema is included verbatim so the LLM knows
       exactly what fields to return.
    3. ``## Rules`` — if the config has a ``rules`` list, each rule is
       appended as a bullet point.
    4. ``## Examples`` — if the config has an ``examples`` list, each
       example's ``input`` / ``output`` is appended.
    5. A final instruction: ``"Respond ONLY with the JSON object…"``.

    Args:
        config_name: Name of the config file without the ``.json`` extension,
            e.g. ``"parse_goal"`` → reads ``parse_goal.json``.
        user_input: The primary user input or learning goal.  Always appears
            under ``## Input`` in the assembled user prompt.
        **kwargs: Additional dynamic variables.  Each key matching a
            ``{{key}}`` placeholder in ``system_prompt`` is substituted
            there.  Any remaining kwargs (not consumed by system_prompt) are
            appended as extra lines under ``## Input``.

    Returns:
        A 3-tuple ``(model_params, system_prompt, user_prompt)`` where:

        - ``model_params`` is the ``model_params`` dict from the JSON config
          (contains keys like ``temperature`` and ``max_tokens``).
        - ``system_prompt`` is the rendered system message string.
        - ``user_prompt`` is the fully assembled user message string.

    Raises:
        ConfigLoadError: The config file does not exist, or its JSON is
            malformed.
    """
    config_dir = Path(__file__).parent
    config_file = config_dir / f"{config_name}.json"

    if not config_file.exists():
        raise ConfigLoadError(f"Configuration file not found: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in {config_file}: {str(e)}")

    model_params = config.get("model_params", {})
    system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

    # Allow placeholder rendering in system_prompt using {{key}} syntax
    for k, v in kwargs.items():
        placeholder = f"{{{{{k}}}}}"
        if placeholder in system_prompt:
            system_prompt = system_prompt.replace(placeholder, str(v))

    # Assemble user prompt
    parts = []
    parts.append("## Input")
    parts.append(f"User input: {user_input}")

    # Append any dynamic kwargs that were NOT consumed by system_prompt placeholders
    for k, v in kwargs.items():
        if f"{{{{{k}}}}}" not in config.get("system_prompt", ""):
            parts.append(f"{k}: {v}")

    if "output_format" in config:
        parts.append("\n## Output Format")
        parts.append("Return ONLY a JSON object with this exact structure:")
        parts.append(json.dumps(config["output_format"], indent=2, ensure_ascii=False))

    if "rules" in config and config["rules"]:
        parts.append("\n## Rules")
        for rule in config["rules"]:
            parts.append(f"- {rule}")

    if "examples" in config and config["examples"]:
        parts.append("\n## Examples")
        for ex in config["examples"]:
            parts.append(f"Input: {ex.get('input', '')}")
            if "output" in ex:
                output = ex["output"]
                if isinstance(output, (dict, list)):
                    parts.append(f"Output: {json.dumps(output, ensure_ascii=False)}")
                else:
                    parts.append(f"Output: {output}")
            parts.append("")

    parts.append(
        "\nRespond ONLY with the JSON object, no markdown formatting, no explanation."
    )

    user_prompt = "\n".join(parts)

    return model_params, system_prompt, user_prompt


__all__ = ["load_ai_config", "ConfigLoadError"]
