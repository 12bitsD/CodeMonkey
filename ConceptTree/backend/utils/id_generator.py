"""ID生成工具"""
import uuid


def generate_user_id() -> str:
    """生成用户ID"""
    return f"u_{uuid.uuid4().hex[:12]}"


def generate_profile_id() -> str:
    """生成用户画像ID"""
    return f"p_{uuid.uuid4().hex[:12]}"
