"""认证路由"""

import re
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database import get_db_context
from models import LoginRequest, RegisterRequest
from utils.password import hash_password, verify_password
from utils.auth import create_access_token, get_current_user_id
from utils.id_generator import generate_user_id, generate_profile_id

router = APIRouter(prefix="/api/auth", tags=["认证"])


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@router.post("/register")
def register(req: RegisterRequest):
    """用户注册"""
    # 验证邮箱格式
    if not validate_email(req.email):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "INVALID_EMAIL", "message": "邮箱格式不正确"},
            },
        )

    # 验证密码长度
    if len(req.password) < 6:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "密码长度至少6位"},
            },
        )

    with get_db_context() as db:
        # 检查邮箱是否已存在
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (req.email,)
        ).fetchone()

        if existing:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": {"code": "EMAIL_EXISTS", "message": "邮箱已被注册"},
                },
            )

        # 创建用户
        user_id = generate_user_id()
        password_hash = hash_password(req.password)

        db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, req.email, password_hash),
        )

        # 创建空的用户画像
        profile_id = generate_profile_id()
        db.execute(
            """INSERT INTO user_profiles (
                   id,
                   user_id,
                   occupation,
                   education,
                   programming_level,
                   math_level,
                   abilities,
                   mastered_knowledge
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (profile_id, user_id, None, None, "入门", "入门", "[]", "[]"),
        )

        db.commit()

        # 生成token
        token = create_access_token(data={"sub": user_id})

        return {
            "success": True,
            "data": {
                "user": {"id": user_id, "email": req.email},
                "token": token,
            },
        }


@router.post("/login")
def login(req: LoginRequest):
    """用户登录"""
    with get_db_context() as db:
        user = db.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (req.email,),
        ).fetchone()

        if not user or not verify_password(
            req.password,
            user["password_hash"],
        ):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "邮箱或密码错误",
                    },
                },
            )

        # 生成token
        token = create_access_token(data={"sub": user["id"]})

        return {
            "success": True,
            "data": {
                "user": {"id": user["id"], "email": user["email"]},
                "token": token,
                "expiresIn": 604800,
            },
        }


@router.post("/logout")
def logout(user_id: str = Depends(get_current_user_id)):
    """用户登出"""
    # 在实际应用中，这里应该将token加入黑名单
    # 目前简化实现，只返回成功消息
    return {"success": True, "data": {"message": "已登出"}}
