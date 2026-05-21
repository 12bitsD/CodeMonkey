"""Phase 2 Memory System — Pydantic models"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ProceduralPatternKey = Literal[
    "effective_analogy_type",
    "optimal_question_density",
    "preferred_explanation_order",
    "common_misconception_pattern",
    "ideal_pace",
]

_PROCEDURAL_KEY_VALUES: dict[str, set[str]] = {
    "effective_analogy_type": {"code", "math", "daily", "visual"},
    "optimal_question_density": {"1", "2", "3"},
    "preferred_explanation_order": {"concrete_first", "abstract_first"},
    "common_misconception_pattern": set(),  # free text
    "ideal_pace": {"slow", "normal", "fast"},
}

VALID_PROCEDURAL_KEYS: set[str] = set(_PROCEDURAL_KEY_VALUES.keys())


class LongTermMemory(BaseModel):
    user_id: str
    learning_style: dict
    mastered_concepts: list[dict]
    weak_concepts: list[dict]
    updated_at: str


class EpisodicRecord(BaseModel):
    id: str
    user_id: str
    node_id: str
    plan_id: str
    session_id: str
    summary: str
    concepts_covered: list[str]
    weak_points: list[str]
    strong_points: list[str]
    test_score: Optional[float]
    passed: bool
    conversation_turns: int
    created_at: str


class ProceduralPattern(BaseModel):
    user_id: str
    pattern_key: str
    pattern_value: str
    confidence: float
    sample_count: int
    updated_at: str


class ImageTriggerOutput(BaseModel):
    needs_image: bool
    image_type: Optional[Literal["mermaid", "dalle"]] = None
    mermaid_code: Optional[str] = None
    dalle_prompt: Optional[str] = None
    reason: str


class MemoryEvent(BaseModel):
    user_id: str
    session_id: str
    node_id: str
    event_type: Literal[
        "concept_passed",
        "concept_failed_twice",
        "concept_skipped",
        "test_passed",
        "test_failed",
        "session_completed",
    ]
    payload: dict
