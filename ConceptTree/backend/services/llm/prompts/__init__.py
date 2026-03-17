"""Prompt templates for LLM operations"""

import os
from pathlib import Path


def load_prompt(name: str) -> str:
    """Load prompt template by name"""
    prompt_dir = Path(__file__).parent
    prompt_file = prompt_dir / f"{name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {name}")

    return prompt_file.read_text(encoding="utf-8")


# Available prompts
PARSE_GOAL_V1 = "parse_goal_v1"
GENERATE_GRAPH_V1 = "generate_graph_v1"

__all__ = ["load_prompt", "PARSE_GOAL_V1", "GENERATE_GRAPH_V1"]
