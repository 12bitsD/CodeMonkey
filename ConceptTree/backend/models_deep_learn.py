from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


DeepLearnState = Literal[
    "INITIALIZING", "TEACHING", "QUESTIONING", "EVALUATING", "AWAITING_COMMAND",
    "AI_ASSESSING_READINESS", "CONFIRMING_TEST", "TESTING", "EVALUATING_TEST",
    "CHOOSING_AFTER_FAIL", "GENERATING_NOTE", "COMPLETED",
]

DeepLearnCommand = Literal[
    "continue", "expand", "skip", "reteach",
    "restart", "confirm_test", "not_ready",
]

ConceptStatus = Literal["pending", "current", "done", "failed", "skipped"]

SessionStatus = Literal["in_progress", "completed", "abandoned"]

TeachingMode = Literal["normal", "expand", "reteach", "probe_stuck", "review_weak"]


class SessionState(BaseModel):
    id: str
    user_id: str
    node_id: str
    plan_id: str
    state: DeepLearnState
    current_concept_index: int
    difficulty_level: int
    wrong_count_current: int
    concepts_status: dict[str, str]
    weak_points: list[str]
    recent_turns: list[dict]
    what_list: list[str]
    test_questions: list[str]
    test_current_index: int
    test_results: list[dict]
    status: SessionStatus


class TeachingOutput(BaseModel):
    content: str
    questions: list[str]
    needs_image: bool = False
    image_type: Optional[str] = None
    mermaid_code: Optional[str] = None


class AssessmentPerQuestionOutput(BaseModel):
    is_correct: bool
    quality_score: float
    explanation: str
    feedback: str
    update_weak_points: list[str] = []
    difficulty_delta: int = 0
    wrong_count: int = 0


class AssessmentOverallOutput(BaseModel):
    passed: bool
    confidence: float
    ready_for_test: bool
    reason: str
    strong_areas: list[str] = []
    weak_areas: list[str] = []
    suggest_review_concepts: list[str] = []


class CreateSessionRequest(BaseModel):
    node_id: str
    plan_id: str


class CreateSessionData(BaseModel):
    session_id: str
    state: DeepLearnState
    is_resumed: bool
    node_name: str
    node_why: str
    what_list: list[str]
    concepts_status: dict[str, str]
    weak_points: list[str]
    current_concept_index: int
    recent_turns: list[dict]


class MessageRequest(BaseModel):
    content: str


class CommandRequest(BaseModel):
    command: DeepLearnCommand


class NoteGeneratorOutput(BaseModel):
    content: str  # Full markdown of the completion note


class CompletionNote(BaseModel):
    id: str
    user_id: str
    node_id: str
    session_id: str
    content: str
    created_at: str
