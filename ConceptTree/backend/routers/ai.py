"""
AI Router — exposes the AI-powered learning flow as REST endpoints.

This router is the bridge between the frontend's multi-step onboarding wizard
and the backend AI service (``ai_service``). All four endpoints are
authentication-required and delegate the heavy lifting to ``AIService``; this
router handles HTTP concerns (request validation, ownership checks, error
mapping) only.

The typical client flow in order:
  1. ``POST /ai/parse-goal``     — interpret a free-text goal into structured data
  2. ``POST /ai/generate-graph`` — turn the interpretation into a knowledge graph
  3. ``POST /ai/clarify-goal``   — (optional) refine the graph when the user edits
                                   the goal after seeing an existing plan
  4. ``POST /ai/recommend-next`` — (ongoing) get the AI's suggested next node to
                                   study based on current progress and user profile

All successful responses use the shape ``{"success": true, "data": {...}}``.
A failure inside the AI service is surfaced as HTTP 500 with
``{"success": false, "error": {...}}``.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional
import json

from database import get_db
from services.ai_service import get_ai_service
from services.learning_history import get_learning_history
from models import ErrorResponse, UserBackgroundInput
from utils.auth import get_current_user_id


router = APIRouter(prefix="/api/ai", tags=["AI"])


class ParseGoalRequest(BaseModel):
    """Request body for parsing a free-text learning goal.

    Attributes:
        input: The raw goal text entered by the user. Must be 5–2000 characters.
    """

    input: str
    userBackground: Optional[UserBackgroundInput] = None

    @field_validator("input")
    @classmethod
    def validate_input_length(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Input must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("Input must be less than 2000 characters")
        return v


class GenerateGraphRequest(BaseModel):
    """Request body for generating a knowledge graph from a parsed goal.

    Attributes:
        input: The original free-text goal (context for the AI).
        interpretation: The structured interpretation returned by ``/parse-goal``.
        userBackground: Optional user background data (occupation, skill levels)
            used to personalise graph depth and difficulty.
    """

    input: str
    interpretation: str
    userBackground: Optional[UserBackgroundInput] = None


class ParseGoalResponseWrapper(BaseModel):
    """Envelope returned by ``/parse-goal``."""

    success: bool
    data: dict


class GenerateGraphResponseWrapper(BaseModel):
    """Envelope returned by ``/generate-graph``."""

    success: bool
    data: dict


@router.post(
    "/parse-goal",
    response_model=ParseGoalResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def parse_goal(
    request: ParseGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Interpret a free-text learning goal and return a structured representation.

    This is **step 1** of the onboarding flow. The AI reads the user's raw
    input (e.g. "I want to learn machine learning") and returns a structured
    object describing the target concept, inferred scope, and any ambiguities
    the user should confirm before graph generation.

    Args:
        request: Contains ``input`` — the user's free-text goal (5–2000 chars).
        current_user_id: Injected from the auth token (user must be authenticated).
        db: Injected database connection (reserved for future per-user context).

    Returns:
        ``ParseGoalResponseWrapper`` with the AI's structured interpretation in
        ``data``.

    Raises:
        HTTPException 500: AI service returned an error (propagated from
            ``AIService.parse_goal``).
    """
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None
    result = await ai_service.parse_goal(request.input, user_background=user_bg)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )

    return {"success": True, "data": result.data.model_dump() if result.data else {}}


@router.post(
    "/generate-graph",
    response_model=GenerateGraphResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def generate_graph(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Generate a knowledge graph (nodes + edges) from a confirmed goal interpretation.

    This is **step 2** of the onboarding flow, called once the user confirms
    the parsed goal. The AI uses the structured ``interpretation`` plus the
    optional ``userBackground`` to produce a dependency graph of learning
    concepts: each node is a topic to master, and each edge represents
    a prerequisite relationship.

    Args:
        request: Contains ``input`` (original text), ``interpretation``
            (from ``/parse-goal``), and optional ``userBackground``.
        current_user_id: Injected from the auth token.
        db: Injected database connection (reserved for future per-user context).

    Returns:
        ``GenerateGraphResponseWrapper`` with the full graph structure (nodes,
        edges, target node) in ``data``.

    Raises:
        HTTPException 500: AI service returned an error.
    """
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None
    result = await ai_service.generate_graph(
        interpretation=request.interpretation,
        original_input=request.input,
        user_background=user_bg,
    )

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )

    return {"success": True, "data": result.data.model_dump() if result.data else {}}


class ClarifyGoalRequest(BaseModel):
    """Request body for re-analysing a goal after the user edits it.

    Attributes:
        originalGoal: The goal text that was used to build the existing plan.
        newGoal: The user's revised goal text (5–2000 characters required).
        planId: Optional ID of the existing plan whose nodes should be used as
            context so the AI can suggest which to keep, add, or remove.
    """

    originalGoal: str
    newGoal: str
    planId: Optional[str] = None

    @field_validator("newGoal")
    @classmethod
    def validate_new_goal_length(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("New goal must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("New goal must be less than 2000 characters")
        return v


class ClarifyGoalResponseWrapper(BaseModel):
    """Envelope returned by ``/clarify-goal``."""

    success: bool
    data: dict


@router.post(
    "/clarify-goal",
    response_model=ClarifyGoalResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def clarify_goal(
    request: ClarifyGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Compare a revised goal against an existing plan and return suggested changes.

    This is **step 3** (optional) — called when a user refines their goal after
    a plan already exists. If ``planId`` is provided and belongs to the current
    user, the existing nodes are fetched and sent to the AI so it can suggest
    which nodes to keep, add, or remove. Without ``planId``, the AI compares
    goals without any node context.

    Args:
        request: Contains ``originalGoal``, ``newGoal`` (5–2000 chars), and an
            optional ``planId``.
        current_user_id: Injected from the auth token; used to verify plan
            ownership before exposing node data.
        db: Injected database connection.

    Returns:
        ``ClarifyGoalResponseWrapper`` with the AI's diff-style suggestions
        (``keep``, ``add``, ``remove`` node lists, new title) in ``data``.

    Raises:
        HTTPException 500: AI service returned an error.
    """
    existing_nodes = []
    if request.planId:
        plan = db.execute(
            "SELECT user_id FROM plans WHERE id = ?", (request.planId,)
        ).fetchone()
        if plan and plan["user_id"] == current_user_id:
            rows = db.execute(
                "SELECT id, name, status FROM nodes WHERE plan_id = ?",
                (request.planId,),
            ).fetchall()
            existing_nodes = [
                {"id": r["id"], "name": r["name"], "status": r["status"]} for r in rows
            ]

    ai_service = get_ai_service()
    result = await ai_service.clarify_goal(
        original_goal=request.originalGoal,
        new_goal=request.newGoal,
        existing_nodes=existing_nodes,
    )
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )
    return {"success": True, "data": result.data.model_dump() if result.data else {}}


class RecommendNextRequest(BaseModel):
    """Request body for getting the AI's next-study recommendation.

    Attributes:
        planId: The active plan for which to generate a recommendation.
    """

    planId: str


class RecommendNextResponseWrapper(BaseModel):
    """Envelope returned by ``/recommend-next``."""

    success: bool
    data: dict


@router.post(
    "/recommend-next",
    response_model=RecommendNextResponseWrapper,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def recommend_next(
    request: RecommendNextRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Recommend the best next node to study based on current plan state and user profile.

    This endpoint assembles three context sources before calling the AI:
      1. **Graph snapshot** — all nodes (id, name, status, isTarget) and edges
         for the plan, so the AI understands prerequisite structure and progress.
      2. **User profile** — occupation, math level, programming level, and
         ability tags from ``user_profiles``; defaults to empty strings / "入门"
         (beginner) if no profile exists.
      3. **Learning history** — recent activity fetched via
         ``get_learning_history`` to help the AI avoid repeating recent nodes.

    Args:
        request: Contains ``planId`` — the plan to generate a recommendation for.
        current_user_id: Injected from the auth token; must match the plan owner.
        db: Injected database connection.

    Returns:
        ``RecommendNextResponseWrapper`` with the AI's recommendation in ``data``
        (typically a node ID, name, and reasoning).

    Raises:
        HTTPException 403: Authenticated user does not own this plan.
        HTTPException 404: Plan not found (``PLAN_NOT_FOUND``).
        HTTPException 500: AI service returned an error.
    """
    plan = db.execute(
        "SELECT id, user_id, title, target_node_id FROM plans WHERE id = ?",
        (request.planId,),
    ).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "PLAN_NOT_FOUND", "message": "Plan not found"},
            },
        )
    if plan["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    nodes = db.execute(
        "SELECT id, name, status, is_target FROM nodes WHERE plan_id = ?",
        (request.planId,),
    ).fetchall()
    edges = db.execute(
        "SELECT from_node_id, to_node_id FROM edges WHERE plan_id = ?",
        (request.planId,),
    ).fetchall()
    profile_row = db.execute(
        "SELECT occupation, math_level, programming_level, abilities FROM user_profiles WHERE user_id = ?",
        (current_user_id,),
    ).fetchone()

    graph = {
        "nodes": [
            {
                "id": n["id"],
                "name": n["name"],
                "status": n["status"],
                "isTarget": bool(n["is_target"]),
            }
            for n in nodes
        ],
        "edges": [
            {"from_node": e["from_node_id"], "to_node": e["to_node_id"]} for e in edges
        ],
        "target_node_id": plan["target_node_id"],
    }

    user_profile = {}
    if profile_row:
        abilities = profile_row["abilities"]
        if isinstance(abilities, str):
            abilities = json.loads(abilities)
        user_profile = {
            "occupation": profile_row["occupation"] or "",
            "math_level": profile_row["math_level"] or "入门",
            "programming_level": profile_row["programming_level"] or "入门",
            "abilities": abilities or [],
        }

    history = get_learning_history(
        user_id=current_user_id, plan_id=request.planId, db=db
    )

    ai_service = get_ai_service()
    result = await ai_service.recommend_next(
        graph=graph,
        user_profile=user_profile,
        learning_history=history,
        learning_goal=plan["title"],
    )

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": result.error.model_dump() if result.error else {},
            },
        )
    return {"success": True, "data": result.data.model_dump() if result.data else {}}
