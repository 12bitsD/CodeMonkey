import json
from pathlib import Path
from typing import Dict, Tuple, Any


class ConfigLoadError(Exception):
    pass


def load_ai_config(
    config_name: str, user_input: str, **kwargs
) -> Tuple[Dict[str, Any], str, str]:
    """
    Load AI configuration from JSON and assemble the final prompts.

    Args:
        config_name: Name of the config file (without .json extension)
        user_input: The primary user input / learning goal
        **kwargs: Additional dynamic variables (e.g., original_input, background)

    Returns:
        (model_params, system_prompt, user_prompt)
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
