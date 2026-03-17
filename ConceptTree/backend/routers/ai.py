from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from database import get_db
from services.ai_service import get_ai_service
from models import ErrorResponse, UserBackgroundInput
from utils.auth import get_current_user_id


router = APIRouter(prefix="/api/ai", tags=["AI"])


class ParseGoalRequest(BaseModel):
    input: str

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
    result = await ai_service.parse_goal(request.input)

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
