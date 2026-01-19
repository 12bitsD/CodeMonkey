"""应用配置管理

支持从环境变量加载配置
"""

import os
from typing import Literal
from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # ==================== 应用基础配置 ====================
    
    APP_NAME: str = "PathFinder API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # ==================== 数据库配置 ====================
    
    # 数据库类型：sqlite | supabase
    DB_TYPE: Literal["sqlite", "supabase"] = "sqlite"
    
    # SQLite 配置
    SQLITE_PATH: str = "./database.sqlite"
    
    # Supabase 配置（未来使用）
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""  # 用于后端服务的 service role key
    
    # ==================== 认证配置 ====================
    
    # JWT 密钥（生产环境请修改）
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    
    # ==================== CORS 配置 ====================
    
    CORS_ORIGINS: list = ["*"]  # 生产环境应限制具体域名
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # ==================== AI 服务配置 ====================
    
    # OpenAI API（如果需要真实 AI 功能）
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


def get_database_config() -> dict:
    """获取数据库配置
    
    根据 DB_TYPE 返回对应的配置参数
    
    Returns:
        数据库配置字典
    """
    if settings.DB_TYPE == "sqlite":
        return {
            "db_type": "sqlite",
            "database_path": settings.SQLITE_PATH
        }
    elif settings.DB_TYPE == "supabase":
        return {
            "db_type": "supabase",
            "url": settings.SUPABASE_URL,
            "key": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        }
    else:
        raise ValueError(f"Unsupported DB_TYPE: {settings.DB_TYPE}")


# ==================== 使用示例 ====================

"""
# 在其他文件中使用：

from config import settings, get_database_config
from adapters import get_database_adapter

# 获取数据库适配器
db_config = get_database_config()
db = get_database_adapter(**db_config)

# 访问配置
print(settings.DB_TYPE)
print(settings.JWT_SECRET_KEY)
"""
