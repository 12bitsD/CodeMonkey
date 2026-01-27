from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db
from services.ai_service import parse_goal_service, generate_graph_service
from models import ErrorResponse
from utils.auth import get_current_user_id


router = APIRouter(prefix="/api/ai", tags=["AI"])


class ParseGoalRequest(BaseModel):
    input: str


class ParseGoalResponse(BaseModel):
    success: bool
    data: dict


class GenerateGraphRequest(BaseModel):
    input: str
    interpretation: str


class GenerateGraphResponse(BaseModel):
    success: bool
    data: dict


@router.post(
    "/parse-goal",
    response_model=ParseGoalResponse,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def parse_goal(
    request: ParseGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """AI解析学习目标"""
    try:
        user_profile = {}

        result = parse_goal_service(request.input, user_profile)

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "PARSE_GOAL_ERROR", "message": str(e)},
            },
        )


@router.post(
    "/generate-graph",
    response_model=GenerateGraphResponse,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def generate_graph(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """AI生成知识图谱"""
    try:
        user_profile = {}

        result = generate_graph_service(
            request.input, request.interpretation, user_profile
        )

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "GENERATE_GRAPH_ERROR", "message": str(e)},
            },
        )
