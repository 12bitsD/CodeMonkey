"""Phase 2 Memory System — Pydantic models"""

from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

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

_DIAGRAM_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,31}$")
_MAX_DIAGRAM_BYTES = 8 * 1024


class DiagramDetails(BaseModel):
    key_points: list[str] = Field(default_factory=list, max_length=4)
    example: Optional[str] = Field(default=None, max_length=180)
    misconception: Optional[str] = Field(default=None, max_length=180)


class DiagramNode(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=32)
    summary: str = Field(min_length=1, max_length=96)
    role: Literal["core", "support", "example", "warning"] = "support"
    details: DiagramDetails = Field(default_factory=DiagramDetails)

    @model_validator(mode="after")
    def validate_id(self) -> "DiagramNode":
        if not _DIAGRAM_ID_PATTERN.fullmatch(self.id):
            raise ValueError("diagram node id has an invalid format")
        return self


class DiagramEdge(BaseModel):
    source: str
    target: str
    relation: Literal[
        "prerequisite",
        "sequence",
        "causes",
        "contains",
        "contrasts",
        "supports",
        "feedback",
        "related",
    ]
    label: Optional[str] = Field(default=None, max_length=32)


class DiagramSpec(BaseModel):
    version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=64)
    layout: Literal["flow", "hierarchy", "radial", "comparison", "cycle"]
    nodes: list[DiagramNode] = Field(min_length=2, max_length=8)
    edges: list[DiagramEdge] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_graph(self) -> "DiagramSpec":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("diagram node ids must be unique")
        known_ids = set(node_ids)
        if any(edge.source not in known_ids or edge.target not in known_ids for edge in self.edges):
            raise ValueError("diagram edges must reference existing nodes")
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")
        if len(payload) > _MAX_DIAGRAM_BYTES:
            raise ValueError("diagram payload exceeds 8 KiB")
        return self


class VisualDecision(BaseModel):
    visual_type: Literal["none", "diagram", "illustration"]
    diagram: Optional[DiagramSpec] = None
    illustration_prompt: Optional[str] = Field(default=None, max_length=600)
    caption: Optional[str] = Field(default=None, max_length=120)
    reason: str = Field(max_length=240)

    @model_validator(mode="after")
    def validate_payload(self) -> "VisualDecision":
        if self.visual_type == "none" and (self.diagram or self.illustration_prompt):
            raise ValueError("none decisions cannot include a visual payload")
        if self.visual_type == "diagram" and (not self.diagram or self.illustration_prompt):
            raise ValueError("diagram decisions require only a diagram payload")
        if self.visual_type == "illustration" and (self.diagram or not self.illustration_prompt):
            raise ValueError("illustration decisions require only an illustration prompt")
        return self


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
