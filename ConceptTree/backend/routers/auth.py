"""认证路由"""

import re
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from database import get_db_context
from models import LoginRequest, RegisterRequest
from utils.password import hash_password, verify_password
from utils.auth import (
    create_access_token,
    get_current_user_id,
    add_token_to_blacklist,
)
from utils.id_generator import generate_user_id, generate_profile_id
from utils.limiter import limiter

_bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth", tags=["认证"])


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@router.post("/register")
@limiter.limit("5/15minutes")
def register(request: Request, req: RegisterRequest):
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

    # 验证密码强度：至少8位，包含字母和数字
    if len(req.password) < 8:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "密码长度至少8位"},
            },
        )
    if not re.search(r"[A-Za-z]", req.password) or not re.search(r"\d", req.password):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"code": "WEAK_PASSWORD", "message": "密码须同时包含字母和数字"},
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
@limiter.limit("5/15minutes")
def login(request: Request, req: LoginRequest):
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
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    user_id: str = Depends(get_current_user_id),
):
    """用户登出（将 token 加入黑名单使其立即失效）"""
    if credentials:
        add_token_to_blacklist(credentials.credentials)
    return {"success": True, "data": {"message": "已登出"}}
