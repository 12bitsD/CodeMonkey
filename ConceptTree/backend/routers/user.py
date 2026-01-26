"""用户画像路由"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database import get_db_context
from models import UpdateProfileRequest
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api/user", tags=["用户"])


def parse_json_field(field_value, default=None):
    if default is None:
        default = []
    if not field_value:
        return default
    if isinstance(field_value, (list, dict)):
        return field_value
    return json.loads(field_value)


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    """获取用户画像"""
    with get_db_context() as db:
        profile = db.execute(
            """SELECT occupation, education, programming_level, math_level, 
                      abilities, mastered_knowledge
               FROM user_profiles WHERE user_id = ?""",
            (user_id,)
        ).fetchone()
        
        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {
                        "code": "PROFILE_NOT_FOUND",
                        "message": "用户画像不存在"
                    }
                }
            )
        
        abilities = parse_json_field(profile["abilities"])
        mastered_knowledge = parse_json_field(profile["mastered_knowledge"])
        
        return {
            "success": True,
            "data": {
                "occupation": profile["occupation"],
                "education": profile["education"],
                "programmingLevel": profile["programming_level"],
                "mathLevel": profile["math_level"],
                "abilities": abilities,
                "masteredKnowledge": mastered_knowledge
            }
        }


@router.put("/profile")
def update_profile(
    req: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id)
):
    """更新用户画像"""
    with get_db_context() as db:
        # 获取当前画像
        profile = db.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {
                        "code": "PROFILE_NOT_FOUND",
                        "message": "用户画像不存在"
                    }
                }
            )
        
        # 构建更新字段
        updates = []
        params = []
        
        if req.occupation is not None:
            updates.append("occupation = ?")
            params.append(req.occupation)
        
        if req.education is not None:
            updates.append("education = ?")
            params.append(req.education)
        
        if req.programmingLevel is not None:
            updates.append("programming_level = ?")
            params.append(req.programmingLevel)
        
        if req.mathLevel is not None:
            updates.append("math_level = ?")
            params.append(req.mathLevel)
        
        if req.abilities is not None:
            updates.append("abilities = ?")
            params.append(req.abilities)
        
        # masteredKnowledge字段不允许更新（只读）
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)

            set_clause = ", ".join(updates)
            query = f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?"
            db.execute(query, params)
            db.commit()
        
        # 返回更新后的画像
        updated_profile = db.execute(
            """SELECT occupation, education, programming_level, math_level, 
                      abilities, mastered_knowledge
               FROM user_profiles WHERE user_id = ?""",
            (user_id,)
        ).fetchone()
        
        abilities = parse_json_field(updated_profile["abilities"])
        mastered_knowledge = parse_json_field(
            updated_profile["mastered_knowledge"]
        )
        
        return {
            "success": True,
            "data": {
                "occupation": updated_profile["occupation"],
                "education": updated_profile["education"],
                "programmingLevel": updated_profile["programming_level"],
                "mathLevel": updated_profile["math_level"],
                "abilities": abilities,
                "masteredKnowledge": mastered_knowledge
            }
        }
