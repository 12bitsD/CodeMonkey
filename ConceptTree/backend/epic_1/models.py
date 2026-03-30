# Epic 1: 认证与用户

from pydantic import BaseModel
from typing import Optional, Dict


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user: Dict[str, str]
    token: str
    expiresIn: Optional[int] = 604800


class UserProfile(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = "入门"
    mathLevel: Optional[str] = "入门"
    abilities: list = []
    masteredKnowledge: list = []


class UpdateProfileRequest(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = None
    mathLevel: Optional[str] = None
    abilities: Optional[list] = None
