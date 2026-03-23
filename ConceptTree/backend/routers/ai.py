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
    input: str
    interpretation: str
    userBackground: Optional[UserBackgroundInput] = None


class ParseGoalResponseWrapper(BaseModel):
    success: bool
    data: dict


class GenerateGraphResponseWrapper(BaseModel):
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
    """AI解析学习目标"""
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
    """AI生成知识图谱"""
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
    planId: str


class RecommendNextResponseWrapper(BaseModel):
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
    return {
        "success": True,
        "data": result.data.model_dump(by_alias=True) if result.data else {},
    }
